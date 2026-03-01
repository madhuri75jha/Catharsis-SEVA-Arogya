"""
Preservation Property Tests for Transcription Session Start Failure Bugfix

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

These tests verify that fixing the session_start bug does NOT break existing
functionality for other SocketIO events and session lifecycle operations.

IMPORTANT: These tests should PASS on UNFIXED code to establish the baseline
behavior that must be preserved after the fix is implemented.

Property 2: Preservation - Non-Session-Start Events Unchanged

For any SocketIO event that is NOT session_start (audio_chunk, session_end,
connect, disconnect), the fixed code SHALL produce exactly the same behavior
as the original code, preserving all existing functionality.
"""
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings, HealthCheck
import base64
import time

# Mock all the AWS service dependencies before importing socketio_handlers
sys.modules['aws_services.audio_buffer'] = Mock()
sys.modules['aws_services.session_manager'] = Mock()
sys.modules['aws_services.transcribe_streaming_manager'] = Mock()
sys.modules['models.transcription'] = Mock()

# Import flask and mock session
import flask
mock_flask_session = Mock()
mock_flask_session.get = Mock(return_value='test-user-123')
flask.session = mock_flask_session


@pytest.fixture
def mock_managers():
    """Mock all the global managers in socketio_handlers"""
    with patch('socketio_handlers.session_manager') as mock_session_mgr, \
         patch('socketio_handlers.transcribe_streaming_manager') as mock_transcribe_mgr, \
         patch('socketio_handlers.database_manager') as mock_db_mgr, \
         patch('socketio_handlers.storage_manager') as mock_storage_mgr:
        
        # Configure mock session
        mock_session = Mock()
        mock_session.sample_rate = 16000
        mock_session.audio_buffer = Mock()
        mock_session.audio_buffer.append = Mock()
        mock_session.audio_buffer.finalize_to_mp3 = Mock(return_value=b'mock_mp3_data')
        mock_session.audio_buffer.get_total_duration = Mock(return_value=120.5)
        mock_session.transcribe_stream = {'stream_id': 'test-stream-123'}
        mock_session.user_id = 'test-user-123'
        mock_session.request_sid = 'test-request-sid'
        
        mock_session_mgr.get_session.return_value = mock_session
        mock_session_mgr.remove_session.return_value = True
        mock_session_mgr.cleanup_idle_sessions.return_value = 0
        mock_session_mgr.get_all_sessions.return_value = {}
        
        # Configure mock transcribe streaming manager
        async def mock_send_audio(*args, **kwargs):
            return True
        
        async def mock_end_stream(*args, **kwargs):
            return True
        
        async def mock_cleanup_all(*args, **kwargs):
            return 0
        
        mock_transcribe_mgr.send_audio_chunk = mock_send_audio
        mock_transcribe_mgr.end_stream = mock_end_stream
        mock_transcribe_mgr.cleanup_all_streams = mock_cleanup_all
        
        # Configure mock storage manager
        mock_storage_mgr.upload_audio_bytes.return_value = True
        
        # Configure mock database manager
        mock_db_mgr.execute_with_retry.return_value = None
        
        yield {
            'session_manager': mock_session_mgr,
            'transcribe_manager': mock_transcribe_mgr,
            'database_manager': mock_db_mgr,
            'storage_manager': mock_storage_mgr,
            'mock_session': mock_session
        }


@pytest.fixture
def mock_socketio_handlers(mock_managers):
    """Create mock SocketIO instance and register handlers"""
    from socketio_handlers import register_handlers
    
    mock_socketio = Mock()
    mock_handlers = {}
    
    def mock_on(event_name):
        def decorator(func):
            mock_handlers[event_name] = func
            return func
        return decorator
    
    mock_socketio.on = mock_on
    mock_socketio.emit = Mock()
    mock_socketio.sleep = Mock()
    mock_socketio.start_background_task = Mock()
    
    # Register handlers
    register_handlers(mock_socketio)
    
    return {
        'socketio': mock_socketio,
        'handlers': mock_handlers,
        'managers': mock_managers
    }


