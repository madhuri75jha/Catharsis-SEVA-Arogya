"""
AWS Transcribe Streaming Manager

Manages real-time streaming transcription using AWS Transcribe Medical streaming API.
"""

import asyncio
import time
from typing import Optional, Callable
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
from utils.logger import get_logger

logger = get_logger(__name__)


class TranscribeResultHandler(TranscriptResultStreamHandler):
    """
    Handler for AWS Transcribe streaming results
    
    Processes partial and final transcription results and emits them via callback.
    """
    
    def __init__(self, session_id: str, result_callback: Callable, output_stream=None):
        """
        Initialize result handler
        
        Args:
            session_id: Session identifier for routing results
            result_callback: Callback function to emit results
            output_stream: Output stream for handler (optional)
        """
        super().__init__(output_stream if output_stream else asyncio.Queue())
        self.session_id = session_id
        self.result_callback = result_callback
        self._result_count = 0
        
        logger.debug(f"TranscribeResultHandler initialized for session: {session_id}")
    
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        """
        Handle transcription result events
        
        Args:
            transcript_event: Transcription event from AWS Transcribe
        """
        try:
            results = transcript_event.transcript.results
            
            for result in results:
                if result.alternatives:
                    transcript = result.alternatives[0].transcript
                    is_partial = result.is_partial
                    
                    # Skip empty transcripts
                    if not transcript or not transcript.strip():
                        continue
                    
                    self._result_count += 1
                    
                    # Get confidence score if available
                    confidence = None
                    if result.alternatives[0].items:
                        confidences = [item.confidence for item in result.alternatives[0].items 
                                     if hasattr(item, 'confidence') and item.confidence is not None]
                        if confidences:
                            confidence = sum(confidences) / len(confidences)
                    
                    # Emit result via callback
                    result_data = {
                        'type': 'transcription_result',
                        'is_partial': is_partial,
                        'text': transcript,
                        'segment_id': f"{self.session_id}_{self._result_count}",
                        'timestamp': time.time(),
                        'confidence': confidence
                    }
                    
                    logger.debug(f"Transcription result: session={self.session_id}, "
                               f"partial={is_partial}, text='{transcript[:50]}...'")
                    
                    # Call the callback (should be thread-safe)
                    self.result_callback(self.session_id, result_data)
                    
        except Exception as e:
            logger.error(f"Error handling transcript event: {str(e)}")


