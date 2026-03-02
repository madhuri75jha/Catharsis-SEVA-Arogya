# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Fault Condition** - Duplicate Audio Chunk Detection
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate duplicate audio chunks are being sent
  - **Scoped PBT Approach**: Test with controlled audio capture sessions (1-5 seconds) to ensure reproducibility
  - Test that each audio chunk from onaudioprocess is emitted exactly once via the 'chunk' event
  - Use content hashing (e.g., SHA-256 of PCM data) to detect duplicate chunks
  - Track all emitted chunks during a recording session and verify no hash appears twice
  - Test scenarios: basic 1-second capture, continuous 5-second capture, start/stop cycles
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves duplicate chunks exist)
  - Document counterexamples found (e.g., "Chunk hash X appeared 2 times at timestamps T1 and T2")
  - _Requirements: 1.1, 1.2, 2.1, 2.2_

- [ ] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Audio Processing Pipeline Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-transmission operations
  - Write property-based tests capturing observed behavior patterns:
    - AudioContext initialization with 16kHz sample rate and 4096 buffer size
    - ScriptProcessorNode creation and connection to audio source
    - Float32Array to Int16Array PCM conversion with clamping [-1.0, 1.0] and scaling
    - Resource cleanup: node disconnection and AudioContext closure on stop()
    - State management: getState() and isActive() return correct values
    - WebSocket encoding: chunks are base64 encoded with correct session ID
  - Property-based testing generates many test cases for stronger guarantees
  - Test with various audio patterns: silence, sine waves, noise, clipping edge cases
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Fix for duplicate audio chunks

  - [x] 3.1 Investigate and identify root cause
    - Review audio-capture.js onaudioprocess callback implementation
    - Verify ScriptProcessorNode provides sequential, non-overlapping chunks
    - Check if external buffering or re-transmission occurs in chunk event handlers
    - Verify event handler registration (ensure 'chunk' handlers not duplicated)
    - Check isCapturing flag management across start/stop cycles
    - Add logging/instrumentation to track chunk flow (sequence numbers or timestamps)
    - Document findings: confirm or refute hypothesized root causes
    - _Bug_Condition: isBugCondition(audioChunk, transmissionLog) where EXISTS previousChunk IN transmissionLog WHERE arraysAreEqual(audioChunk, previousChunk)_
    - _Expected_Behavior: Each audio chunk emitted exactly once via 'chunk' event_
    - _Preservation: Audio initialization, PCM conversion, cleanup, and WebSocket encoding unchanged_
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 3.3, 3.4_

  - [x] 3.2 Implement the fix based on root cause
    - Apply fix to audio-capture.js based on investigation findings
    - If issue is in onaudioprocess: ensure chunk emission happens exactly once per callback
    - If issue is external: fix buffering or handler duplication in consuming code
    - If issue is event handlers: ensure proper registration/deregistration on start/stop
    - Verify isCapturing flag correctly gates chunk emission
    - Consider adding chunk sequence numbers for tracking and debugging
    - _Bug_Condition: isBugCondition(audioChunk, transmissionLog) from design_
    - _Expected_Behavior: transmissionCount(audioChunk) == 1 for all chunks_
    - _Preservation: Preservation Requirements from design_
    - _Requirements: 2.1, 2.2_

  - [x] 3.3 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Each Audio Chunk Sent Exactly Once
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms each chunk is sent exactly once
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - Verify no duplicate chunk hashes appear in emission log
    - _Requirements: 2.1, 2.2_

  - [x] 3.4 Verify preservation tests still pass
    - **Property 2: Preservation** - Audio Processing Pipeline Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all audio processing operations work identically after fix
    - Verify initialization, PCM conversion, cleanup, and WebSocket encoding unchanged
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 4. Checkpoint - Ensure all tests pass
  - Run all exploration and preservation tests
  - Verify no duplicate chunks in any test scenario
  - Verify all audio processing operations work correctly
  - Confirm AWS Transcribe receives each audio chunk exactly once
  - Ask the user if questions arise or if integration testing is needed
