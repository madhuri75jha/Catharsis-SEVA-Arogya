"""
Bug Condition Exploration Test for Transcription Page Not Starting

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

This test encodes the EXPECTED behavior - it will FAIL on unfixed code,
confirming the bug exists. When the bug is fixed, this test will PASS.

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

GOAL: Surface counterexamples that demonstrate the bug exists.
"""
import pytest
from hypothesis import given, strategies as st
from jinja2 import Environment, FileSystemLoader
import os


def hasJavaScriptModules(page_html):
    """
    Check if the page includes all required JavaScript modules.
    
    Returns True if all modules are present:
    - audio-capture.js
    - websocket-client.js
    - transcription-display.js
    - transcription-controller.js
    """
    required_modules = [
        'audio-capture.js',
        'websocket-client.js',
        'transcription-display.js',
        'transcription-controller.js'
    ]
    
    return all(module in page_html for module in required_modules)


def hasTranscriptionControllerInit(page_html):
    """
    Check if the page initializes the TranscriptionController.
    
    Returns True if initialization code is present:
    - new TranscriptionController
    - controller.initialize()
    """
    return ('new TranscriptionController' in page_html and 
            'controller.initialize()' in page_html)


def controllerAutoStarts(page_html):
    """
    Check if the controller automatically starts on page load.
    
    Returns True if auto-start code is present:
    - controller.start() called after initialization
    - DOMContentLoaded event listener
    """
    return ('controller.start()' in page_html and 
            'DOMContentLoaded' in page_html)


def displaysRealTranscription(page_html):
    """
    Check if the page is set up to display real transcription data.
    
    Returns True if:
    - TranscriptionController is initialized (which manages display)
    - Socket.IO client is loaded (for WebSocket connection)
    
    Returns False if:
    - Only static dummy text is present without transcription setup
    """
    has_socketio = 'socket.io' in page_html
    has_controller = hasTranscriptionControllerInit(page_html)
    
    return has_socketio and has_controller


def hasStaticDummyText(page_html):
    """
    Check if the page contains hardcoded dummy text.
    
    Returns True if dummy text is present:
    - "Ramesh... 45 years old"
    - "History of fever for 3 days"
    """
    return ('Ramesh' in page_html or 
            'History of fever' in page_html or
            '45 years old' in page_html)


@pytest.fixture
def render_transcription_page():
    """Fixture to render the transcription.html template"""
    # Set up Jinja2 environment
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    env = Environment(loader=FileSystemLoader(template_dir))
    
    def render(user_id='test-user-123'):
        """Render the transcription template with a mock session"""
        template = env.get_template('transcription.html')
        
        # Mock Flask's url_for function
        def mock_url_for(endpoint, **kwargs):
            if endpoint == 'static':
                filename = kwargs.get('filename', '')
                return f'/static/{filename}'
            return f'/{endpoint}'
        
        # Mock session
        mock_session = {'user_id': user_id}
        
        # Render template with mocked context
        return template.render(
            url_for=mock_url_for,
            session=mock_session
        )
    
    return render


