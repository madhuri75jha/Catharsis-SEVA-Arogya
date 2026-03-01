"""
Bug Condition Exploration Test for Transcription Session Start Failure

**Validates: Requirements 2.1, 2.4**

This test encodes the EXPECTED behavior - it will FAIL on unfixed code,
confirming the bug exists. When the bug is fixed, this test will PASS.

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

GOAL: Surface counterexamples that demonstrate the NameError when accessing request.sid.

This test verifies that when a session_start event is received, the server
successfully creates a session without raising a NameError.
"""
import pytest
import sys
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from hypothesis import given, strategies as st, settings, HealthCheck
import uuid
import asyncio

# Mock all the AWS service dependencies before importing socketio_handlers
sys.modules['aws_services.audio_buffer'] = Mock()
sys.modules['aws_services.session_manager'] = Mock()
sys.modules['aws_services.transcribe_streaming_manager'] = Mock()
sys.modules['models.transcription'] = Mock()

# Import flask and mock session and request
import flask
mock_flask_session = Mock()
mock_flask_session.get = Mock(return_value='test-user-123')
flask.session = mock_flask_session

# Mock the request object with sid attribute
mock_flask_request = Mock()
mock_flask_request.sid = 'test-request-sid-12345'
flask.request = mock_flask_request


def is_bug_condition(event_data):
    """
    Check if the bug condition holds (session_start event triggers NameError).
    
    Returns True for session_start events that would trigger the bug.
    The bug is that handle_session_start tries to access request.sid without
    importing request from Flask.
    """
    return event_data.get('event_name') == 'session_start'


@pytest.fixture
def mock_managers():
    """Mock all the global managers in socketio_handlers"""
    with patch('socketio_handlers.session_manager') as mock_session_mgr, \
         patch('socketio_handlers.transcribe_streaming_manager') as mock_transcribe_mgr, \
         patch('socketio_handlers.database_manager') as mock_db_mgr, \
         patch('socketio_handlers.storage_manager') as mock_storage_mgr:
        
        # Configure mock session manager
        mock_session = Mock()
        mock_session.sample_rate = 16000
        mock_session.audio_buffer = None
        mock_session.transcribe_stream = None
        mock_session.user_id = 'test-user-123'
        mock_session.request_sid = 'test-request-sid'
        
        mock_session_mgr.create_session.return_value = mock_session
        mock_session_mgr.get_session.return_value = mock_session
        
        # Configure mock transcribe streaming manager
        async def mock_start_stream(*args, **kwargs):
            return {'stream_id': 'test-stream-123'}
        
        mock_transcribe_mgr.start_stream = mock_start_stream
        
        # Configure mock database manager
        mock_db_mgr.execute_with_retry.return_value = None
        
        yield {
            'session_manager': mock_session_mgr,
            'transcribe_manager': mock_transcribe_mgr,
            'database_manager': mock_db_mgr,
            'storage_manager': mock_storage_mgr,
            'mock_session': mock_session
        }


