"""
Flask-SocketIO Event Handlers for Real-Time Audio Transcription Streaming

Handles WebSocket connections, audio streaming, and transcription result delivery.
"""

import uuid
import time
from datetime import datetime
from flask import session, request
from flask_socketio import emit, disconnect
from utils.logger import get_logger
from aws_services.session_manager import SessionManager
from aws_services.audio_buffer import AudioBuffer
from aws_services.transcribe_streaming_manager import TranscribeStreamingManager

logger = get_logger(__name__)

# Global managers (initialized in init_socketio_handlers)
session_manager = None
transcribe_streaming_manager = None
database_manager = None
storage_manager = None


def init_socketio_handlers(socketio_instance, db_mgr, storage_mgr, config_mgr):
    """
    Initialize SocketIO handlers with required managers
    
    Args:
        socketio_instance: Flask-SocketIO instance
        db_mgr: DatabaseManager instance
        storage_mgr: StorageManager instance
        config_mgr: ConfigManager instance
    """
    global session_manager, transcribe_streaming_manager, database_manager, storage_manager
    
    database_manager = db_mgr
    storage_manager = storage_mgr
    
    # Initialize session manager
    idle_timeout = config_mgr.get('stream_idle_timeout_seconds', 900)
    session_manager = SessionManager(max_sessions=100, idle_timeout=idle_timeout)
    
    # Initialize transcribe streaming manager
    region = config_mgr.get('aws_transcribe_region') or config_mgr.get('aws_region')
    transcribe_streaming_manager = TranscribeStreamingManager(region=region)
    
    logger.info("SocketIO handlers initialized")
    
    # Register event handlers
    register_handlers(socketio_instance)
    
    # Start background tasks
    start_background_tasks(socketio_instance)
    
    # Start transcription queue workers
    start_transcription_workers(socketio_instance)


def emit_transcription_progress(socketio, consultation_id, clip_id, status, 
                                queue_position=None, partial_text=None, 
                                final_text=None, error_message=None, request_sid=None):
    """
    Emit transcription progress event with real-time status updates
    
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.8, 11.3, 11.4
    
    Args:
        socketio: SocketIO instance
        consultation_id: Consultation identifier
        clip_id: Clip identifier
        status: Status string ('queued', 'transcribing', 'completed', 'failed')
        queue_position: Queue position for queued jobs (optional)
        partial_text: Partial transcription result (optional)
        final_text: Final transcription result (optional)
        error_message: Error message if failed (optional)
        request_sid: Socket.IO request SID for targeted emission (optional)
    """
    try:
        event_data = {
            'type': 'transcription_progress',
            'consultation_id': consultation_id,
            'clip_id': clip_id,
            'status': status,
            'timestamp': time.time()
        }
        
        if queue_position is not None:
            event_data['queue_position'] = queue_position
        
        if partial_text:
            event_data['partial_text'] = partial_text
            event_data['is_partial'] = True
        
        if final_text:
            event_data['final_text'] = final_text
            event_data['is_final'] = True
        
        if error_message:
            event_data['error_message'] = error_message
        
        # Emit to specific room if request_sid provided, otherwise broadcast
        if request_sid:
            socketio.emit('transcription_progress', event_data, room=request_sid)
        else:
            socketio.emit('transcription_progress', event_data)
        
        logger.debug(f"Transcription progress emitted: consultation_id={consultation_id}, "
                    f"clip_id={clip_id}, status={status}")
        
    except Exception as e:
        logger.error(f"Failed to emit transcription progress: {str(e)}")


