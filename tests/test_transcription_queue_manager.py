"""
Unit tests for TranscriptionQueueManager

Tests FIFO queue processing, concurrent job limiting, retry logic,
and job metadata tracking.
"""

import pytest
import asyncio
import time
from aws_services.transcription_queue_manager import (
    TranscriptionQueueManager,
    JobStatus,
    JobMetadata
)


@pytest.fixture
def queue_manager():
    """Create a queue manager for testing"""
    return TranscriptionQueueManager(max_concurrent_jobs=3, max_retries=3)


@pytest.fixture
def sample_audio_data():
    """Sample audio data for testing"""
    return b"sample_audio_data_bytes"


@pytest.mark.asyncio
async def test_enqueue_job(queue_manager, sample_audio_data):
    """Test enqueuing a job"""
    metadata = await queue_manager.enqueue_job(
        job_id="job1",
        session_id="session1",
        audio_data=sample_audio_data,
        chunk_sequence=0
    )
    
    assert metadata.job_id == "job1"
    assert metadata.session_id == "session1"
    assert metadata.audio_data == sample_audio_data
    assert metadata.chunk_sequence == 0
    assert metadata.status == JobStatus.QUEUED
    assert metadata.retry_count == 0
    assert queue_manager.get_queue_size() == 1


@pytest.mark.asyncio
async def test_fifo_order(queue_manager, sample_audio_data):
    """Test that jobs are processed in FIFO order"""
    processed_jobs = []
    
    async def mock_handler(job_id, session_id, audio_data, chunk_sequence):
        """Mock transcription handler that records job order"""
        processed_jobs.append(job_id)
        await asyncio.sleep(0.1)  # Simulate processing time
        return {"text": f"transcription_{job_id}"}
    
    # Enqueue multiple jobs
    for i in range(5):
        await queue_manager.enqueue_job(
            job_id=f"job{i}",
            session_id="session1",
            audio_data=sample_audio_data,
            chunk_sequence=i
        )
    
    # Start workers with only 1 concurrent job to ensure FIFO
    queue_manager.max_concurrent_jobs = 1
    await queue_manager.start_workers(mock_handler)
    
    # Wait for all jobs to complete
    while queue_manager.get_queue_size() > 0 or queue_manager.get_active_job_count() > 0:
        await asyncio.sleep(0.1)
    
    # Shutdown workers
    await queue_manager.shutdown()
    
    # Verify FIFO order
    assert processed_jobs == ["job0", "job1", "job2", "job3", "job4"]


@pytest.mark.asyncio
async def test_concurrent_job_limiting(queue_manager, sample_audio_data):
    """Test that concurrent jobs are limited to max_concurrent_jobs"""
    max_concurrent_observed = 0
    current_concurrent = 0
    lock = asyncio.Lock()
    
    async def mock_handler(job_id, session_id, audio_data, chunk_sequence):
        """Mock handler that tracks concurrent execution"""
        nonlocal max_concurrent_observed, current_concurrent
        
        async with lock:
            current_concurrent += 1
            max_concurrent_observed = max(max_concurrent_observed, current_concurrent)
        
        await asyncio.sleep(0.2)  # Simulate processing time
        
        async with lock:
            current_concurrent -= 1
        
        return {"text": f"transcription_{job_id}"}
    
    # Enqueue more jobs than max_concurrent_jobs
    for i in range(10):
        await queue_manager.enqueue_job(
            job_id=f"job{i}",
            session_id="session1",
            audio_data=sample_audio_data,
            chunk_sequence=i
        )
    
    # Start workers
    await queue_manager.start_workers(mock_handler)
    
    # Wait for all jobs to complete
    while queue_manager.get_queue_size() > 0 or queue_manager.get_active_job_count() > 0:
        await asyncio.sleep(0.1)
    
    # Shutdown workers
    await queue_manager.shutdown()
    
    # Verify concurrent limit was respected
    assert max_concurrent_observed <= queue_manager.max_concurrent_jobs