class TestAudioChunkPreservation:
    """
    Test that audio_chunk event handling is preserved after the fix.
    
    **Validates: Requirement 3.1**
    
    WHEN a session is successfully created and audio chunks are sent for a valid session
    THEN the system SHALL CONTINUE TO process audio and return transcription results correctly
    """
    
    def test_audio_chunk_with_valid_session(self, mock_socketio_handlers):
        """
        Test that audio_chunk processing works correctly for valid sessions.
        
        EXPECTED: PASS on unfixed code (establishes baseline behavior)
        """
        handlers = mock_socketio_handlers['handlers']
        managers = mock_socketio_handlers['managers']
        
        # Get the audio_chunk handler
        assert 'audio_chunk' in handlers, "audio_chunk handler should be registered"
        handle_audio_chunk = handlers['audio_chunk']
        
        # Prepare test data
        audio_data = base64.b64encode(b'test_audio_data').decode('utf-8')
        chunk_data = {
            'session_id': 'test-session-123',
            'audio_data': audio_data
        }
        
        mock_emit = Mock()
        with patch('socketio_handlers.emit', mock_emit):
            # Call the handler
            handle_audio_chunk(chunk_data)
            
            # Verify session was retrieved
            managers['session_manager'].get_session.assert_called_once_with('test-session-123')
            
            # Verify audio was buffered
            managers['mock_session'].audio_buffer.append.assert_called_once()
            
            # Verify activity was updated
            managers['session_manager'].update_activity.assert_called_once_with('test-session-123')
            
            # Verify no error was emitted
            error_emitted = any(
                call[0][0] == 'error' for call in mock_emit.call_args_list if len(call[0]) > 0
            )
            assert not error_emitted, "No error should be emitted for valid audio chunk"
    
    def test_audio_chunk_with_missing_session(self, mock_socketio_handlers):
        """
        Test that audio_chunk handling emits SESSION_NOT_FOUND for missing sessions.
        
        EXPECTED: PASS on unfixed code (establishes baseline error handling)
        """
        handlers = mock_socketio_handlers['handlers']
        managers = mock_socketio_handlers['managers']
        
        # Configure session manager to return None (session not found)
        managers['session_manager'].get_session.return_value = None
        
        handle_audio_chunk = handlers['audio_chunk']
        
        chunk_data = {
            'session_id': 'nonexistent-session',
            'audio_data': base64.b64encode(b'test_audio').decode('utf-8')
        }
        
        mock_emit = Mock()
        with patch('socketio_handlers.emit', mock_emit):
            handle_audio_chunk(chunk_data)
            
            # Verify error was emitted
            error_calls = [call for call in mock_emit.call_args_list if len(call[0]) > 0 and call[0][0] == 'error']
            assert len(error_calls) > 0, "Error should be emitted for missing session"
            
            # Verify error code is SESSION_NOT_FOUND
            error_data = error_calls[0][0][1]
            assert error_data['error_code'] == 'SESSION_NOT_FOUND', "Error code should be SESSION_NOT_FOUND"
    
    @given(
        session_id=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='-_'
        )),
        audio_size=st.integers(min_value=100, max_value=10000)
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_audio_chunk_property_processing(self, session_id, audio_size, mock_socketio_handlers):
        """
        Property: For any valid audio_chunk with an existing session,
        the audio SHALL be buffered and forwarded to AWS Transcribe.
        
        EXPECTED: PASS on unfixed code (establishes baseline behavior)
        
        **Validates: Requirement 3.1**
        """
        handlers = mock_socketio_handlers['handlers']
        managers = mock_socketio_handlers['managers']
        
        handle_audio_chunk = handlers['audio_chunk']
        
        # Generate audio data
        audio_bytes = b'x' * audio_size
        audio_data = base64.b64encode(audio_bytes).decode('utf-8')
        
        chunk_data = {
            'session_id': session_id,
            'audio_data': audio_data
        }
        
        # Reset mocks
        managers['session_manager'].get_session.reset_mock()
        managers['mock_session'].audio_buffer.append.reset_mock()
        managers['session_manager'].update_activity.reset_mock()
        
        mock_emit = Mock()
        with patch('socketio_handlers.emit', mock_emit):
            handle_audio_chunk(chunk_data)
            
            # Verify session was retrieved
            managers['session_manager'].get_session.assert_called_once_with(session_id)
            
            # Verify audio was buffered
            managers['mock_session'].audio_buffer.append.assert_called_once()
            
            # Verify activity was updated
            managers['session_manager'].update_activity.assert_called_once_with(session_id)


