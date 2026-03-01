# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Fault Condition** - Transcription Page Initializes and Starts
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope the property to the concrete failing case - navigation to `/transcription` route
  - Test that navigating to `/transcription` results in a page that includes all required JavaScript modules (audio-capture.js, websocket-client.js, transcription-display.js, transcription-controller.js), initializes TranscriptionController with proper configuration, and automatically starts audio capture and WebSocket connection
  - The test assertions should verify: hasJavaScriptModules(page), hasTranscriptionControllerInit(page), controllerAutoStarts(page), and displaysRealTranscription(page)
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found: missing script tags, no TranscriptionController initialization, only static dummy text displayed
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Other Routes and Functionality Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs (routes other than `/transcription`)
  - Observe: `/live-transcription` route renders with manual start/stop controls and functions correctly
  - Observe: TranscriptionController on other pages captures audio, establishes WebSocket connections, and displays transcriptions when initialized
  - Observe: Database operations save transcription data with correct structure after sessions complete
  - Observe: Final prescription page accesses transcription data correctly
  - Write property-based tests capturing observed behavior patterns: for all routes != '/transcription', behavior remains unchanged; for all TranscriptionController usage on other pages, functionality is preserved
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. Fix for transcription page not starting

  - [x] 3.1 Add Socket.IO client library to transcription.html
    - Include Socket.IO CDN script tag in `{% block extra_js %}` section before application scripts
    - Add: `<script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>`
    - _Bug_Condition: isBugCondition(input) where input.route == '/transcription' AND NOT hasJavaScriptModules(input.renderedPage)_
    - _Expected_Behavior: Page includes Socket.IO library for WebSocket communication_
    - _Preservation: Other routes and templates remain unchanged_
    - _Requirements: 2.1, 2.2_

  - [x] 3.2 Add JavaScript module imports to transcription.html
    - Include script tags for all required application modules in `{% block extra_js %}` section
    - Add: `<script src="{{ url_for('static', filename='js/audio-capture.js') }}"></script>`
    - Add: `<script src="{{ url_for('static', filename='js/websocket-client.js') }}"></script>`
    - Add: `<script src="{{ url_for('static', filename='js/transcription-display.js') }}"></script>`
    - Add: `<script src="{{ url_for('static', filename='js/transcription-controller.js') }}"></script>`
    - _Bug_Condition: isBugCondition(input) where NOT hasJavaScriptModules(input.renderedPage)_
    - _Expected_Behavior: hasJavaScriptModules(page) returns true - all modules loaded_
    - _Preservation: Module files themselves remain unchanged, only template imports them_
    - _Requirements: 2.1, 2.2_

  - [x] 3.3 Add TranscriptionController initialization code
    - Replace the simple timer script with initialization code wrapped in DOMContentLoaded event listener
    - Get userId from Flask session: `const userId = '{{ session.user_id }}';`
    - Create TranscriptionController instance with configuration:
      - websocketUrl: `window.location.origin`
      - userId: from session
      - quality: 'medium'
      - sampleRate: 16000
      - chunkDurationMs: 250
    - _Bug_Condition: isBugCondition(input) where NOT hasTranscriptionControllerInit(input.renderedPage)_
    - _Expected_Behavior: hasTranscriptionControllerInit(page) returns true - controller is instantiated_
    - _Preservation: TranscriptionController class behavior remains unchanged_
    - _Requirements: 2.2, 2.3_

  - [x] 3.4 Add auto-start logic to begin transcription on page load
    - Call `await controller.initialize()` after controller creation
    - Call `await controller.start()` to begin recording immediately
    - Wrap in try-catch to handle initialization errors (e.g., microphone permission denied)
    - Start the existing timer when controller starts recording
    - _Bug_Condition: isBugCondition(input) where page does not auto-start transcription_
    - _Expected_Behavior: controllerAutoStarts(page) returns true - transcription begins automatically_
    - _Preservation: Manual start behavior on /live-transcription remains unchanged_
    - _Requirements: 2.3, 2.4_

  - [x] 3.5 Update stop button handler to properly stop controller
    - Modify `stopAndReview()` function to call `await controller.stop()` before navigation
    - Ensure transcription data is saved before navigating to final prescription page
    - Stop the timer when controller stops recording
    - _Bug_Condition: Ensures proper cleanup when user stops transcription_
    - _Expected_Behavior: Controller stops cleanly and data is saved before navigation_
    - _Preservation: Database save operations remain unchanged_
    - _Requirements: 2.5, 3.3_

  - [x] 3.6 Clear or update static dummy content
    - Clear the dummy text in `#transcriptionContent` div on initialization, or let TranscriptionDisplay replace it when transcription starts
    - Ensure placeholder text does not interfere with real transcription display
    - _Bug_Condition: isBugCondition(input) where hasStaticDummyText(input.renderedPage)_
    - _Expected_Behavior: Real transcription text replaces dummy content_
    - _Preservation: UI visual design (layout, styling, animations) remains unchanged_
    - _Requirements: 2.4, 2.5, 3.5_

  - [x] 3.7 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Transcription Page Initializes and Starts
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - Verify page includes all JavaScript modules, initializes TranscriptionController, auto-starts transcription, and displays real transcription text
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.8 Verify preservation tests still pass
    - **Property 2: Preservation** - Other Routes and Functionality Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm `/live-transcription` route still works with manual controls
    - Confirm TranscriptionController functionality preserved on other pages
    - Confirm database operations and final prescription page access unchanged
    - Confirm UI visual design unchanged

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise
  - Verify transcription page now starts automatically when navigating to `/transcription`
  - Verify live transcription page still requires manual start
  - Verify no regressions in other application functionality
