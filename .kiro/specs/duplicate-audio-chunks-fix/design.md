# Duplicate Audio Chunks Fix - Bugfix Design

## Overview

This bugfix addresses a misunderstanding about the Web Audio API's ScriptProcessorNode behavior. The initial bug report suggested that duplicate audio chunks were being sent to AWS Transcribe due to improper tracking of sent audio data. However, analysis reveals that the ScriptProcessorNode.onaudioprocess callback is designed to provide sequential, non-overlapping audio chunks automatically. Each callback invocation receives NEW audio data (4096 samples) that advances the audio stream position, not overlapping data from previous calls.

The fix involves verifying that the current implementation correctly handles the sequential audio chunks and ensuring that each chunk is transmitted exactly once without any buffering or tracking logic that might introduce duplicates.

## Glossary

- **Bug_Condition (C)**: The condition where audio chunks are sent multiple times to AWS Transcribe, resulting in duplicate transcription output
- **Property (P)**: Each audio chunk from onaudioprocess should be sent exactly once to AWS Transcribe
- **Preservation**: Existing audio capture initialization, PCM conversion, resource cleanup, and WebSocket transmission must remain unchanged
- **ScriptProcessorNode**: Web Audio API node that processes audio in fixed-size buffers (4096 samples) via the onaudioprocess callback
- **onaudioprocess**: Callback that fires every ~256ms (at 16kHz sample rate) with a new, non-overlapping 4096-sample buffer
- **AudioCapture**: The class in `static/js/audio-capture.js` that manages microphone capture and audio processing
- **PCM (Pulse Code Modulation)**: Audio format using 16-bit signed integers, required by AWS Transcribe

## Bug Details

### Fault Condition

The bug manifests when the onaudioprocess callback fires and the audio chunk is either sent multiple times or buffered in a way that causes re-transmission. However, upon analysis, the ScriptProcessorNode API guarantees that each callback receives sequential, non-overlapping audio data.

**Formal Specification:**
```
FUNCTION isBugCondition(audioChunk, transmissionLog)
  INPUT: audioChunk of type Int16Array (PCM data from onaudioprocess)
         transmissionLog of type Array<Int16Array> (history of sent chunks)
  OUTPUT: boolean
  
  RETURN EXISTS previousChunk IN transmissionLog WHERE
         arraysAreEqual(audioChunk, previousChunk)
END FUNCTION
```

### Examples

- **Scenario 1**: onaudioprocess fires at t=0ms with buffer A (samples 0-4095), then fires at t=256ms with buffer B (samples 4096-8191). If buffer A is sent twice, this is a bug.
- **Scenario 2**: Audio chunk is buffered and re-sent when the next onaudioprocess event occurs, causing the same samples to appear in multiple transmissions.
- **Scenario 3**: The isCapturing flag is checked correctly, and each chunk is emitted exactly once via the 'chunk' event.
- **Edge Case**: If onaudioprocess fires while isCapturing is false, the chunk should be discarded (not sent), which is correct behavior.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Audio capture initialization with AudioContext and ScriptProcessorNode must continue to work with the correct sample rate (16kHz) and buffer size (4096 samples)
- PCM conversion from Float32Array to Int16Array must continue to work correctly with proper clamping [-1.0, 1.0] and scaling
- Resource cleanup when stopping recording must continue to properly disconnect audio nodes and close the AudioContext
- WebSocket transmission of audio chunks must continue to encode as base64 and emit with the correct session ID

**Scope:**
All audio processing logic that does NOT involve the transmission of chunks should be completely unaffected by this fix. This includes:
- Microphone permission requests
- AudioContext creation and configuration
- Audio node connections and disconnections
- Float32 to PCM Int16 conversion
- Event handler registration and emission

## Hypothesized Root Cause

Based on the bug description and code analysis, the potential issues are:

1. **Misunderstanding of ScriptProcessorNode API**: The most likely issue is a misunderstanding of how the Web Audio API works. The ScriptProcessorNode automatically provides sequential, non-overlapping audio chunks. Each onaudioprocess callback receives the NEXT 4096 samples in the audio stream, not a sliding window or overlapping buffer.

2. **External Buffering or Re-transmission**: The bug may not be in audio-capture.js itself, but in how the chunks are handled after the 'chunk' event is emitted. If the consumer of these chunks (e.g., WebSocket handler) buffers or re-sends chunks, duplicates could occur.

3. **Event Handler Duplication**: If multiple event handlers are registered for the 'chunk' event, each chunk would be processed multiple times, potentially causing duplicate transmissions.

4. **Incorrect isCapturing Flag Management**: If the isCapturing flag is not properly managed, chunks might be emitted when they shouldn't be, though this would cause missing chunks rather than duplicates.

## Correctness Properties

Property 1: Fault Condition - Each Audio Chunk Sent Exactly Once