class TestTranscriptionPageBugCondition:
    """
    Property 1: Fault Condition - Transcription Page Initializes and Starts
    
    For any page navigation where the user accesses the `/transcription` route,
    the rendered page SHALL include all required JavaScript modules, initialize
    the TranscriptionController with proper configuration, automatically start
    audio capture and WebSocket connection, and display real-time transcribed
    text replacing any placeholder content.
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
    """
    
    def test_transcription_page_has_javascript_modules(self, render_transcription_page):
        """
        Test that the /transcription page includes all required JavaScript modules.
        
        EXPECTED ON UNFIXED CODE: FAIL - modules are missing
        EXPECTED ON FIXED CODE: PASS - modules are present
        
        **Validates: Requirement 2.2**
        """
        page_html = render_transcription_page()
        
        # This assertion will FAIL on unfixed code (proving the bug exists)
        assert hasJavaScriptModules(page_html), (
            "COUNTEREXAMPLE FOUND: /transcription page is missing required JavaScript modules. "
            "Expected modules: audio-capture.js, websocket-client.js, "
            "transcription-display.js, transcription-controller.js"
        )
    
    def test_transcription_page_initializes_controller(self, render_transcription_page):
        """
        Test that the /transcription page initializes TranscriptionController.
        
        EXPECTED ON UNFIXED CODE: FAIL - no initialization code
        EXPECTED ON FIXED CODE: PASS - initialization code present
        
        **Validates: Requirement 2.3**
        """
        page_html = render_transcription_page()
        
        # This assertion will FAIL on unfixed code (proving the bug exists)
        assert hasTranscriptionControllerInit(page_html), (
            "COUNTEREXAMPLE FOUND: /transcription page does not initialize TranscriptionController. "
            "Expected: 'new TranscriptionController' and 'controller.initialize()' in page HTML"
        )
    
    def test_transcription_page_auto_starts_controller(self, render_transcription_page):
        """
        Test that the /transcription page automatically starts the controller.
        
        EXPECTED ON UNFIXED CODE: FAIL - no auto-start code
        EXPECTED ON FIXED CODE: PASS - auto-start code present
        
        **Validates: Requirement 2.4**
        """
        page_html = render_transcription_page()
        
        # This assertion will FAIL on unfixed code (proving the bug exists)
        assert controllerAutoStarts(page_html), (
            "COUNTEREXAMPLE FOUND: /transcription page does not automatically start controller. "
            "Expected: 'controller.start()' and 'DOMContentLoaded' event listener in page HTML"
        )
    
    def test_transcription_page_displays_real_transcription(self, render_transcription_page):
        """
        Test that the /transcription page is set up to display real transcription.
        
        EXPECTED ON UNFIXED CODE: FAIL - only static dummy text, no transcription setup
        EXPECTED ON FIXED CODE: PASS - transcription display setup present
        
        **Validates: Requirement 2.5**
        """
        page_html = render_transcription_page()
        
        # This assertion will FAIL on unfixed code (proving the bug exists)
        assert displaysRealTranscription(page_html), (
            "COUNTEREXAMPLE FOUND: /transcription page is not set up to display real transcription. "
            "Expected: Socket.IO client and TranscriptionController initialization"
        )
    
    def test_transcription_page_bug_condition_complete(self, render_transcription_page):
        """
        Complete bug condition test - verifies all aspects of the expected behavior.
        
        This is the main property test that encodes the complete expected behavior.
        
        EXPECTED ON UNFIXED CODE: FAIL - demonstrates the bug exists
        EXPECTED ON FIXED CODE: PASS - confirms the fix works
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
        """
        page_html = render_transcription_page()
        
        # Collect all counterexamples
        counterexamples = []
        
        if not hasJavaScriptModules(page_html):
            counterexamples.append(
                "Missing JavaScript modules (audio-capture.js, websocket-client.js, "
                "transcription-display.js, transcription-controller.js)"
            )
        
        if not hasTranscriptionControllerInit(page_html):
            counterexamples.append(
                "No TranscriptionController initialization "
                "(missing 'new TranscriptionController' and 'controller.initialize()')"
            )
        
        if not controllerAutoStarts(page_html):
            counterexamples.append(
                "Controller does not auto-start "
                "(missing 'controller.start()' or 'DOMContentLoaded' listener)"
            )
        
        if not displaysRealTranscription(page_html):
            counterexamples.append(
                "Not set up to display real transcription "
                "(missing Socket.IO client or TranscriptionController setup)"
            )
        
        if hasStaticDummyText(page_html) and not hasTranscriptionControllerInit(page_html):
            counterexamples.append(
                "Page contains static dummy text without transcription functionality "
                "(found 'Ramesh', '45 years old', or 'History of fever' without controller)"
            )
        
        # This assertion will FAIL on unfixed code with detailed counterexamples
        assert len(counterexamples) == 0, (
            f"COUNTEREXAMPLES FOUND - Bug confirmed! "
            f"The /transcription page has {len(counterexamples)} issue(s):\n" +
            "\n".join(f"  {i+1}. {ce}" for i, ce in enumerate(counterexamples))
        )


class TestTranscriptionPagePropertyBased:
    """
    Property-based test using Hypothesis to verify the bug condition
    across different user sessions.
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
    """
    
    @given(
        user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'), 
            whitelist_characters='-_'
        ))
    )
    @pytest.mark.parametrize('_', [None])  # Workaround for fixture with hypothesis
    def test_transcription_page_initializes_for_any_user(self, _, user_id):
        """
        Property: For ANY user session, navigating to /transcription should
        result in a page that initializes TranscriptionController and starts
        transcription automatically.
        
        This property-based test generates random user sessions and verifies
        the expected behavior holds for all of them.
        
        EXPECTED ON UNFIXED CODE: FAIL for all generated user sessions
        EXPECTED ON FIXED CODE: PASS for all generated user sessions
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
        """
        # Set up Jinja2 environment directly (avoid fixture)
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('transcription.html')
        
        # Mock Flask's url_for function
        def mock_url_for(endpoint, **kwargs):
            if endpoint == 'static':
                filename = kwargs.get('filename', '')
                return f'/static/{filename}'
            return f'/{endpoint}'
        
        # Mock session
        mock_session = {'user_id': user_id}
        
        # Render template with mocked context
        page_html = template.render(
            url_for=mock_url_for,
            session=mock_session
        )
        
        # Verify all required components are present
        # These assertions will FAIL on unfixed code for ANY user session
        assert hasJavaScriptModules(page_html), (
            f"COUNTEREXAMPLE: User ID '{user_id}' - "
            "Page missing JavaScript modules"
        )
        
        assert hasTranscriptionControllerInit(page_html), (
            f"COUNTEREXAMPLE: User ID '{user_id}' - "
            "Page does not initialize TranscriptionController"
        )
        
        assert controllerAutoStarts(page_html), (
            f"COUNTEREXAMPLE: User ID '{user_id}' - "
            "Controller does not auto-start"
        )
        
        assert displaysRealTranscription(page_html), (
            f"COUNTEREXAMPLE: User ID '{user_id}' - "
            "Page not set up for real transcription"
        )
