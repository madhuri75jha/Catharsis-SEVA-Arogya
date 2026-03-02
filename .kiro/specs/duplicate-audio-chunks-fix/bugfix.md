# Bugfix Requirements Document

## Introduction

The live audio transcription feature is sending duplicate audio chunks to AWS Transcribe, resulting in repeated transcription of the same audio content. The `ScriptProcessorNode.onaudioprocess` callback in `audio-capture.js` fires continuously every ~256ms with a 4096 sample buffer. While this callback mechanism is correct, the current implementation does not properly track which audio samples have been sent versus which are new, causing the same audio data to be transmitted multiple times to the transcription service.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the `onaudioprocess` callback fires with a 4096 sample buffer THEN the system sends all buffer data to AWS Transcribe without tracking what has been previously sent

1.2 WHEN audio is continuously captured during a recording session THEN the system repeatedly sends the same audio samples multiple times, resulting in duplicate transcription output

### Expected Behavior (Correct)

2.1 WHEN the `onaudioprocess` callback fires with a 4096 sample buffer THEN the system SHALL send only the new audio samples that have not been previously transmitted

2.2 WHEN audio is continuously captured during a recording session THEN the system SHALL ensure each audio sample is sent exactly once to AWS Transcribe, preventing duplicate transcription

### Unchanged Behavior (Regression Prevention)

3.1 WHEN audio capture is initialized with the specified sample rate THEN the system SHALL CONTINUE TO create the AudioContext and ScriptProcessorNode with the correct configuration

3.2 WHEN audio data is converted from Float32Array to PCM Int16Array format THEN the system SHALL CONTINUE TO perform the conversion correctly with proper clamping and scaling

3.3 WHEN the recording is stopped THEN the system SHALL CONTINUE TO properly disconnect audio nodes and cleanup resources

3.4 WHEN audio chunks are sent via WebSocket THEN the system SHALL CONTINUE TO encode them as base64 and emit them with the correct session ID
