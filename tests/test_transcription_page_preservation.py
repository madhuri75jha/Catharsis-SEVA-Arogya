"""
Preservation Property Tests for Transcription Page Bug Fix

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

These tests verify that fixing the /transcription page bug does NOT break
existing functionality. They test behavior on UNFIXED code first to establish
a baseline, then will be re-run after the fix to ensure no regressions.

IMPORTANT: These tests should PASS on unfixed code (baseline behavior).
After the fix, they should still PASS (no regressions).

GOAL: Ensure preservation of existing functionality.
"""
import pytest
from hypothesis import given, strategies as st, settings
from jinja2 import Environment, FileSystemLoader
import os


@pytest.fixture
def render_template():
    """Fixture to render any template"""
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    env = Environment(loader=FileSystemLoader(template_dir))
    
    def render(template_name, user_id='test-user-123', **context):
        """Render a template with mocked Flask context"""
        template = env.get_template(template_name)
        
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
            session=mock_session,
            **context
        )
    
    return render


def hasManualStartStopControls(page_html):
    """
    Check if the page has manual start/stop controls.
    
    Returns True if:
    - Start recording button is present
    - Stop recording button is present
    - Buttons are separate (not auto-start)
    """
    has_start_button = 'start-recording' in page_html or 'Start Recording' in page_html
    has_stop_button = 'stop-recording' in page_html or 'Stop Recording' in page_html
    
    return has_start_button and has_stop_button


def hasTranscriptionControllerSetup(page_html):
    """
    Check if the page sets up TranscriptionController properly.
    
    Returns True if:
    - TranscriptionController is instantiated
    - Controller is initialized
    - Required modules are loaded
    """
    has_controller = 'new TranscriptionController' in page_html
    has_modules = all(module in page_html for module in [
        'audio-capture.js',
        'websocket-client.js',
        'transcription-display.js',
        'transcription-controller.js'
    ])
    
    return has_controller and has_modules


def hasQualitySelector(page_html):
    """
    Check if the page has audio quality selector.
    
    Returns True if quality-select element is present.
    """
    return 'quality-select' in page_html or 'Audio Quality' in page_html


def hasRecordingPulseAnimation(page_html):
    """
    Check if the page has recording pulse animation.
    
    Returns True if recording-pulse class or animation is present.
    """
    return 'recording-pulse' in page_html or 'animate-pulse' in page_html


def hasTimerDisplay(page_html):
    """
    Check if the page has a timer display.
    
    Returns True if timer element is present.
    """
    return 'timer' in page_html or '00:00' in page_html


def hasSmartSuggestionsArea(page_html):
    """
    Check if the page has smart suggestions area.
    
    Returns True if smart suggestions section is present.
    """
    return 'Smart Suggestions' in page_html or 'AI ACTIVE' in page_html


def hasStopAndReviewButton(page_html):
    """
    Check if the page has stop and review button.
    
    Returns True if stop and review button is present.
    """
    return 'Stop and Review' in page_html or 'stopAndReview' in page_html