def register_handlers(socketio):
    """Register all SocketIO event handlers"""

    def normalize_session_id(raw_session_id):
        """
        Ensure session_id is a UUID string accepted by AWS Transcribe Medical.

        Returns a canonical UUID string. If raw_session_id is invalid or missing,
        generates a new UUID.
        """
        if raw_session_id:
            try:
                return str(uuid.UUID(str(raw_session_id)))
            except (ValueError, TypeError, AttributeError):
                logger.warning(f"Invalid session_id format received: {raw_session_id}. Generating UUID.")
        return str(uuid.uuid4())
    
    @socketio.on('chunk_upload')
    def handle_chunk_upload(data):
        """
        Handle audio chunk upload for async transcription
        
        Enqueues transcription jobs for each chunk and returns immediate acknowledgment.
        Requirements: 11.1, 11.2, 2.3, 3.4
        """
        try:
            if not isinstance(data, dict):
                logger.warning(f"Invalid chunk_upload payload type: {type(data)}")
                emit('error', {
                    'type': 'error',
                    'error_code': 'INVALID_PAYLOAD',
                    'message': 'Invalid chunk upload payload',
                    'recoverable': False,
                    'timestamp': time.time()
                })
                return
            
            consultation_id = data.get('consultation_id')
            clip_id = data.get('clip_id')
            chunk_sequence = data.get('chunk_sequence', 0)
            audio_data = data.get('audio_data')  # Base64 encoded
            
            if not consultation_id or not clip_id or not audio_data:
                logger.warning("Missing required fields in chunk_upload")
                emit('error', {
                    'type': 'error',
                    'error_code': 'MISSING_FIELDS',
                    'message': 'Missing consultation_id, clip_id, or audio_data',
                    'recoverable': False,
                    'timestamp': time.time()
                })
                return
            
            user_id = session.get('user_id')
            if not user_id:
                logger.warning("Unauthenticated chunk_upload attempt")
                emit('error', {
                    'type': 'error',
                    'error_code': 'UNAUTHORIZED',
                    'message': 'User not authenticated',
                    'recoverable': False,
                    'timestamp': time.time()
                })
                return
            
            # Decode audio data
            import base64
            try:
                audio_bytes = base64.b64decode(audio_data, validate=True)
            except Exception as decode_error:
                logger.warning(f"Invalid base64 audio in chunk_upload: {decode_error}")
                emit('error', {
                    'type': 'error',
                    'error_code': 'INVALID_AUDIO_DATA',
                    'message': 'Invalid audio data format',
                    'recoverable': True,
                    'timestamp': time.time()
                })
                return
            
            if not audio_bytes:
                logger.warning(f"Empty audio chunk received: clip_id={clip_id}")
                return
            
            # Generate job_id for this chunk
            job_id = f"{clip_id}_chunk_{chunk_sequence}"
            
            # Enqueue transcription job
            from app import transcription_queue_manager
            import asyncio
            
            try:
                # Create event loop for async operation
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Enqueue the job
                job_metadata = loop.run_until_complete(
                    transcription_queue_manager.enqueue_job(
                        job_id=job_id,
                        session_id=consultation_id,
                        audio_data=audio_bytes,
                        chunk_sequence=chunk_sequence
                    )
                )
                
                loop.close()
                
                # Get queue position
                queue_position = transcription_queue_manager.get_queue_size()
                
                # Emit immediate acknowledgment
                emit('chunk_queued', {
                    'type': 'chunk_queued',
                    'consultation_id': consultation_id,
                    'clip_id': clip_id,
                    'chunk_sequence': chunk_sequence,
                    'job_id': job_id,
                    'queue_position': queue_position,
                    'timestamp': time.time()
                })
                
                logger.info(f"Chunk uploaded and queued: consultation_id={consultation_id}, "
                           f"clip_id={clip_id}, chunk={chunk_sequence}, job_id={job_id}, queue_pos={queue_position}")
                
            except Exception as queue_error:
                logger.error(f"Failed to enqueue transcription job: {str(queue_error)}")
                emit('error', {
                    'type': 'error',
                    'error_code': 'QUEUE_FAILED',
                    'message': 'Failed to queue transcription job',
                    'recoverable': True,
                    'timestamp': time.time()
                })
                return
            
        except Exception as e:
            logger.error(f"Chunk upload error: {str(e)}")
            emit('error', {
                'type': 'error',
                'error_code': 'CHUNK_UPLOAD_FAILED',
                'message': 'Failed to process audio chunk',
                'recoverable': True,
                'timestamp': time.time()
            })
    
    @socketio.on('clip_complete')
    def handle_clip_complete(data):
        """
        Handle clip completion - finalize clip and process remaining chunks
        
        Requirements: 11.6, 11.7, 4.1, 4.2
        """
        try:
            if not isinstance(data, dict):
                logger.warning(f"Invalid clip_complete payload type: {type(data)}")
                emit('error', {
                    'type': 'error',
                    'error_code': 'INVALID_PAYLOAD',
                    'message': 'Invalid clip complete payload',
                    'recoverable': False,
                    'timestamp': time.time()
                })
                return
            
            consultation_id = data.get('consultation_id')
            clip_id = data.get('clip_id')
            
            if not consultation_id or not clip_id:
                logger.warning("Missing required fields in clip_complete")
                emit('error', {
                    'type': 'error',
                    'error_code': 'MISSING_FIELDS',
                    'message': 'Missing consultation_id or clip_id',
                    'recoverable': False,
                    'timestamp': time.time()
                })
                return
            
            user_id = session.get('user_id')
            if not user_id:
                logger.warning("Unauthenticated clip_complete attempt")
                emit('error', {
                    'type': 'error',
                    'error_code': 'UNAUTHORIZED',
                    'message': 'User not authenticated',
                    'recoverable': False,
                    'timestamp': time.time()
                })
                return
            
            # Mark clip as finalized
            # This signals that no more chunks will be uploaded for this clip
            # The transcription queue will process any remaining chunks
            
            logger.info(f"Clip finalized: consultation_id={consultation_id}, clip_id={clip_id}")
            
            # Emit acknowledgment
            emit('clip_finalized', {
                'type': 'clip_finalized',
                'consultation_id': consultation_id,
                'clip_id': clip_id,
                'timestamp': time.time()
            })
            
            # Note: Final transcription result will be emitted via transcription_progress
            # once all chunks are processed
            
        except Exception as e:
            logger.error(f"Clip complete error: {str(e)}")
            emit('error', {
                'type': 'error',
                'error_code': 'CLIP_COMPLETE_FAILED',
                'message': 'Failed to finalize clip',
                'recoverable': True,
                'timestamp': time.time()
            })
    
    @socketio.on('retry_job')
    def handle_retry_job(data):
        """
        Handle manual retry of failed transcription job
        
        Requirements: 2.5, 5.3, 5.4
        """
        try:
            if not isinstance(data, dict):
                logger.warning(f"Invalid retry_job payload type: {type(data)}")
                emit('error', {
                    'type': 'error',
                    'error_code': 'INVALID_PAYLOAD',
                    'message': 'Invalid retry job payload',
                    'recoverable': False,
                    'timestamp': time.time()
                })
                return
            
            job_id = data.get('job_id')
            
            if not job_id:
                logger.warning("Missing job_id in retry_job")
                emit('error', {
                    'type': 'error',
                    'error_code': 'MISSING_FIELDS',
                    'message': 'Missing job_id',
                    'recoverable': False,
                    'timestamp': time.time()
                })
                return
            
            user_id = session.get('user_id')
            if not user_id:
                logger.warning("Unauthenticated retry_job attempt")
                emit('error', {
                    'type': 'error',
                    'error_code': 'UNAUTHORIZED',
                    'message': 'User not authenticated',
                    'recoverable': False,
                    'timestamp': time.time()
                })
                return
            
            # Get transcription queue manager from app context
            from app import transcription_queue_manager
            
            # Retry the job
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(transcription_queue_manager.retry_failed_job(job_id))
            loop.close()
            
            if success:
                logger.info(f"Job retry initiated: job_id={job_id}, user_id={user_id}")
                
                # Emit success
                emit('job_retry_initiated', {
                    'type': 'job_retry_initiated',
                    'job_id': job_id,
                    'timestamp': time.time()
                })
            else:
                logger.warning(f"Job retry failed: job_id={job_id} not found or not in failed state")
                
                emit('error', {
                    'type': 'error',
                    'error_code': 'RETRY_FAILED',
                    'message': 'Job not found or not in failed state',
                    'recoverable': False,
                    'timestamp': time.time()
                })
            
        except Exception as e:
            logger.error(f"Retry job error: {str(e)}")
            emit('error', {
                'type': 'error',
                'error_code': 'RETRY_JOB_FAILED',
                'message': 'Failed to retry job',
                'recoverable': True,
                'timestamp': time.time()
            })
    
    @socketio.on('sync_state')
    def handle_sync_state(data):
        """
        Handle state synchronization after reconnection
        
        Requirements: 5.5, 5.6
        """
        try:
            user_id = session.get('user_id')
            if not user_id:
                logger.warning("Unauthenticated sync_state attempt")
                emit('error', {
                    'type': 'error',
                    'error_code': 'UNAUTHORIZED',
                    'message': 'User not authenticated',
                    'recoverable': False,
                    'timestamp': time.time()
                })
                return
            
            # Get active consultation session
            from app import consultation_session_manager
            active_session = consultation_session_manager.get_active_session(user_id)
            
            # Get pending jobs from queue manager
            from app import transcription_queue_manager
            queue_stats = transcription_queue_manager.get_statistics()
            
            logger.info(f"State sync requested: user_id={user_id}")
            
            # Emit state sync response
            emit('state_synced', {
                'type': 'state_synced',
                'active_session': active_session,
                'queue_statistics': queue_stats,
                'timestamp': time.time()
            })
            
            # Resume status updates for pending jobs
            # This will be handled by the transcription progress emitter
            
        except Exception as e:
            logger.error(f"Sync state error: {str(e)}")
            emit('error', {
                'type': 'error',
                'error_code': 'SYNC_STATE_FAILED',
                'message': 'Failed to synchronize state',
                'recoverable': True,
                'timestamp': time.time()
            })
    
    @socketio.on('connect')
    def handle_connect():
        """Handle WebSocket connection"""
        try:
            # Authenticate using Flask session
            if 'user_id' not in session:
                logger.warning("Unauthenticated connection attempt")
                disconnect()
                return False
            
            user_id = session.get('user_id')
            logger.info(f"WebSocket connected: user={user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            disconnect()
            return False
    
    
    @socketio.on('session_start')
    def handle_session_start(data):
        """Handle session start - initialize transcription"""
        session_id = None
        stream_started = False
        try:
            user_id = session.get('user_id')
            payload = data if isinstance(data, dict) else {}
            session_id = normalize_session_id(payload.get('session_id'))
            quality = payload.get('quality', 'medium')
            
            logger.info(f"Session start: session_id={session_id}, user={user_id}, quality={quality}")
            
            # Get Socket.IO session ID with defensive check
            request_sid = getattr(request, 'sid', None)
            if request_sid is None:
                logger.warning(f"request.sid not available for session {session_id}")
                request_sid = session_id  # Fallback to session_id
            else:
                logger.debug(f"Retrieved request.sid: {request_sid} for session {session_id}")

            # Defensive cleanup: if this socket reconnects/restarts without a clean
            # session_end, clear stale sessions bound to the same request_sid so
            # the next start can still get an acknowledgment promptly.
            stale_session_ids = []
            for existing_id, existing_session in session_manager.get_all_sessions().items():
                if existing_session.request_sid == request_sid and existing_id != session_id:
                    stale_session_ids.append(existing_id)

            for stale_session_id in stale_session_ids:
                try:
                    transcribe_streaming_manager.end_stream(stale_session_id)
                except Exception as cleanup_error:
                    logger.warning(
                        f"Failed ending stale stream for request_sid={request_sid}, "
                        f"session_id={stale_session_id}: {cleanup_error}"
                    )
                finally:
                    session_manager.remove_session(stale_session_id)
                    logger.info(
                        f"Cleaned stale session before new start: "
                        f"request_sid={request_sid}, session_id={stale_session_id}"
                    )
            
            # Create session
            streaming_session = session_manager.create_session(
                session_id=session_id,
                user_id=user_id,
                request_sid=request_sid,
                quality=quality
            )
            
            # Initialize audio buffer
            streaming_session.audio_buffer = AudioBuffer(
                sample_rate=streaming_session.sample_rate,
                max_duration_seconds=1800  # 30 minutes
            )
            
            # Start AWS Transcribe streaming (async)
            def result_callback(sess_id, result_data):
                """Callback to emit transcription results"""
                target_room = None
                try:
                    active_session = session_manager.get_session(sess_id)
                    if active_session:
                        target_room = active_session.request_sid

                        # Persist only final transcript segments once to avoid
                        # duplicate text in DB from repeated partial updates.
                        if not result_data.get('is_partial'):
                            segment_id = result_data.get('segment_id')
                            text = (result_data.get('text') or '').strip()
                            if text:
                                if not hasattr(active_session, 'persisted_final_segments'):
                                    active_session.persisted_final_segments = set()
                                if segment_id not in active_session.persisted_final_segments:
                                    database_manager.append_transcript_text(sess_id, text)
                                    active_session.persisted_final_segments.add(segment_id)
                except Exception:
                    target_room = None

                if target_room:
                    socketio.emit('transcription_result', result_data, room=target_room)
                else:
                    # Fallback: emit without room to avoid silently dropping results.
                    socketio.emit('transcription_result', result_data)
            
            stream_info = transcribe_streaming_manager.start_stream(
                session_id=session_id,
                sample_rate=streaming_session.sample_rate,
                result_callback=result_callback,
                language_code='en-US',
                specialty='PRIMARYCARE'
            )
            stream_started = True
            
            streaming_session.transcribe_stream = stream_info
            streaming_session.result_callback = result_callback
            
            # Create transcription record in database
            from models.transcription import Transcription
            transcription = Transcription(
                user_id=user_id,
                audio_s3_key='pending',  # Will be updated on session end
                job_id=session_id,  # Use session_id as job_id for streaming
                status='IN_PROGRESS'
            )
            
            # Add streaming-specific fields
            transcription_id = transcription.save(database_manager)
            
            if transcription_id:
                # Update with streaming fields
                query = """
                UPDATE transcriptions
                SET session_id = %s, streaming_job_id = %s, is_streaming = TRUE,
                    sample_rate = %s, quality = %s
                WHERE transcription_id = %s
                """
                database_manager.execute_with_retry(
                    query,
                    (session_id, session_id, streaming_session.sample_rate, quality, transcription_id)
                )
            
            # Send acknowledgment
            emit('session_ack', {
                'type': 'session_ack',
                'session_id': session_id,
                'job_id': session_id,
                'status': 'ready',
                'timestamp': time.time()
            })
            
            logger.info(f"Session started successfully: {session_id}")
            
        except RuntimeError as e:
            # Session limit or other runtime error
            logger.error(f"Session start failed: {str(e)}")
            if session_id:
                try:
                    if stream_started:
                        transcribe_streaming_manager.end_stream(session_id)
                except Exception as cleanup_error:
                    logger.warning(f"Failed stream cleanup after session start error: {cleanup_error}")
                finally:
                    session_manager.remove_session(session_id)
            emit('error', {
                'type': 'error',
                'error_code': 'SESSION_LIMIT_EXCEEDED' if 'capacity' in str(e) else 'SESSION_START_FAILED',
                'message': str(e),
                'recoverable': False,
                'timestamp': time.time()
            })
            
        except Exception as e:
            logger.error(f"Session start error: {str(e)}")
            if session_id:
                try:
                    if stream_started:
                        transcribe_streaming_manager.end_stream(session_id)
                except Exception as cleanup_error:
                    logger.warning(f"Failed stream cleanup after session start exception: {cleanup_error}")
                finally:
                    session_manager.remove_session(session_id)
            emit('error', {
                'type': 'error',
                'error_code': 'SESSION_START_FAILED',
                'message': 'Failed to start transcription session',
                'recoverable': True,
                'timestamp': time.time()
            })
    
    
    @socketio.on('audio_chunk')
    def handle_audio_chunk(data):
        """Handle incoming audio chunk"""
        try:
            # Extract session_id from data or use a stored mapping
            # For binary data, we need to handle it differently
            if isinstance(data, bytes):
                # Binary audio data
                # First byte should be message type (0x01)
                if len(data) < 2 or data[0] != 0x01:
                    logger.warning("Invalid audio chunk format")
                    return
                
                audio_data = data[1:]  # Skip type byte
                
                # Get session from request context (stored during session_start)
                # For now, we'll need to track this differently
                # This is a simplified version - in production, you'd need better session tracking
                
                logger.debug(f"Received audio chunk: {len(audio_data)} bytes")
                
                # TODO: Implement proper session tracking for binary messages
                # For now, emit error
                emit('error', {
                    'type': 'error',
                    'error_code': 'IMPLEMENTATION_PENDING',
                    'message': 'Binary audio streaming implementation pending',
                    'recoverable': False,
                    'timestamp': time.time()
                })
                
            else:
                # JSON data with session_id
                if not isinstance(data, dict):
                    logger.warning(f"Invalid audio chunk payload type: {type(data)}")
                    return

                session_id = data.get('session_id')
                audio_data = data.get('audio_data')  # Base64 encoded
                chunk_id = data.get('chunk_id')
                
                if not session_id or not audio_data:
                    logger.warning("Missing session_id or audio_data")
                    return
                
                # Get session
                streaming_session = session_manager.get_session(session_id)
                if not streaming_session:
                    logger.warning(f"Session not found: {session_id}")
                    emit('error', {
                        'type': 'error',
                        'error_code': 'SESSION_NOT_FOUND',
                        'message': 'Session not found or expired',
                        'recoverable': False,
                        'timestamp': time.time()
                    })
                    return
                
                # Decode audio data
                import base64
                try:
                    audio_bytes = base64.b64decode(audio_data, validate=True)
                except Exception:
                    logger.warning(f"Invalid base64 audio payload: session={session_id}")
                    emit('error', {
                        'type': 'error',
                        'error_code': 'INVALID_AUDIO_CHUNK',
                        'message': 'Invalid audio chunk format',
                        'recoverable': True,
                        'timestamp': time.time()
                    })
                    return

                if not audio_bytes:
                    logger.warning(f"Empty audio payload received: session={session_id}")
                    return

                # Optional chunk sequencing: drop duplicate/replayed chunks.
                if chunk_id is not None:
                    try:
                        chunk_id_int = int(chunk_id)
                    except (TypeError, ValueError):
                        logger.warning(f"Invalid chunk_id: session={session_id}, chunk_id={chunk_id}")
                        chunk_id_int = None

                    if chunk_id_int is not None:
                        last_chunk_id = getattr(streaming_session, 'last_chunk_id', -1)
                        if chunk_id_int <= last_chunk_id:
                            logger.debug(
                                f"Dropped duplicate/replayed chunk: session={session_id}, "
                                f"chunk_id={chunk_id_int}, last_chunk_id={last_chunk_id}"
                            )
                            return
                        streaming_session.last_chunk_id = chunk_id_int
                
                # Buffer audio for later S3 upload
                streaming_session.audio_buffer.append(audio_bytes)
                
                # Forward to AWS Transcribe
                try:
                    transcribe_streaming_manager.send_audio_chunk(session_id, audio_bytes)
                except RuntimeError as stream_error:
                    logger.warning(f"Audio stream unavailable: session={session_id}, error={stream_error}")

                    # Attempt one in-place stream recovery for transient worker failures.
                    try:
                        transcribe_streaming_manager.end_stream(session_id)
                    except Exception as end_error:
                        logger.warning(f"Failed ending broken stream: session={session_id}, error={end_error}")

                    try:
                        result_callback = getattr(streaming_session, 'result_callback', None)
                        if result_callback is None:
                            raise RuntimeError("Missing result callback for stream recovery")

                        stream_info = transcribe_streaming_manager.start_stream(
                            session_id=session_id,
                            sample_rate=streaming_session.sample_rate,
                            result_callback=result_callback,
                            language_code='en-US',
                            specialty='PRIMARYCARE'
                        )
                        streaming_session.transcribe_stream = stream_info
                        transcribe_streaming_manager.send_audio_chunk(session_id, audio_bytes)
                        logger.info(f"Recovered transcription stream: session={session_id}")
                    except Exception as restart_error:
                        logger.error(
                            f"Failed to recover transcription stream: session={session_id}, "
                            f"error={restart_error}"
                        )
                        emit('error', {
                            'type': 'error',
                            'error_code': 'STREAM_NOT_READY',
                            'message': 'Transcription stream is not ready',
                            'recoverable': False,
                            'timestamp': time.time()
                        })
                        return
                
                # Update activity
                session_manager.update_activity(session_id)
                
        except Exception as e:
            logger.error(f"Audio chunk error: {str(e)}")
            emit('error', {
                'type': 'error',
                'error_code': 'AUDIO_PROCESSING_FAILED',
                'message': 'Failed to process audio chunk',
                'recoverable': True,
                'timestamp': time.time()
            })
    
    
    @socketio.on('session_end')
    def handle_session_end(data):
        """Handle session end - finalize transcription"""
        session_id = None
        try:
            payload = data if isinstance(data, dict) else {}
            session_id = payload.get('session_id')
            
            if not session_id:
                logger.warning("Missing session_id in session_end")
                return
            
            logger.info(f"Session end: {session_id}")
            
            # Remove session first so failures below do not leave stale session
            # state that can block/impact future starts from the same device.
            streaming_session = session_manager.remove_session(session_id)
            if not streaming_session:
                logger.warning(f"Session not found: {session_id}")
                return
            
            # End transcribe stream
            transcribe_streaming_manager.end_stream(session_id)
            
            # Finalize audio buffer to MP3
            audio_buffer = streaming_session.audio_buffer
            mp3_data = audio_buffer.finalize_to_mp3(bitrate=64)
            
            # Generate S3 key
            user_id = streaming_session.user_id
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            s3_key = f"audio/{user_id}/{timestamp}_{session_id}.mp3"
            
            # Upload to S3
            success = storage_manager.upload_audio_bytes(mp3_data, s3_key)
            
            if not success:
                logger.error(f"Failed to upload audio to S3: {session_id}")
                emit('error', {
                    'type': 'error',
                    'error_code': 'S3_UPLOAD_FAILED',
                    'message': 'Failed to save audio file',
                    'recoverable': False,
                    'timestamp': time.time()
                })
                return
            
            # Update transcription record
            query = """
            UPDATE transcriptions
            SET audio_s3_key = %s, status = 'COMPLETED',
                audio_duration_seconds = %s, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = %s
            """
            database_manager.execute_with_retry(
                query,
                (s3_key, audio_buffer.get_total_duration(), session_id)
            )
            
            # Send completion message
            emit('session_complete', {
                'type': 'session_complete',
                'session_id': session_id,
                'audio_s3_key': s3_key,
                'total_duration': audio_buffer.get_total_duration(),
                'timestamp': time.time()
            })
            
            logger.info(f"Session completed successfully: {session_id}")
            
        except Exception as e:
            logger.error(f"Session end error: {str(e)}")
            if session_id:
                # Ensure no stale session survives session_end failures.
                session_manager.remove_session(session_id)
            emit('error', {
                'type': 'error',
                'error_code': 'SESSION_END_FAILED',
                'message': 'Failed to complete session',
                'recoverable': False,
                'timestamp': time.time()
            })
    
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle WebSocket disconnection"""
        try:
            user_id = session.get('user_id')
            request_sid = getattr(request, 'sid', None)
            logger.info(f"WebSocket disconnected: user={user_id}")
            
            # Clean up any active sessions for this socket connection.
            if request_sid:
                stale_session_ids = []
                for existing_id, existing_session in session_manager.get_all_sessions().items():
                    if existing_session.request_sid == request_sid:
                        stale_session_ids.append(existing_id)

                for stale_session_id in stale_session_ids:
                    try:
                        transcribe_streaming_manager.end_stream(stale_session_id)
                    except Exception as cleanup_error:
                        logger.warning(
                            f"Failed ending stream on disconnect: "
                            f"session_id={stale_session_id}, error={cleanup_error}"
                        )
                    finally:
                        session_manager.remove_session(stale_session_id)
                        logger.info(
                            f"Cleaned session on disconnect: "
                            f"request_sid={request_sid}, session_id={stale_session_id}"
                        )
            
        except Exception as e:
            logger.error(f"Disconnect error: {str(e)}")


def start_background_tasks(socketio):
    """Start background tasks for session cleanup and heartbeat"""
    
    def cleanup_idle_sessions():
        """Background task to clean up idle sessions"""
        while True:
            try:
                socketio.sleep(60)  # Run every 60 seconds
                count = session_manager.cleanup_idle_sessions()
                if count > 0:
                    logger.info(f"Cleaned up {count} idle sessions")
            except Exception as e:
                logger.error(f"Idle session cleanup error: {str(e)}")
    
    def send_heartbeats():
        """Background task to send heartbeat messages"""
        while True:
            try:
                socketio.sleep(30)  # Send every 30 seconds
                socketio.emit('heartbeat', {
                    'type': 'heartbeat',
                    'timestamp': time.time()
                })
            except Exception as e:
                logger.error(f"Heartbeat error: {str(e)}")
    
    # Start background tasks
    socketio.start_background_task(cleanup_idle_sessions)
    socketio.start_background_task(send_heartbeats)
    
    logger.info("Background tasks started")


def shutdown_handler(socketio_instance):
    """
    Graceful shutdown handler for cleaning up resources
    
    Call this function when the application is shutting down.
    """
    logger.info("Initiating graceful shutdown...")
    
    try:
        # Get all active sessions
        if session_manager:
            active_sessions = session_manager.get_all_sessions()
            logger.info(f"Closing {len(active_sessions)} active sessions")
            
            # Close all WebSocket connections
            for session_id, streaming_session in active_sessions.items():
                try:
                    # Emit shutdown message to client
                    socketio_instance.emit('server_shutdown', {
                        'type': 'server_shutdown',
                        'message': 'Server is shutting down',
                        'timestamp': time.time()
                    }, room=streaming_session.request_sid)
                    
                    # End transcribe stream
                    if transcribe_streaming_manager:
                        transcribe_streaming_manager.end_stream(session_id)
                    
                except Exception as e:
                    logger.error(f"Error closing session {session_id}: {str(e)}")
            
            # Clear all sessions
            session_manager.clear_all()
        
        # Cleanup transcribe streams
        if transcribe_streaming_manager:
            count = transcribe_streaming_manager.cleanup_all_streams()
            logger.info(f"Cleaned up {count} transcribe streams")
        
        logger.info("Graceful shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during graceful shutdown: {str(e)}")


def start_transcription_workers(socketio):
    """
    Start transcription queue workers
    
    Requirements: 2.6, 4.1, 7.4
    """
    from app import transcription_queue_manager
    import asyncio
    
    async def transcription_handler(job_id, session_id, audio_data, chunk_sequence):
        """
        Handle transcription for a queued job
        
        Args:
            job_id: Job identifier
            session_id: Session/consultation identifier
            audio_data: Audio bytes to transcribe
            chunk_sequence: Chunk sequence number
            
        Returns:
            dict: Transcription result
            
        Raises:
            Exception: If transcription fails
        """
        try:
            logger.info(f"Processing transcription job: job_id={job_id}, session_id={session_id}, chunk={chunk_sequence}")
            
            # Extract clip_id from job_id (format: {clip_id}_chunk_{sequence})
            clip_id = job_id.rsplit('_chunk_', 1)[0]
            
            # Emit progress: transcribing
            emit_transcription_progress(
                socketio,
                consultation_id=session_id,
                clip_id=clip_id,
                status='transcribing'
            )
            
            # Transcribe audio using AWS Transcribe
            # For now, use a placeholder - this would call the actual transcription service
            # In production, this would integrate with TranscribeStreamingManager or batch transcription
            
            # Placeholder transcription result
            transcript_text = f"[Transcription for chunk {chunk_sequence}]"
            
            # Store transcription in database
            if database_manager:
                try:
                    # Get user_id from session (would need to be passed through)
                    # For now, use a placeholder
                    user_id = "system"
                    
                    # Insert transcription
                    insert_query = """
                    INSERT INTO transcriptions 
                    (job_id, user_id, consultation_id, clip_order, chunk_sequence, transcript_text, status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (job_id) DO UPDATE SET
                        transcript_text = EXCLUDED.transcript_text,
                        status = EXCLUDED.status,
                        updated_at = NOW()
                    """
                    database_manager.execute_with_retry(
                        insert_query,
                        (job_id, user_id, session_id, 1, chunk_sequence, transcript_text, 'completed')
                    )
                    
                except Exception as db_error:
                    logger.error(f"Failed to store transcription: {str(db_error)}")
            
            # Emit progress: completed
            emit_transcription_progress(
                socketio,
                consultation_id=session_id,
                clip_id=clip_id,
                status='completed',
                final_text=transcript_text
            )
            
            logger.info(f"Transcription job completed: job_id={job_id}")
            
            return {
                'job_id': job_id,
                'transcript_text': transcript_text,
                'status': 'completed'
            }
            
        except Exception as e:
            logger.error(f"Transcription job failed: job_id={job_id}, error={str(e)}")
            
            # Emit progress: failed
            clip_id = job_id.rsplit('_chunk_', 1)[0]
            emit_transcription_progress(
                socketio,
                consultation_id=session_id,
                clip_id=clip_id,
                status='failed',
                error_message=str(e)
            )
            
            raise
    
    # Start workers in background
    def start_workers():
        """Start async workers"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(
                transcription_queue_manager.start_workers(transcription_handler)
            )
        except Exception as e:
            logger.error(f"Error starting transcription workers: {str(e)}")
        finally:
            loop.close()
    
    # Start workers in background thread
    import eventlet
    eventlet.spawn(start_workers)
    
    logger.info("Transcription queue workers started")