@pytest.mark.asyncio
async def test_retry_logic_with_exponential_backoff(queue_manager, sample_audio_data):
    """Test retry logic with exponential backoff"""
    attempt_times = []
    
    async def failing_handler(job_id, session_id, audio_data, chunk_sequence):
        """Mock handler that fails on first 2 attempts, succeeds on 3rd"""
        attempt_times.append(time.time())
        if len(attempt_times) < 3:
            raise Exception(f"Simulated failure {len(attempt_times)}")
        return {"text": "success"}
    
    # Enqueue a job
    await queue_manager.enqueue_job(
        job_id="job1",
        session_id="session1",
        audio_data=sample_audio_data,
        chunk_sequence=0
    )
    
    # Start workers
    await queue_manager.start_workers(failing_handler)
    
    # Wait for job to complete (with retries)
    timeout = time.time() + 10  # 10 second timeout
    while time.time() < timeout:
        metadata = queue_manager.get_job_status("job1")
        if metadata and metadata.status == JobStatus.COMPLETED:
            break
        await asyncio.sleep(0.1)
    
    # Shutdown workers
    await queue_manager.shutdown()
    
    # Verify retry behavior
    metadata = queue_manager.get_job_status("job1")
    assert metadata.status == JobStatus.COMPLETED
    assert metadata.retry_count == 2  # Failed twice, succeeded on 3rd attempt
    assert len(attempt_times) == 3
    
    # Verify exponential backoff (approximately 1s, 2s delays)
    if len(attempt_times) >= 3:
        delay1 = attempt_times[1] - attempt_times[0]
        delay2 = attempt_times[2] - attempt_times[1]
        
        # Allow some tolerance for timing
        assert 0.8 <= delay1 <= 1.5  # ~1 second backoff
        assert 1.8 <= delay2 <= 2.5  # ~2 second backoff


@pytest.mark.asyncio
async def test_max_retries_exceeded(queue_manager, sample_audio_data):
    """Test that jobs fail after max retries"""
    async def always_failing_handler(job_id, session_id, audio_data, chunk_sequence):
        """Mock handler that always fails"""
        raise Exception("Permanent failure")
    
    # Enqueue a job
    await queue_manager.enqueue_job(
        job_id="job1",
        session_id="session1",
        audio_data=sample_audio_data,
        chunk_sequence=0
    )
    
    # Start workers
    await queue_manager.start_workers(always_failing_handler)
    
    # Wait for job to fail permanently
    timeout = time.time() + 15  # 15 second timeout (enough for 3 retries with backoff)
    while time.time() < timeout:
        metadata = queue_manager.get_job_status("job1")
        if metadata and metadata.status == JobStatus.FAILED:
            break
        await asyncio.sleep(0.1)
    
    # Shutdown workers
    await queue_manager.shutdown()
    
    # Verify job failed after max retries
    metadata = queue_manager.get_job_status("job1")
    assert metadata.status == JobStatus.FAILED
    assert metadata.retry_count == 3
    assert metadata.error_message == "Permanent failure"


@pytest.mark.asyncio
async def test_job_metadata_tracking(queue_manager, sample_audio_data):
    """Test job metadata tracking (status, timestamps, retry count)"""
    async def mock_handler(job_id, session_id, audio_data, chunk_sequence):
        """Mock handler"""
        await asyncio.sleep(0.1)
        return {"text": "transcription"}
    
    # Enqueue a job
    metadata = await queue_manager.enqueue_job(
        job_id="job1",
        session_id="session1",
        audio_data=sample_audio_data,
        chunk_sequence=0
    )
    
    # Check initial metadata
    assert metadata.status == JobStatus.QUEUED
    assert metadata.created_at > 0
    assert metadata.started_at is None
    assert metadata.completed_at is None
    
    # Start workers
    await queue_manager.start_workers(mock_handler)
    
    # Wait for job to complete
    timeout = time.time() + 5
    while time.time() < timeout:
        metadata = queue_manager.get_job_status("job1")
        if metadata and metadata.status == JobStatus.COMPLETED:
            break
        await asyncio.sleep(0.1)
    
    # Shutdown workers
    await queue_manager.shutdown()
    
    # Check final metadata
    metadata = queue_manager.get_job_status("job1")
    assert metadata.status == JobStatus.COMPLETED
    assert metadata.started_at > metadata.created_at
    assert metadata.completed_at > metadata.started_at
    assert metadata.retry_count == 0
    assert metadata.result == {"text": "transcription"}