_For any_ audio chunk generated by the onaudioprocess callback during an active recording session, the fixed AudioCapture class SHALL emit that chunk exactly once via the 'chunk' event, ensuring no duplicate audio data is transmitted to AWS Transcribe.

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation - Audio Processing Pipeline Unchanged

_For any_ audio processing operation that is NOT related to chunk transmission tracking (initialization, PCM conversion, resource cleanup, WebSocket encoding), the fixed code SHALL produce exactly the same behavior as the original code, preserving all existing audio capture functionality.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

## Fix Implementation

### Changes Required

Based on the root cause analysis, the fix should focus on verification rather than major changes:

**File**: `static/js/audio-capture.js`

**Function**: `onaudioprocess` callback in the `initialize()` method

**Specific Changes**:
1. **Verify Sequential Chunk Handling**: Confirm that the onaudioprocess callback correctly processes each chunk exactly once without any buffering or re-emission logic.

2. **Review Event Emission**: Ensure that `_emitEvent('chunk', pcmData)` is called exactly once per onaudioprocess invocation and that the isCapturing flag correctly gates this emission.

3. **Investigate External Handlers**: Check how the 'chunk' event is consumed (likely in the WebSocket or transcription module) to ensure chunks are not buffered or re-sent at that level.

4. **Add Logging/Instrumentation**: Consider adding sequence numbers or timestamps to chunks to track their flow through the system and identify where duplicates are introduced.

5. **Verify Event Handler Registration**: Ensure that event handlers for 'chunk' events are registered only once and not duplicated during re-initialization or multiple start/stop cycles.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate duplicate chunk transmission on unfixed code, then verify the fix ensures each chunk is sent exactly once while preserving all existing audio processing behavior.

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate duplicate audio chunks BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Write tests that capture audio for a fixed duration, track all emitted chunks (with content hashing or sequence numbers), and assert that no duplicate chunks are emitted. Run these tests on the UNFIXED code to observe failures and understand the root cause.

**Test Cases**:
1. **Basic Duplicate Detection**: Capture 1 second of audio, hash each chunk, verify no hash appears twice (will fail on unfixed code if duplicates exist)
2. **Event Handler Duplication Test**: Register multiple 'chunk' handlers, verify each chunk is emitted to all handlers exactly once (may fail if handlers cause re-emission)
3. **Start/Stop Cycle Test**: Start recording, stop, start again, verify no chunks from first session are re-sent in second session (may fail if buffering occurs)
4. **Continuous Recording Test**: Capture 5 seconds of audio continuously, verify chunk count matches expected count based on sample rate and buffer size (will fail if duplicates exist)

**Expected Counterexamples**:
- Chunk hashes appear multiple times in the emission log
- Possible causes: external buffering, event handler duplication, incorrect ScriptProcessorNode usage

### Fix Checking

**Goal**: Verify that for all audio chunks generated during recording, each chunk is sent exactly once.

**Pseudocode:**
```
FOR ALL audioChunk generated by onaudioprocess DO
  transmissionCount := countTransmissions(audioChunk)
  ASSERT transmissionCount == 1
END FOR
```

### Preservation Checking

**Goal**: Verify that for all audio processing operations not related to chunk transmission, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL operation IN [initialize, convertToPCM, stop, getState, isActive] DO
  ASSERT originalAudioCapture.operation(input) = fixedAudioCapture.operation(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across different audio inputs and configurations
- It catches edge cases that manual unit tests might miss (e.g., different sample rates, buffer sizes, audio patterns)
- It provides strong guarantees that behavior is unchanged for all non-transmission-related operations

**Test Plan**: Observe behavior on UNFIXED code first for initialization, PCM conversion, and cleanup operations, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Initialization Preservation**: Verify AudioContext creation, sample rate configuration, and node connections work identically after fix
2. **PCM Conversion Preservation**: Verify Float32 to Int16 conversion produces identical output for various audio patterns (silence, sine waves, noise)
3. **Cleanup Preservation**: Verify stop() properly disconnects nodes and closes AudioContext identically after fix
4. **State Management Preservation**: Verify getState() and isActive() return correct values across start/stop cycles

### Unit Tests

- Test that onaudioprocess callback emits exactly one chunk per invocation
- Test that isCapturing flag correctly gates chunk emission
- Test that PCM conversion produces correct Int16 values for edge cases (silence, clipping, negative values)
- Test that event handlers are registered and invoked correctly

### Property-Based Tests

- Generate random audio patterns (sine waves, noise, silence) and verify each chunk is emitted exactly once
- Generate random start/stop sequences and verify no chunks are duplicated or lost
- Test PCM conversion with random Float32 values and verify output is always in valid Int16 range
- Test that multiple recording sessions produce independent, non-overlapping chunk streams

### Integration Tests

- Test full audio capture flow: initialize → start → capture 5 seconds → stop, verify chunk count and uniqueness
- Test WebSocket integration: verify chunks are transmitted to backend exactly once
- Test AWS Transcribe integration: verify transcription output does not contain repeated phrases
- Test error handling: verify that errors during capture do not cause chunk duplication or loss