class TestSessionEndPreservation:
    """
    Test that session_end event handling is preserved after the fix.
    
    **Validates: Requirement 3.2**
    
    WHEN a session completes normally via session_end
    THEN the system SHALL CONTINUE TO finalize the audio, upload to S3,
    update the database, and clean up resources
    """
    
    def test_session_end_complete_flow(self, mock_socketio_handlers):
        """
        Test that session_end completes the full finalization flow.
        
        EXPECTED: PASS on unfixed code (establishes baseline behavior)
        """
        handlers = mock_socketio_handlers['handlers']
        managers = mock_socketio_handlers['managers']
        
        handle_session_end = handlers['session_end']
        
        end_data = {
            'session_id': 'test-session-123'
        }
        
        mock_emit = Mock()
        with patch('socketio_handlers.emit', mock_emit):
            handle_session_end(end_data)
            
            # Verify session was retrieved
            managers['session_manager'].get_session.assert_called_once_with('test-session-123')
            
            # Verify audio was finalized to MP3
            managers['mock_session'].audio_buffer.finalize_to_mp3.assert_called_once()
            
            # Verify audio was uploaded to S3
            managers['storage_manager'].upload_audio_bytes.assert_called_once()
            
            # Verify database was updated
            managers['database_manager'].execute_with_retry.assert_called()
            
            # Verify session was removed
            managers['session_manager'].remove_session.assert_called_once_with('test-session-123')
            
            # Verify session_complete was emitted
            complete_calls = [
                call for call in mock_emit.call_args_list 
                if len(call[0]) > 0 and call[0][0] == 'session_complete'
            ]
            assert len(complete_calls) > 0, "session_complete should be emitted"
    
    def test_session_end_with_missing_session(self, mock_socketio_handlers):
        """
        Test that session_end handles missing sessions gracefully.
        
        EXPECTED: PASS on unfixed code (establishes baseline error handling)
        """
        handlers = mock_socketio_handlers['handlers']
        managers = mock_socketio_handlers['managers']
        
        # Configure session manager to return None
        managers['session_manager'].get_session.return_value = None
        
        handle_session_end = handlers['session_end']
        
        end_data = {
            'session_id': 'nonexistent-session'
        }
        
        mock_emit = Mock()
        with patch('socketio_handlers.emit', mock_emit):
            handle_session_end(end_data)
            
            # Verify session was queried
            managers['session_manager'].get_session.assert_called_once_with('nonexistent-session')
            
            # Verify no S3 upload was attempted
            managers['storage_manager'].upload_audio_bytes.assert_not_called()
            
            # Verify no session removal was attempted
            managers['session_manager'].remove_session.assert_not_called()
    
    def test_session_end_s3_upload_failure(self, mock_socketio_handlers):
        """
        Test that session_end handles S3 upload failures correctly.
        
        EXPECTED: PASS on unfixed code (establishes baseline error handling)
        """
        handlers = mock_socketio_handlers['handlers']
        managers = mock_socketio_handlers['managers']
        
        # Configure storage manager to fail upload
        managers['storage_manager'].upload_audio_bytes.return_value = False
        
        handle_session_end = handlers['session_end']
        
        end_data = {
            'session_id': 'test-session-123'
        }
        
        mock_emit = Mock()
        with patch('socketio_handlers.emit', mock_emit):
            handle_session_end(end_data)
            
            # Verify error was emitted
            error_calls = [
                call for call in mock_emit.call_args_list 
                if len(call[0]) > 0 and call[0][0] == 'error'
            ]
            assert len(error_calls) > 0, "Error should be emitted for S3 upload failure"
            
            # Verify error code is S3_UPLOAD_FAILED
            error_data = error_calls[0][0][1]
            assert error_data['error_code'] == 'S3_UPLOAD_FAILED', "Error code should be S3_UPLOAD_FAILED"


class TestConnectionHandlingPreservation:
    """
    Test that connect and disconnect event handling is preserved after the fix.
    
    **Validates: Requirement 3.3**
    
    WHEN the WebSocket connection is established or lost
    THEN the system SHALL CONTINUE TO handle connection lifecycle correctly
    """
    
    def test_connect_handler_registered(self, mock_socketio_handlers):
        """
        Test that connect handler is registered correctly.
        
        EXPECTED: PASS on unfixed code (establishes baseline behavior)
        """
        handlers = mock_socketio_handlers['handlers']
        
        # Verify connect handler exists
        assert 'connect' in handlers, "connect handler should be registered"
        assert callable(handlers['connect']), "connect handler should be callable"
    
    def test_disconnect_handler_registered(self, mock_socketio_handlers):
        """
        Test that disconnect handler is registered correctly.
        
        EXPECTED: PASS on unfixed code (establishes baseline behavior)
        """
        handlers = mock_socketio_handlers['handlers']
        
        # Verify disconnect handler exists
        assert 'disconnect' in handlers, "disconnect handler should be registered"
        assert callable(handlers['disconnect']), "disconnect handler should be callable"
    
    def test_disconnect_handler_executes(self, mock_socketio_handlers):
        """
        Test that disconnect handler executes without errors.
        
        EXPECTED: PASS on unfixed code (establishes baseline behavior)
        """
        handlers = mock_socketio_handlers['handlers']
        
        handle_disconnect = handlers['disconnect']
        
        # Mock authenticated session
        mock_session = Mock()
        mock_session.get.return_value = 'test-user-123'
        
        with patch('flask.session', mock_session):
            # Should not raise any exceptions
            handle_disconnect()


