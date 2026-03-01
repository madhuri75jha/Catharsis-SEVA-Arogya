# Bugfix Requirements Document

## Introduction

This document specifies the requirements for fixing a critical bug in the transcription session lifecycle where sessions fail to start with "SESSION_START_FAILED" followed by "SESSION_NOT_FOUND" errors. The bug prevents users from starting transcription sessions, rendering the core transcription functionality unusable.

The issue occurs when:
- User clicks to start transcription
- Session is created successfully on the client (e.g., session_1772381925848_1ztymh6vi)
- Audio capture and recording start
- Transcription starts automatically via WebSocket
- Session immediately fails with SESSION_START_FAILED error
- Followed by SESSION_NOT_FOUND error when audio chunks are sent
- Session ends and recording stops

The root cause is a session tracking mismatch between client and server: the client generates a session_id locally and sends it to the server, but the server may not properly store or retrieve this session_id, causing subsequent audio_chunk messages to fail with SESSION_NOT_FOUND.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the client calls `startSession()` and generates a session_id locally THEN the server receives `session_start` but may fail to properly create or store the session in session_manager

1.2 WHEN the server fails to start the AWS Transcribe stream during `session_start` THEN the system emits SESSION_START_FAILED error but the session may be partially created in an inconsistent state

1.3 WHEN the client sends audio chunks with a session_id that was not properly stored THEN the server returns SESSION_NOT_FOUND error causing the transcription to fail

1.4 WHEN session creation fails on the server THEN the client is not properly notified before audio chunks start being sent, leading to a race condition

### Expected Behavior (Correct)

2.1 WHEN the client calls `startSession()` and generates a session_id locally THEN the server SHALL successfully create and store the session in session_manager with that session_id

2.2 WHEN the server encounters an error starting the AWS Transcribe stream THEN the system SHALL properly clean up any partially created session state and emit a clear error to the client before any audio chunks are sent

2.3 WHEN the client sends audio chunks with a valid session_id THEN the server SHALL successfully retrieve the session from session_manager and process the audio

2.4 WHEN session creation fails on the server THEN the client SHALL receive the error acknowledgment before attempting to send any audio chunks, preventing SESSION_NOT_FOUND errors

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a session is successfully created and audio chunks are sent for a valid session THEN the system SHALL CONTINUE TO process audio and return transcription results correctly

3.2 WHEN a session completes normally via `session_end` THEN the system SHALL CONTINUE TO finalize the audio, upload to S3, update the database, and clean up resources

3.3 WHEN the WebSocket connection is lost during an active session THEN the system SHALL CONTINUE TO handle reconnection attempts and buffer audio as designed

3.4 WHEN multiple concurrent sessions exist for different users THEN the system SHALL CONTINUE TO track and manage each session independently without interference

3.5 WHEN session cleanup runs for idle sessions THEN the system SHALL CONTINUE TO properly remove expired sessions without affecting active ones