class TestSessionStartBugCondition:
    """
    Property 1: Fault Condition - Session Start NameError
    
    For any session_start event received by the server, the fixed handle_session_start
    function SHALL successfully retrieve the Socket.IO session ID and create a session
    in session_manager without raising a NameError, allowing subsequent audio chunks
    to be processed.
    
    **Validates: Requirements 2.1, 2.4**
    """
    
    def test_bug_condition_holds(self):
        """
        Verify that the bug condition holds (session_start event triggers the code path).
        
        This test confirms we're testing the right scenario.
        """
        event_data = {'event_name': 'session_start', 'session_id': 'test-123'}
        assert is_bug_condition(event_data), "Bug condition should hold for session_start events"
    
    def test_session_start_creates_session_without_nameerror(self, mock_managers):
        """
        Test that handle_session_start creates a session without raising NameError.
        
        EXPECTED ON UNFIXED CODE: FAIL - NameError: name 'request' is not defined
        EXPECTED ON FIXED CODE: PASS - session created successfully
        
        **Validates: Requirements 2.1, 2.4**
        """
        # Import the handler after mocks are set up
        from socketio_handlers import register_handlers
        
        # Create a mock SocketIO instance
        mock_socketio = Mock()
        mock_handlers = {}
        
        def mock_on(event_name):
            def decorator(func):
                mock_handlers[event_name] = func
                return func
            return decorator
        
        mock_socketio.on = mock_on
        mock_emit = Mock()
        
        # Register handlers
        with patch('socketio_handlers.emit', mock_emit):
            register_handlers(mock_socketio)
            
            # Get the session_start handler
            assert 'session_start' in mock_handlers, "session_start handler should be registered"
            handle_session_start = mock_handlers['session_start']
            
            # Prepare test data
            session_data = {
                'session_id': 'test-session-123',
                'quality': 'medium'
            }
            
            # Call the handler
            handle_session_start(session_data)
            
            # Check if session was created successfully OR if an error was emitted
            session_created = mock_managers['session_manager'].create_session.called
            
            # Check for error emissions
            error_emitted = False
            for call in mock_emit.call_args_list:
                if len(call[0]) > 0 and call[0][0] == 'error':
                    error_emitted = True
                    error_data = call[0][1] if len(call[0]) > 1 else {}
                    # Check if it's the NameError we're looking for
                    if 'SESSION_START_FAILED' in str(error_data):
                        pytest.fail(
                            f"COUNTEREXAMPLE FOUND: SESSION_START_FAILED error emitted. "
                            f"Error data: {error_data}. "
                            f"Expected: Session created successfully without NameError. "
                            f"Actual: Error indicates session start failed due to NameError. "
                            f"This confirms the bug exists - request.sid is accessed without importing request."
                        )
            
            # If no session was created and no error was emitted, something is wrong
            if not session_created and not error_emitted:
                pytest.fail(
                    "COUNTEREXAMPLE FOUND: Neither session creation nor error emission occurred. "
                    "Expected: Session created successfully. "
                    "Actual: Handler executed but no observable outcome."
                )
            
            # Verify session was created successfully
            assert session_created, (
                "COUNTEREXAMPLE FOUND: Session was not created. "
                "Expected: session_manager.create_session called. "
                "Actual: create_session was not called, indicating the bug prevented session creation."
            )
            
            # Verify session_ack was emitted
            ack_emitted = any(call[0][0] == 'session_ack' for call in mock_emit.call_args_list if len(call[0]) > 0)
            assert ack_emitted, (
                "COUNTEREXAMPLE FOUND: session_ack was not emitted. "
                "Expected: session_ack emitted after successful session creation. "
                "Actual: No session_ack emission found."
            )
    
    def test_session_start_with_generated_session_id(self, mock_managers):
        """
        Test that handle_session_start works when session_id is not provided (UUID generation).
        
        EXPECTED ON UNFIXED CODE: FAIL - NameError: name 'request' is not defined
        EXPECTED ON FIXED CODE: PASS - session created with generated UUID
        
        **Validates: Requirements 2.1, 2.4**
        """
        from socketio_handlers import register_handlers
        
        mock_socketio = Mock()
        mock_handlers = {}
        
        def mock_on(event_name):
            def decorator(func):
                mock_handlers[event_name] = func
                return func
            return decorator
        
        mock_socketio.on = mock_on
        mock_emit = Mock()
        
        with patch('socketio_handlers.emit', mock_emit):
            register_handlers(mock_socketio)
            handle_session_start = mock_handlers['session_start']
            
            # Test data without session_id (should generate UUID)
            session_data = {
                'quality': 'high'
            }
            
            try:
                handle_session_start(session_data)
                
                # Verify session was created
                mock_managers['session_manager'].create_session.assert_called_once()
                
                # Verify a session_id was generated (UUID format)
                call_kwargs = mock_managers['session_manager'].create_session.call_args[1]
                session_id = call_kwargs.get('session_id')
                assert session_id is not None, "session_id should be generated"
                
            except NameError as e:
                pytest.fail(
                    f"COUNTEREXAMPLE FOUND: NameError raised when creating session without session_id. "
                    f"Error: {str(e)}. "
                    f"Expected: Session created with generated UUID without NameError. "
                    f"Actual: NameError indicates 'request' is not defined. "
                    f"Bug confirmed: request.sid access fails before UUID generation completes."
                )
    
    def test_session_start_with_different_quality_settings(self, mock_managers):
        """
        Test that handle_session_start works with different quality parameters.
        
        EXPECTED ON UNFIXED CODE: FAIL - NameError: name 'request' is not defined
        EXPECTED ON FIXED CODE: PASS - session created with specified quality
        
        **Validates: Requirements 2.1, 2.4**
        """
        from socketio_handlers import register_handlers
        
        mock_socketio = Mock()
        mock_handlers = {}
        
        def mock_on(event_name):
            def decorator(func):
                mock_handlers[event_name] = func
                return func
            return decorator
        
        mock_socketio.on = mock_on
        mock_emit = Mock()
        
        # Test with different quality settings
        quality_settings = ['low', 'medium', 'high']
        
        for quality in quality_settings:
            with patch('socketio_handlers.emit', mock_emit):
                mock_managers['session_manager'].create_session.reset_mock()
                
                register_handlers(mock_socketio)
                handle_session_start = mock_handlers['session_start']
                
                session_data = {
                    'session_id': f'test-session-{quality}',
                    'quality': quality
                }
                
                try:
                    handle_session_start(session_data)
                    
                    # Verify session was created with correct quality
                    mock_managers['session_manager'].create_session.assert_called_once()
                    call_kwargs = mock_managers['session_manager'].create_session.call_args[1]
                    assert call_kwargs.get('quality') == quality, f"Quality should be {quality}"
                    
                except NameError as e:
                    pytest.fail(
                        f"COUNTEREXAMPLE FOUND: NameError raised for quality={quality}. "
                        f"Error: {str(e)}. "
                        f"Expected: Session created successfully for all quality settings. "
                        f"Actual: NameError indicates 'request' is not defined. "
                        f"Bug confirmed: request.sid access fails regardless of quality parameter."
                    )