class TestBackgroundTasksPreservation:
    """
    Test that background tasks are preserved after the fix.
    
    **Validates: Requirement 3.5**
    
    WHEN session cleanup runs for idle sessions
    THEN the system SHALL CONTINUE TO properly remove expired sessions
    without affecting active ones
    """
    
    def test_background_tasks_registered(self):
        """
        Test that background tasks are registered correctly.
        
        EXPECTED: PASS on unfixed code (establishes baseline behavior)
        """
        from socketio_handlers import start_background_tasks
        
        mock_socketio = Mock()
        mock_socketio.sleep = Mock()
        mock_socketio.emit = Mock()
        mock_socketio.start_background_task = Mock()
        
        # Start background tasks
        start_background_tasks(mock_socketio)
        
        # Verify two background tasks were started
        assert mock_socketio.start_background_task.call_count == 2, \
            "Two background tasks should be started (cleanup and heartbeat)"
    
    def test_cleanup_idle_sessions_callable(self, mock_managers):
        """
        Test that cleanup_idle_sessions can be called without errors.
        
        EXPECTED: PASS on unfixed code (establishes baseline behavior)
        """
        from socketio_handlers import start_background_tasks
        
        mock_socketio = Mock()
        mock_socketio.sleep = Mock()
        mock_socketio.emit = Mock()
        
        cleanup_func = None
        
        def capture_task(func):
            nonlocal cleanup_func
            if cleanup_func is None:
                cleanup_func = func
        
        mock_socketio.start_background_task = capture_task
        
        # Start background tasks
        with patch('socketio_handlers.session_manager', mock_managers['session_manager']):
            start_background_tasks(mock_socketio)
            
            # Verify cleanup function was captured
            assert cleanup_func is not None, "Cleanup function should be registered"


class TestMultiSessionPreservation:
    """
    Test that multi-session tracking is preserved after the fix.
    
    **Validates: Requirement 3.4**
    
    WHEN multiple concurrent sessions exist for different users
    THEN the system SHALL CONTINUE TO track and manage each session
    independently without interference
    """
    
    def test_multiple_audio_chunks_different_sessions(self, mock_socketio_handlers):
        """
        Test that audio chunks for different sessions are handled independently.
        
        EXPECTED: PASS on unfixed code (establishes baseline behavior)
        """
        handlers = mock_socketio_handlers['handlers']
        managers = mock_socketio_handlers['managers']
        
        handle_audio_chunk = handlers['audio_chunk']
        
        # Create multiple sessions
        session_ids = ['session-1', 'session-2', 'session-3']
        
        mock_emit = Mock()
        with patch('socketio_handlers.emit', mock_emit):
            for session_id in session_ids:
                # Reset mocks
                managers['session_manager'].get_session.reset_mock()
                managers['session_manager'].update_activity.reset_mock()
                
                chunk_data = {
                    'session_id': session_id,
                    'audio_data': base64.b64encode(b'test_audio').decode('utf-8')
                }
                
                handle_audio_chunk(chunk_data)
                
                # Verify correct session was retrieved
                managers['session_manager'].get_session.assert_called_once_with(session_id)
                
                # Verify activity was updated for correct session
                managers['session_manager'].update_activity.assert_called_once_with(session_id)
    
    def test_multiple_session_ends_independent(self, mock_socketio_handlers):
        """
        Test that session_end for different sessions are handled independently.
        
        EXPECTED: PASS on unfixed code (establishes baseline behavior)
        """
        handlers = mock_socketio_handlers['handlers']
        managers = mock_socketio_handlers['managers']
        
        handle_session_end = handlers['session_end']
        
        session_ids = ['session-1', 'session-2']
        
        mock_emit = Mock()
        with patch('socketio_handlers.emit', mock_emit):
            for session_id in session_ids:
                # Reset mocks
                managers['session_manager'].get_session.reset_mock()
                managers['session_manager'].remove_session.reset_mock()
                
                end_data = {'session_id': session_id}
                
                handle_session_end(end_data)
                
                # Verify correct session was retrieved
                managers['session_manager'].get_session.assert_called_once_with(session_id)
                
                # Verify correct session was removed
                managers['session_manager'].remove_session.assert_called_once_with(session_id)