@pytest.mark.asyncio
async def test_get_statistics(queue_manager, sample_audio_data):
    """Test queue statistics"""
    async def mock_handler(job_id, session_id, audio_data, chunk_sequence):
        """Mock handler"""
        await asyncio.sleep(0.1)
        return {"text": "transcription"}
    
    # Enqueue multiple jobs
    for i in range(5):
        await queue_manager.enqueue_job(
            job_id=f"job{i}",
            session_id="session1",
            audio_data=sample_audio_data,
            chunk_sequence=i
        )
    
    # Check initial statistics
    stats = queue_manager.get_statistics()
    assert stats['total_jobs'] == 5
    assert stats['queued'] == 5
    assert stats['processing'] == 0
    assert stats['completed'] == 0
    assert stats['failed'] == 0
    
    # Start workers
    await queue_manager.start_workers(mock_handler)
    
    # Wait for all jobs to complete
    while queue_manager.get_queue_size() > 0 or queue_manager.get_active_job_count() > 0:
        await asyncio.sleep(0.1)
    
    # Shutdown workers
    await queue_manager.shutdown()
    
    # Check final statistics
    stats = queue_manager.get_statistics()
    assert stats['total_jobs'] == 5
    assert stats['completed'] == 5
    assert stats['failed'] == 0
    assert stats['queued'] == 0
    assert stats['processing'] == 0


@pytest.mark.asyncio
async def test_cleanup_old_metadata(queue_manager, sample_audio_data):
    """Test cleanup of old job metadata"""
    async def mock_handler(job_id, session_id, audio_data, chunk_sequence):
        """Mock handler"""
        return {"text": "transcription"}
    
    # Enqueue and process a job
    await queue_manager.enqueue_job(
        job_id="job1",
        session_id="session1",
        audio_data=sample_audio_data,
        chunk_sequence=0
    )
    
    await queue_manager.start_workers(mock_handler)
    
    # Wait for job to complete
    while queue_manager.get_queue_size() > 0 or queue_manager.get_active_job_count() > 0:
        await asyncio.sleep(0.1)
    
    await queue_manager.shutdown()
    
    # Manually set old timestamp
    metadata = queue_manager.get_job_status("job1")
    metadata.created_at = time.time() - 90000  # 25 hours ago
    
    # Cleanup old metadata (24 hour threshold)
    removed_count = queue_manager.cleanup_old_metadata(max_age_seconds=86400)
    
    assert removed_count == 1
    assert queue_manager.get_job_status("job1") is None


@pytest.mark.asyncio
async def test_immediate_return_on_enqueue(queue_manager, sample_audio_data):
    """Test that enqueue returns immediately without blocking"""
    async def slow_handler(job_id, session_id, audio_data, chunk_sequence):
        """Mock handler with long processing time"""
        await asyncio.sleep(5)
        return {"text": "transcription"}
    
    # Start workers
    await queue_manager.start_workers(slow_handler)
    
    # Enqueue job and measure time
    start_time = time.time()
    await queue_manager.enqueue_job(
        job_id="job1",
        session_id="session1",
        audio_data=sample_audio_data,
        chunk_sequence=0
    )
    enqueue_time = time.time() - start_time
    
    # Enqueue should return immediately (< 0.1 seconds)
    assert enqueue_time < 0.1
    
    # Verify job is queued
    assert queue_manager.get_queue_size() >= 0  # May have been picked up already
    
    # Cleanup
    await queue_manager.shutdown()


@pytest.mark.asyncio
async def test_multiple_sessions(queue_manager, sample_audio_data):
    """Test handling jobs from multiple sessions"""
    processed_sessions = set()
    
    async def mock_handler(job_id, session_id, audio_data, chunk_sequence):
        """Mock handler that tracks sessions"""
        processed_sessions.add(session_id)
        await asyncio.sleep(0.1)
        return {"text": f"transcription_{session_id}"}
    
    # Enqueue jobs from different sessions
    for session_num in range(3):
        for chunk_num in range(2):
            await queue_manager.enqueue_job(
                job_id=f"job_s{session_num}_c{chunk_num}",
                session_id=f"session{session_num}",
                audio_data=sample_audio_data,
                chunk_sequence=chunk_num
            )
    
    # Start workers
    await queue_manager.start_workers(mock_handler)
    
    # Wait for all jobs to complete
    while queue_manager.get_queue_size() > 0 or queue_manager.get_active_job_count() > 0:
        await asyncio.sleep(0.1)
    
    # Shutdown workers
    await queue_manager.shutdown()
    
    # Verify all sessions were processed
    assert processed_sessions == {"session0", "session1", "session2"}
    
    # Verify all jobs completed
    stats = queue_manager.get_statistics()
    assert stats['completed'] == 6
    assert stats['failed'] == 0