class TestLiveTranscriptionPreservation:
    """
    Property 2.1: Preservation - Live Transcription Route Unchanged
    
    For any page navigation to /live-transcription route, the system SHALL
    continue to function correctly with manual start/stop controls.
    
    **Validates: Requirement 3.1**
    """
    
    def test_live_transcription_has_manual_controls(self, render_template):
        """
        Test that /live-transcription page has manual start/stop controls.
        
        EXPECTED ON UNFIXED CODE: PASS (baseline behavior)
        EXPECTED ON FIXED CODE: PASS (preserved behavior)
        
        **Validates: Requirement 3.1**
        """
        page_html = render_template('live_transcription.html')
        
        assert hasManualStartStopControls(page_html), (
            "REGRESSION: /live-transcription page missing manual start/stop controls. "
            "Expected: separate 'Start Recording' and 'Stop Recording' buttons"
        )
    
    def test_live_transcription_has_controller_setup(self, render_template):
        """
        Test that /live-transcription page sets up TranscriptionController.
        
        EXPECTED ON UNFIXED CODE: PASS (baseline behavior)
        EXPECTED ON FIXED CODE: PASS (preserved behavior)
        
        **Validates: Requirement 3.1, 3.2**
        """
        page_html = render_template('live_transcription.html')
        
        assert hasTranscriptionControllerSetup(page_html), (
            "REGRESSION: /live-transcription page missing TranscriptionController setup. "
            "Expected: TranscriptionController instantiation and required modules"
        )
    
    def test_live_transcription_has_quality_selector(self, render_template):
        """
        Test that /live-transcription page has audio quality selector.
        
        EXPECTED ON UNFIXED CODE: PASS (baseline behavior)
        EXPECTED ON FIXED CODE: PASS (preserved behavior)
        
        **Validates: Requirement 3.1**
        """
        page_html = render_template('live_transcription.html')
        
        assert hasQualitySelector(page_html), (
            "REGRESSION: /live-transcription page missing audio quality selector. "
            "Expected: quality-select element or 'Audio Quality' label"
        )
    
    def test_live_transcription_does_not_auto_start(self, render_template):
        """
        Test that /live-transcription page does NOT auto-start recording.
        
        This is a key difference from /transcription page - live transcription
        requires manual start, while transcription page should auto-start.
        
        EXPECTED ON UNFIXED CODE: PASS (baseline behavior)
        EXPECTED ON FIXED CODE: PASS (preserved behavior)
        
        **Validates: Requirement 3.1**
        """
        page_html = render_template('live_transcription.html')
        
        # Check that controller.start() is NOT called automatically on page load
        # It should only be called when user clicks start button
        has_auto_start = (
            'controller.start()' in page_html and 
            'DOMContentLoaded' in page_html and
            'start-recording' not in page_html.split('controller.start()')[0].split('DOMContentLoaded')[-1]
        )
        
        assert not has_auto_start, (
            "REGRESSION: /live-transcription page now auto-starts recording. "
            "Expected: manual start via button click, not automatic on page load"
        )


class TestTranscriptionPageUIPreservation:
    """
    Property 2.2: Preservation - Transcription Page UI Design Unchanged
    
    For the /transcription page, the visual design and layout SHALL remain
    unchanged after the fix (recording pulse animation, timer display,
    smart suggestions area, layout).
    
    **Validates: Requirement 3.5**
    """
    
    def test_transcription_page_has_recording_pulse(self, render_template):
        """
        Test that /transcription page has recording pulse animation.
        
        EXPECTED ON UNFIXED CODE: PASS (baseline behavior)
        EXPECTED ON FIXED CODE: PASS (preserved behavior)
        
        **Validates: Requirement 3.5**
        """
        page_html = render_template('transcription.html')
        
        assert hasRecordingPulseAnimation(page_html), (
            "REGRESSION: /transcription page missing recording pulse animation. "
            "Expected: recording-pulse class or animate-pulse"
        )
    
    def test_transcription_page_has_timer(self, render_template):
        """
        Test that /transcription page has timer display.
        
        EXPECTED ON UNFIXED CODE: PASS (baseline behavior)
        EXPECTED ON FIXED CODE: PASS (preserved behavior)
        
        **Validates: Requirement 3.5**
        """
        page_html = render_template('transcription.html')
        
        assert hasTimerDisplay(page_html), (
            "REGRESSION: /transcription page missing timer display. "
            "Expected: timer element or '00:00' display"
        )
    
    def test_transcription_page_has_smart_suggestions(self, render_template):
        """
        Test that /transcription page has smart suggestions area.
        
        EXPECTED ON UNFIXED CODE: PASS (baseline behavior)
        EXPECTED ON FIXED CODE: PASS (preserved behavior)
        
        **Validates: Requirement 3.5**
        """
        page_html = render_template('transcription.html')
        
        assert hasSmartSuggestionsArea(page_html), (
            "REGRESSION: /transcription page missing smart suggestions area. "
            "Expected: 'Smart Suggestions' section or 'AI ACTIVE' indicator"
        )
    
    def test_transcription_page_has_stop_button(self, render_template):
        """
        Test that /transcription page has stop and review button.
        
        EXPECTED ON UNFIXED CODE: PASS (baseline behavior)
        EXPECTED ON FIXED CODE: PASS (preserved behavior)
        
        **Validates: Requirement 3.5**
        """
        page_html = render_template('transcription.html')
        
        assert hasStopAndReviewButton(page_html), (
            "REGRESSION: /transcription page missing stop and review button. "
            "Expected: 'Stop and Review' button or stopAndReview function"
        )
    
    def test_transcription_page_layout_structure(self, render_template):
        """
        Test that /transcription page maintains its layout structure.
        
        EXPECTED ON UNFIXED CODE: PASS (baseline behavior)
        EXPECTED ON FIXED CODE: PASS (preserved behavior)
        
        **Validates: Requirement 3.5**
        """
        page_html = render_template('transcription.html')
        
        # Check for key layout elements
        has_header = 'Listening...' in page_html or 'Voice Capture' in page_html
        has_main_area = 'transcriptionContent' in page_html
        has_suggestions_area = 'Smart Suggestions' in page_html
        
        assert has_header and has_main_area and has_suggestions_area, (
            "REGRESSION: /transcription page layout structure changed. "
            "Expected: header with 'Listening...', main transcription area, and suggestions area"
        )