class TestSessionStartPropertyBased:
    """
    Property-based test using Hypothesis to verify the bug condition
    holds regardless of specific session data.
    
    **Validates: Requirements 2.1, 2.4**
    """
    
    @given(
        session_id=st.one_of(
            st.none(),
            st.uuids().map(str),
            st.text(min_size=1, max_size=50, alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd'),
                whitelist_characters='-_'
            ))
        ),
        quality=st.sampled_from(['low', 'medium', 'high'])
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_session_start_property_no_nameerror(self, session_id, quality, mock_managers):
        """
        Property: For any valid session_start event data, handle_session_start
        SHALL NOT raise a NameError.
        
        EXPECTED ON UNFIXED CODE: FAIL - NameError for all inputs
        EXPECTED ON FIXED CODE: PASS - no NameError for any input
        
        **Validates: Requirements 2.1, 2.4**
        """
        from socketio_handlers import register_handlers
        
        mock_socketio = Mock()
        mock_handlers = {}
        
        def mock_on(event_name):
            def decorator(func):
                mock_handlers[event_name] = func
                return func
            return decorator
        
        mock_socketio.on = mock_on
        mock_emit = Mock()
        
        with patch('socketio_handlers.emit', mock_emit):
            register_handlers(mock_socketio)
            handle_session_start = mock_handlers['session_start']
            
            # Prepare session data
            session_data = {'quality': quality}
            if session_id is not None:
                session_data['session_id'] = session_id
            
            # Reset mocks
            mock_managers['session_manager'].create_session.reset_mock()
            
            try:
                handle_session_start(session_data)
                
                # If we get here, no NameError was raised (bug is fixed)
                # Verify session creation was attempted
                assert mock_managers['session_manager'].create_session.called, (
                    "session_manager.create_session should be called"
                )
                
            except NameError as e:
                pytest.fail(
                    f"COUNTEREXAMPLE FOUND: NameError raised for session_data={session_data}. "
                    f"Error: {str(e)}. "
                    f"Expected: No NameError for any valid session_start data. "
                    f"Actual: NameError indicates 'request' is not defined. "
                    f"Bug confirmed: request.sid access fails for input: {session_data}"
                )
