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
    session_manager = SessionManager(max_sessions=100, idle_timeout=300)
    
    # Initialize transcribe streaming manager
    region = config_mgr.get('aws_transcribe_region') or config_mgr.get('aws_region')
    transcribe_streaming_manager = TranscribeStreamingManager(region=region)
    
    logger.info("SocketIO handlers initialized")
    
    # Register event handlers
    register_handlers(socketio_instance)
    
    # Start background tasks
    start_background_tasks(socketio_instance)


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
                    emit('error', {
                        'type': 'error',
                        'error_code': 'STREAM_NOT_READY',
                        'message': 'Transcription stream is not ready',
                        'recoverable': True,
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
        try:
            session_id = data.get('session_id')
            
            if not session_id:
                logger.warning("Missing session_id in session_end")
                return
            
            logger.info(f"Session end: {session_id}")
            
            # Get session
            streaming_session = session_manager.get_session(session_id)
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
            
            # Remove session
            session_manager.remove_session(session_id)
            
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
            logger.info(f"WebSocket disconnected: user={user_id}")
            
            # Clean up any active sessions for this connection
            # Note: This is simplified - in production, you'd need better session tracking
            
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