class TranscribeStreamingManager:
    """
    Manages AWS Transcribe Medical streaming sessions
    
    Features:
    - Initialize streaming transcription sessions
    - Send audio chunks to AWS Transcribe
    - Receive and process transcription results
    - Handle errors and stream completion
    """
    
    def __init__(self, region: str):
        """
        Initialize TranscribeStreamingManager
        
        Args:
            region: AWS region (e.g., 'us-east-1')
        """
        self.region = region
        self._active_streams = {}
        
        logger.info(f"TranscribeStreamingManager initialized: region={region}")
    
    async def start_stream(self, 
                          session_id: str,
                          sample_rate: int,
                          result_callback: Callable,
                          language_code: str = 'en-US',
                          specialty: str = 'PRIMARYCARE',
                          media_encoding: str = 'pcm') -> dict:
        """
        Start a streaming transcription session
        
        Args:
            session_id: Unique session identifier
            sample_rate: Audio sample rate (8000, 16000, or 48000)
            result_callback: Callback function for results (session_id, result_data)
            language_code: Language code (default: 'en-US')
            specialty: Medical specialty (default: 'PRIMARYCARE')
            media_encoding: Media encoding (default: 'pcm')
            
        Returns:
            Dictionary with stream info: {
                'client': TranscribeStreamingClient,
                'stream': stream object,
                'audio_queue': asyncio.Queue for audio chunks,
                'handler': result handler
            }
            
        Raises:
            RuntimeError: If stream initialization fails
        """
        try:
            logger.info(f"Starting transcribe stream: session={session_id}, "
                       f"sample_rate={sample_rate}, language={language_code}")
            
            # Create client
            client = TranscribeStreamingClient(region=self.region)
            
            # Create audio queue for streaming
            audio_queue = asyncio.Queue()
            
            # Create result handler
            handler = TranscribeResultHandler(session_id, result_callback)
            
            # Audio stream generator
            async def audio_generator():
                """Generate audio chunks from queue"""
                while True:
                    chunk = await audio_queue.get()
                    if chunk is None:  # End signal
                        break
                    yield chunk
            
            # Start streaming transcription
            stream = await client.start_stream_transcription(
                language_code=language_code,
                media_sample_rate_hz=sample_rate,
                media_encoding=media_encoding,
                vocabulary_name=None,  # Optional: custom medical vocabulary
                session_id=session_id
            )
            
            # Store stream info
            stream_info = {
                'client': client,
                'stream': stream,
                'audio_queue': audio_queue,
                'handler': handler,
                'session_id': session_id
            }
            
            self._active_streams[session_id] = stream_info
            
            # Start result handler in background
            asyncio.create_task(self._handle_results(stream_info))
            
            logger.info(f"Transcribe stream started: session={session_id}")
            
            return stream_info
            
        except Exception as e:
            logger.error(f"Failed to start transcribe stream: {str(e)}")
            raise RuntimeError(f"Failed to start transcription: {str(e)}")
    
    async def _handle_results(self, stream_info: dict):
        """
        Background task to handle transcription results
        
        Args:
            stream_info: Stream information dictionary
        """
        session_id = stream_info['session_id']
        stream = stream_info['stream']
        handler = stream_info['handler']
        
        try:
            async for event in stream.output_stream:
                if isinstance(event, TranscriptEvent):
                    await handler.handle_transcript_event(event)
                    
        except Exception as e:
            logger.error(f"Error in result handler: session={session_id}, error={str(e)}")
    
    async def send_audio_chunk(self, session_id: str, chunk: bytes) -> None:
        """
        Send audio chunk to active stream
        
        Args:
            session_id: Session identifier
            chunk: PCM audio data
            
        Raises:
            RuntimeError: If session not found or send fails
        """
        stream_info = self._active_streams.get(session_id)
        
        if not stream_info:
            raise RuntimeError(f"No active stream for session: {session_id}")
        
        try:
            audio_queue = stream_info['audio_queue']
            await audio_queue.put(chunk)
            
        except Exception as e:
            logger.error(f"Failed to send audio chunk: session={session_id}, error={str(e)}")
            raise RuntimeError(f"Failed to send audio: {str(e)}")
    
    async def end_stream(self, session_id: str) -> None:
        """
        End streaming transcription session
        
        Args:
            session_id: Session identifier
        """
        stream_info = self._active_streams.get(session_id)
        
        if not stream_info:
            logger.warning(f"No active stream to end: session={session_id}")
            return
        
        try:
            # Send end signal to audio queue
            audio_queue = stream_info['audio_queue']
            await audio_queue.put(None)
            
            # Remove from active streams
            self._active_streams.pop(session_id, None)
            
            logger.info(f"Transcribe stream ended: session={session_id}")
            
        except Exception as e:
            logger.error(f"Error ending stream: session={session_id}, error={str(e)}")
    
    def get_active_stream_count(self) -> int:
        """
        Get number of active streams
        
        Returns:
            Active stream count
        """
        return len(self._active_streams)
    
    async def cleanup_all_streams(self) -> int:
        """
        Clean up all active streams (for graceful shutdown)
        
        Returns:
            Number of streams cleaned up
        """
        session_ids = list(self._active_streams.keys())
        
        for session_id in session_ids:
            try:
                await self.end_stream(session_id)
            except Exception as e:
                logger.error(f"Error cleaning up stream: session={session_id}, error={str(e)}")
        
        count = len(session_ids)
        logger.info(f"Cleaned up {count} transcribe streams")
        
        return count
