"""
AWS Transcribe Streaming Manager

Manages real-time streaming transcription using AWS Transcribe Medical streaming API.
"""

import asyncio
import threading
import time
from typing import Callable
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
        self._last_emitted_by_segment = {}
        
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
                    
                    # Use AWS result_id as stable segment key so partial updates
                    # replace previous text instead of rendering as new segments.
                    result_id = getattr(result, 'result_id', None) or getattr(result, 'resultId', None)
                    if result_id:
                        segment_id = f"{self.session_id}_{result_id}"
                    else:
                        self._result_count += 1
                        segment_id = f"{self.session_id}_{self._result_count}"

                    # Avoid emitting identical repeated partial updates.
                    previous = self._last_emitted_by_segment.get(segment_id)
                    current = (transcript, bool(is_partial))
                    if previous == current:
                        continue
                    self._last_emitted_by_segment[segment_id] = current
                    
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
                        'segment_id': segment_id,
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

    @staticmethod
    def _start_session_loop() -> tuple:
        """
        Start a dedicated asyncio event loop in a background thread.

        Returns:
            (loop, thread)
        """
        loop = asyncio.new_event_loop()

        def _runner():
            asyncio.set_event_loop(loop)
            loop.run_forever()

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        return loop, thread

    @staticmethod
    def _run_in_loop(loop: asyncio.AbstractEventLoop, coro):
        """
        Execute coroutine in a specific loop and wait for completion.
        """
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()

    async def _send_audio_worker(self, session_id: str, stream, audio_queue: asyncio.Queue):
        """
        Consume queued audio chunks and forward them to AWS Transcribe input stream.
        Runs inside the session's dedicated event loop.
        """
        try:
            while True:
                chunk = await audio_queue.get()
                if chunk is None:
                    break
                await stream.input_stream.send_audio_event(audio_chunk=chunk)
        except Exception as e:
            logger.error(f"Audio sender worker error: session={session_id}, error={str(e)}")
            raise
    
    def start_stream(self,
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
            Dictionary with stream info.
            
        Raises:
            RuntimeError: If stream initialization fails
        """
        try:
            logger.info(f"Starting transcribe stream: session={session_id}, "
                       f"sample_rate={sample_rate}, language={language_code}")
            
            # Start dedicated loop for this streaming session.
            # AWS Transcribe stream read/write must stay on the same active loop.
            session_loop, session_thread = self._start_session_loop()

            async def _initialize():
                client = TranscribeStreamingClient(region=self.region)
                stream = await client.start_stream_transcription(
                    language_code=language_code,
                    media_sample_rate_hz=sample_rate,
                    media_encoding=media_encoding,
                    vocabulary_name=None,  # Optional: custom medical vocabulary
                    session_id=session_id
                )
                handler = TranscribeResultHandler(session_id, result_callback)
                audio_queue = asyncio.Queue()

                stream_info_local = {
                    'client': client,
                    'stream': stream,
                    'handler': handler,
                    'audio_queue': audio_queue,
                    'session_id': session_id,
                    'loop': session_loop,
                    'thread': session_thread,
                    'results_task': None,
                    'sender_task': None,
                }
                stream_info_local['results_task'] = asyncio.create_task(
                    self._handle_results(stream_info_local)
                )
                stream_info_local['sender_task'] = asyncio.create_task(
                    self._send_audio_worker(session_id, stream, audio_queue)
                )
                return stream_info_local

            stream_info = self._run_in_loop(session_loop, _initialize())
            self._active_streams[session_id] = stream_info
            
            logger.info(f"Transcribe stream started: session={session_id}")
            
            return stream_info
            
        except Exception as e:
            # Best-effort cleanup if loop/thread were created.
            if 'session_loop' in locals():
                try:
                    session_loop.call_soon_threadsafe(session_loop.stop)
                except Exception:
                    pass
            if 'session_thread' in locals() and session_thread.is_alive():
                session_thread.join(timeout=2)
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
    
    def send_audio_chunk(self, session_id: str, chunk: bytes) -> None:
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
            sender_task = stream_info.get('sender_task')
            if sender_task and sender_task.done():
                task_error = None
                try:
                    task_error = sender_task.exception()
                except Exception:
                    task_error = None
                raise RuntimeError(
                    f"Audio sender task stopped for session {session_id}: {task_error}"
                )

            results_task = stream_info.get('results_task')
            if results_task and results_task.done():
                task_error = None
                try:
                    task_error = results_task.exception()
                except Exception:
                    task_error = None
                raise RuntimeError(
                    f"Result handler task stopped for session {session_id}: {task_error}"
                )

            session_loop = stream_info['loop']
            audio_queue = stream_info['audio_queue']
            session_loop.call_soon_threadsafe(audio_queue.put_nowait, chunk)
        except Exception as e:
            logger.error(f"Failed to send audio chunk: session={session_id}, error={str(e)}")
            raise RuntimeError(f"Failed to send audio: {str(e)}")
    
    def end_stream(self, session_id: str) -> None:
        """
        End streaming transcription session
        
        Args:
            session_id: Session identifier
        """
        stream_info = self._active_streams.get(session_id)
        
        if not stream_info:
            logger.warning(f"No active stream to end: session={session_id}")
            return
        
        session_loop = None
        session_thread = None
        try:
            stream = stream_info['stream']
            session_loop = stream_info['loop']
            session_thread = stream_info.get('thread')
            results_task = stream_info.get('results_task')
            sender_task = stream_info.get('sender_task')
            audio_queue = stream_info.get('audio_queue')

            async def _end():
                if audio_queue is not None:
                    await audio_queue.put(None)

                if sender_task:
                    try:
                        await asyncio.wait_for(sender_task, timeout=5)
                    except Exception:
                        pass

                try:
                    await stream.input_stream.end_stream()
                except Exception as end_err:
                    logger.warning(f"Error ending input stream: session={session_id}, error={str(end_err)}")

                if results_task:
                    try:
                        await asyncio.wait_for(results_task, timeout=5)
                    except Exception:
                        # Do not block teardown on result-task drain issues
                        pass

            self._run_in_loop(session_loop, _end())
        except Exception as e:
            logger.error(f"Error ending stream: session={session_id}, error={str(e)}")
        finally:
            # Remove from active streams and tear down loop thread.
            self._active_streams.pop(session_id, None)
            if session_loop:
                try:
                    session_loop.call_soon_threadsafe(session_loop.stop)
                except Exception:
                    pass
            if session_thread and session_thread.is_alive():
                session_thread.join(timeout=2)

            logger.info(f"Transcribe stream ended: session={session_id}")
    
    def get_active_stream_count(self) -> int:
        """
        Get number of active streams
        
        Returns:
            Active stream count
        """
        return len(self._active_streams)
    
    def cleanup_all_streams(self) -> int:
        """
        Clean up all active streams (for graceful shutdown)
        
        Returns:
            Number of streams cleaned up
        """
        session_ids = list(self._active_streams.keys())
        
        for session_id in session_ids:
            try:
                self.end_stream(session_id)
            except Exception as e:
                logger.error(f"Error cleaning up stream: session={session_id}, error={str(e)}")
        
        count = len(session_ids)
        logger.info(f"Cleaned up {count} transcribe streams")
        
        return count