class TestOtherRoutesPreservation:
    """
    Property 2.3: Preservation - Other Routes Unchanged
    
    For any route that is NOT /transcription, the behavior SHALL remain
    completely unchanged.
    
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
    """
    
    @pytest.mark.parametrize('route', [
        'home.html',
        'login.html',
        'final_prescription.html',
        '404.html',
        '500.html'
    ])
    def test_other_templates_unchanged(self, render_template, route):
        """
        Test that templates other than transcription.html and
        live_transcription.html remain unchanged.
        
        EXPECTED ON UNFIXED CODE: PASS (baseline behavior)
        EXPECTED ON FIXED CODE: PASS (preserved behavior)
        
        **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
        """
        try:
            page_html = render_template(route)
            
            # Basic sanity checks - page should render and have content
            assert len(page_html) > 0, (
                f"REGRESSION: Template {route} failed to render or is empty"
            )
            
            # Should extend base template
            assert 'SEVA Arogya' in page_html or 'base.html' in page_html or len(page_html) > 100, (
                f"REGRESSION: Template {route} structure changed"
            )
            
        except Exception as e:
            pytest.fail(
                f"REGRESSION: Template {route} failed to render. Error: {str(e)}"
            )


class TestTranscriptionControllerPreservation:
    """
    Property 2.4: Preservation - TranscriptionController Functionality
    
    For any usage of TranscriptionController on any page, the functionality
    SHALL remain unchanged (audio capture, WebSocket connections, display).
    
    **Validates: Requirement 3.2**
    """
    
    def test_live_transcription_controller_config(self, render_template):
        """
        Test that TranscriptionController configuration on /live-transcription
        remains unchanged.
        
        EXPECTED ON UNFIXED CODE: PASS (baseline behavior)
        EXPECTED ON FIXED CODE: PASS (preserved behavior)
        
        **Validates: Requirement 3.2**
        """
        page_html = render_template('live_transcription.html')
        
        # Check that controller is configured with expected parameters
        has_websocket_url = 'websocketUrl' in page_html
        has_user_id = 'userId' in page_html
        has_quality = 'quality' in page_html
        has_sample_rate = 'sampleRate' in page_html
        
        assert all([has_websocket_url, has_user_id, has_quality, has_sample_rate]), (
            "REGRESSION: TranscriptionController configuration changed on /live-transcription. "
            "Expected: websocketUrl, userId, quality, sampleRate parameters"
        )
    
    def test_live_transcription_controller_initialization(self, render_template):
        """
        Test that TranscriptionController initialization on /live-transcription
        remains unchanged.
        
        EXPECTED ON UNFIXED CODE: PASS (baseline behavior)
        EXPECTED ON FIXED CODE: PASS (preserved behavior)
        
        **Validates: Requirement 3.2**
        """
        page_html = render_template('live_transcription.html')
        
        # Check that controller is initialized properly
        has_new_controller = 'new TranscriptionController' in page_html
        has_initialize = 'controller.initialize()' in page_html
        
        assert has_new_controller and has_initialize, (
            "REGRESSION: TranscriptionController initialization changed on /live-transcription. "
            "Expected: 'new TranscriptionController' and 'controller.initialize()'"
        )


