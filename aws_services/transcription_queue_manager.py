"""
Transcription Job Queue Manager

Manages asynchronous transcription jobs with FIFO queue processing,
concurrent job limiting, retry logic with exponential backoff, and
job metadata tracking.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, Any
from enum import Enum
from utils.logger import get_logger

logger = get_logger(__name__)


class JobStatus(Enum):
    """Job status enumeration"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class JobMetadata:
    """Metadata for a transcription job"""
    job_id: str
    session_id: str
    audio_data: bytes
    chunk_sequence: int
    status: JobStatus = JobStatus.QUEUED
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class TranscriptionQueueManager:
    """
    Manages asynchronous transcription job queue with FIFO processing,
    concurrent job limiting, and retry logic with exponential backoff.
    """
    
    def __init__(self, max_concurrent_jobs: int = 10, max_retries: int = 3):
        """
        Initialize the queue manager
        
        Args:
            max_concurrent_jobs: Maximum number of concurrent transcription jobs (default 10)
            max_retries: Maximum number of retry attempts per job (default 3)
        """
        self.max_concurrent_jobs = max_concurrent_jobs
        self.max_retries = max_retries
        
        # FIFO queue for pending jobs
        self.job_queue: asyncio.Queue = asyncio.Queue()
        
        # Track active jobs
        self.active_jobs: Dict[str, JobMetadata] = {}
        
        # Track all job metadata (for status queries)
        self.job_metadata: Dict[str, JobMetadata] = {}
        
        # Worker tasks
        self.workers: list = []
        
        # Shutdown flag
        self.shutdown_flag = False
        
        logger.info(f"TranscriptionQueueManager initialized: max_concurrent={max_concurrent_jobs}, max_retries={max_retries}")
    
    async def enqueue_job(
        self,
        job_id: str,
        session_id: str,
        audio_data: bytes,
        chunk_sequence: int = 0
    ) -> JobMetadata:
        """
        Enqueue a new transcription job
        
        Args:
            job_id: Unique job identifier
            session_id: Session identifier
            audio_data: Audio data to transcribe
            chunk_sequence: Sequence number for chunk ordering
            
        Returns:
            JobMetadata: Metadata for the enqueued job
        """
        metadata = JobMetadata(
            job_id=job_id,
            session_id=session_id,
            audio_data=audio_data,
            chunk_sequence=chunk_sequence,
            max_retries=self.max_retries
        )
        
        # Store metadata
        self.job_metadata[job_id] = metadata
        
        # Add to queue (non-blocking)
        await self.job_queue.put(metadata)
        
        logger.info(f"Job enqueued: job_id={job_id}, session_id={session_id}, chunk={chunk_sequence}, queue_size={self.job_queue.qsize()}")
        
        return metadata
    
    async def start_workers(self, transcription_handler: Callable):
        """
        Start worker tasks to process jobs from the queue
        
        Args:
            transcription_handler: Async function to handle transcription
                                  Should accept (job_id, session_id, audio_data, chunk_sequence)
                                  and return result dict or raise exception on failure
        """
        if self.workers:
            logger.warning("Workers already started")
            return
        
        logger.info(f"Starting {self.max_concurrent_jobs} worker tasks")
        
        for i in range(self.max_concurrent_jobs):
            worker = asyncio.create_task(
                self._worker(worker_id=i, transcription_handler=transcription_handler)
            )
            self.workers.append(worker)
        
        logger.info(f"Started {len(self.workers)} workers")
    
    async def _worker(self, worker_id: int, transcription_handler: Callable):
        """
        Worker task that processes jobs from the queue
        
        Args:
            worker_id: Worker identifier for logging
            transcription_handler: Function to handle transcription
        """
        logger.info(f"Worker {worker_id} started")
        
        while not self.shutdown_flag:
            try:
                # Get job from queue (with timeout to check shutdown flag)
                try:
                    metadata = await asyncio.wait_for(
                        self.job_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process the job
                await self._process_job(worker_id, metadata, transcription_handler)
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {str(e)}")
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def _process_job(
        self,
        worker_id: int,
        metadata: JobMetadata,
        transcription_handler: Callable
    ):
        """
        Process a single job with retry logic
        
        Args:
            worker_id: Worker identifier for logging
            metadata: Job metadata
            transcription_handler: Function to handle transcription
        """
        job_id = metadata.job_id
        
        try:
            # Update status to processing
            metadata.status = JobStatus.PROCESSING
            metadata.started_at = time.time()
            self.active_jobs[job_id] = metadata
            
            logger.info(f"Worker {worker_id} processing job: job_id={job_id}, session_id={metadata.session_id}, chunk={metadata.chunk_sequence}")
            
            # Call transcription handler
            result = await transcription_handler(
                job_id=metadata.job_id,
                session_id=metadata.session_id,
                audio_data=metadata.audio_data,
                chunk_sequence=metadata.chunk_sequence
            )
            
            # Job completed successfully
            metadata.status = JobStatus.COMPLETED
            metadata.completed_at = time.time()
            metadata.result = result
            
            logger.info(f"Worker {worker_id} completed job: job_id={job_id}, duration={metadata.completed_at - metadata.started_at:.2f}s")
            
        except Exception as e:
            # Job failed
            error_msg = str(e)
            logger.error(f"Worker {worker_id} job failed: job_id={job_id}, error={error_msg}, retry_count={metadata.retry_count}")
            
            metadata.error_message = error_msg
            
            # Check if we should retry
            if metadata.retry_count < metadata.max_retries:
                # Retry with exponential backoff
                metadata.retry_count += 1
                metadata.status = JobStatus.RETRYING
                
                # Calculate backoff delay: 2^retry_count seconds (1s, 2s, 4s)
                backoff_delay = 2 ** (metadata.retry_count - 1)
                
                logger.info(f"Worker {worker_id} retrying job: job_id={job_id}, retry={metadata.retry_count}/{metadata.max_retries}, backoff={backoff_delay}s")
                
                # Wait for backoff period
                await asyncio.sleep(backoff_delay)
                
                # Re-enqueue the job
                metadata.status = JobStatus.QUEUED
                metadata.started_at = None
                await self.job_queue.put(metadata)
                
            else:
                # Max retries exceeded
                metadata.status = JobStatus.FAILED
                metadata.completed_at = time.time()
                
                logger.error(f"Worker {worker_id} job failed permanently: job_id={job_id}, retries_exhausted={metadata.retry_count}")
        
        finally:
            # Remove from active jobs
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
    
    def get_job_status(self, job_id: str) -> Optional[JobMetadata]:
        """
        Get the status of a job
        
        Args:
            job_id: Job identifier
            
        Returns:
            JobMetadata if found, None otherwise
        """
        return self.job_metadata.get(job_id)
    
    def get_queue_position(self, job_id: str) -> Optional[int]:
        """
        Get the queue position of a job (0-indexed)
        
        Args:
            job_id: Job identifier
            
        Returns:
            Queue position if job is queued, None otherwise
        """
        metadata = self.job_metadata.get(job_id)
        if not metadata or metadata.status != JobStatus.QUEUED:
            return None
        
        # Count jobs in queue before this one
        # Note: This is approximate since queue is being processed concurrently
        return self.job_queue.qsize()
    
    def get_queue_size(self) -> int:
        """Get the current queue size"""
        return self.job_queue.qsize()
    
    def get_active_job_count(self) -> int:
        """Get the number of currently processing jobs"""
        return len(self.active_jobs)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get queue statistics
        
        Returns:
            Dictionary with queue statistics
        """
        total_jobs = len(self.job_metadata)
        completed = sum(1 for m in self.job_metadata.values() if m.status == JobStatus.COMPLETED)
        failed = sum(1 for m in self.job_metadata.values() if m.status == JobStatus.FAILED)
        processing = len(self.active_jobs)
        queued = self.job_queue.qsize()
        
        return {
            'total_jobs': total_jobs,
            'completed': completed,
            'failed': failed,
            'processing': processing,
            'queued': queued,
            'max_concurrent': self.max_concurrent_jobs
        }
    
    async def retry_failed_job(self, job_id: str) -> bool:
        """
        Manually retry a failed job
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if job was re-queued, False if job not found or not failed
        """
        metadata = self.job_metadata.get(job_id)
        
        if not metadata:
            logger.warning(f"Cannot retry job: job_id={job_id} not found")
            return False
        
        if metadata.status != JobStatus.FAILED:
            logger.warning(f"Cannot retry job: job_id={job_id} status={metadata.status.value} (must be FAILED)")
            return False
        
        # Reset job for retry
        metadata.status = JobStatus.QUEUED
        metadata.retry_count = 0  # Reset retry count for manual retry
        metadata.started_at = None
        metadata.completed_at = None
        metadata.error_message = None
        
        # Re-enqueue the job
        await self.job_queue.put(metadata)
        
        logger.info(f"Manually retrying failed job: job_id={job_id}")
        
        return True
    
    async def shutdown(self):
        """Gracefully shutdown the queue manager"""
        logger.info("Shutting down TranscriptionQueueManager")
        
        self.shutdown_flag = True
        
        # Wait for workers to finish
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
            self.workers.clear()
        
        logger.info("TranscriptionQueueManager shutdown complete")
    
    def cleanup_old_metadata(self, max_age_seconds: float = 86400):
        """
        Clean up old job metadata (default 24 hours)
        
        Args:
            max_age_seconds: Maximum age of metadata to keep (default 86400 = 24 hours)
        """
        current_time = time.time()
        jobs_to_remove = []
        
        for job_id, metadata in self.job_metadata.items():
            # Only clean up completed or failed jobs
            if metadata.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                age = current_time - metadata.created_at
                if age > max_age_seconds:
                    jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self.job_metadata[job_id]
        
        if jobs_to_remove:
            logger.info(f"Cleaned up {len(jobs_to_remove)} old job metadata entries")
        
        return len(jobs_to_remove)