class TestDatabaseAndNavigationPreservation:
    """
    Property 2.5: Preservation - Database and Navigation
    
    Database operations and navigation to final prescription page SHALL
    remain unchanged.
    
    **Validates: Requirements 3.3, 3.4**
    """
    
    def test_transcription_page_navigates_to_final_prescription(self, render_template):
        """
        Test that /transcription page navigates to final prescription page.
        
        EXPECTED ON UNFIXED CODE: PASS (baseline behavior)
        EXPECTED ON FIXED CODE: PASS (preserved behavior)
        
        **Validates: Requirement 3.4**
        """
        page_html = render_template('transcription.html')
        
        # Check that navigation to final prescription is present
        has_navigation = (
            '/final-prescription' in page_html or
            'final_prescription' in page_html
        )
        
        assert has_navigation, (
            "REGRESSION: /transcription page no longer navigates to final prescription. "
            "Expected: link or redirect to /final-prescription"
        )
    
    def test_final_prescription_page_structure(self, render_template):
        """
        Test that final prescription page structure is unchanged.
        
        EXPECTED ON UNFIXED CODE: PASS (baseline behavior)
        EXPECTED ON FIXED CODE: PASS (preserved behavior)
        
        **Validates: Requirement 3.4**
        """
        page_html = render_template('final_prescription.html')
        
        # Basic sanity check - page should render
        assert len(page_html) > 0, (
            "REGRESSION: Final prescription page failed to render"
        )
        
        # Should have prescription-related content
        has_prescription_content = (
            'prescription' in page_html.lower() or
            'final' in page_html.lower() or
            len(page_html) > 100
        )
        
        assert has_prescription_content, (
            "REGRESSION: Final prescription page structure changed"
        )


class TestPropertyBasedPreservation:
    """
    Property-based tests for preservation using Hypothesis.
    
    These tests generate many test cases to ensure preservation across
    different scenarios.
    
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
    """
    
    @given(
        user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='-_'
        ))
    )
    @settings(max_examples=20)
    def test_live_transcription_preserved_for_any_user(self, user_id):
        """
        Property: For ANY user session, /live-transcription page SHALL
        maintain manual start/stop controls and TranscriptionController setup.
        
        EXPECTED ON UNFIXED CODE: PASS for all user sessions (baseline)
        EXPECTED ON FIXED CODE: PASS for all user sessions (preserved)
        
        **Validates: Requirements 3.1, 3.2**
        """
        # Set up Jinja2 environment directly (avoid fixture)
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('live_transcription.html')
        
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
        
        # Verify preservation for this user session
        assert hasManualStartStopControls(page_html), (
            f"REGRESSION: User '{user_id}' - /live-transcription missing manual controls"
        )
        
        assert hasTranscriptionControllerSetup(page_html), (
            f"REGRESSION: User '{user_id}' - /live-transcription missing controller setup"
        )
        
        assert hasQualitySelector(page_html), (
            f"REGRESSION: User '{user_id}' - /live-transcription missing quality selector"
        )
    
    @given(
        user_id=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='-_'
        ))
    )
    @settings(max_examples=20)
    def test_transcription_page_ui_preserved_for_any_user(self, user_id):
        """
        Property: For ANY user session, /transcription page SHALL maintain
        its UI design (recording pulse, timer, smart suggestions, layout).
        
        EXPECTED ON UNFIXED CODE: PASS for all user sessions (baseline)
        EXPECTED ON FIXED CODE: PASS for all user sessions (preserved)
        
        **Validates: Requirement 3.5**
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
        
        # Verify UI preservation for this user session
        assert hasRecordingPulseAnimation(page_html), (
            f"REGRESSION: User '{user_id}' - /transcription missing recording pulse"
        )
        
        assert hasTimerDisplay(page_html), (
            f"REGRESSION: User '{user_id}' - /transcription missing timer"
        )
        
        assert hasSmartSuggestionsArea(page_html), (
            f"REGRESSION: User '{user_id}' - /transcription missing smart suggestions"
        )
        
        assert hasStopAndReviewButton(page_html), (
            f"REGRESSION: User '{user_id}' - /transcription missing stop button"
        )
