# Implementation Plan: Live Audio Transcription Streaming

## Overview

This implementation plan breaks down the live audio transcription streaming feature into discrete coding tasks. The feature enables real-time audio capture from the browser, streaming to AWS Transcribe Medical via WebSocket, and live display of transcription results. The implementation follows a layered approach: infrastructure setup, backend streaming services, frontend audio capture and display, database schema updates, and comprehensive testing.

The tasks are organized to build incrementally, with each step validating functionality before moving forward. Testing tasks are marked as optional to allow for faster MVP delivery while maintaining the option for comprehensive test coverage.

## Tasks

- [x] 1. Set up infrastructure and dependencies
  - [x] 1.1 Update Terraform configuration for AWS Transcribe permissions
    - Add IAM policy for `transcribe:StartStreamTranscription` and `transcribe:StartMedicalStreamTranscription`
    - Attach policies to existing ECS task role
    - Add `AWS_TRANSCRIBE_REGION` environment variable to ECS task definition
    - Configure S3 bucket access for transcription output
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [x] 1.2 Install Python backend dependencies
    - Add `flask-socketio==5.3.4`, `eventlet==0.33.3`, `amazon-transcribe==0.6.2`, `pydub==0.25.1` to requirements.txt
    - Update requirements.txt with version pins
    - _Requirements: 3.1, 3.2_
  
  - [x] 1.3 Install JavaScript frontend dependencies
    - Add Socket.IO client library to frontend (via CDN or npm)
    - Verify Web Audio API browser compatibility detection
    - _Requirements: 1.1, 2.1_
  
  - [x] 1.4 Update database schema for streaming transcriptions
    - Create migration script to add streaming-specific columns to transcriptions table
    - Add columns: `session_id`, `streaming_job_id`, `is_streaming`, `partial_transcript`, `audio_duration_seconds`, `sample_rate`, `quality`
    - Create indexes on `session_id` and `streaming_job_id`
    - _Requirements: 6.1, 6.2_

- [x] 2. Implement backend session management
  - [x] 2.1 Create Session data model and SessionManager class
    - Implement `Session` dataclass with fields: session_id, user_id, request_sid, job_id, audio_buffer, transcribe_stream, timestamps, quality, sample_rate
    - Implement `SessionManager` class with thread-safe session registry
    - Implement methods: `create_session()`, `get_session()`, `update_activity()`, `remove_session()`, `cleanup_idle_sessions()`, `get_active_count()`
    - Enforce maximum 100 concurrent sessions limit
    - Implement 5-minute idle timeout logic
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  
  - [ ] 2.2 Write unit tests for SessionManager
    - Test session creation and registration
    - Test session retrieval and activity updates
    - Test idle session cleanup (5-minute timeout)
    - Test concurrent session limit enforcement
    - Test thread safety with concurrent operations
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 3. Implement audio buffering and format conversion
  - [x] 3.1 Create AudioBuffer class for in-memory audio accumulation
    - Implement `AudioBuffer` class with PCM chunk storage
    - Implement `append()` method with size limit enforcement (30 minutes max)
    - Implement `get_total_duration()` for duration calculation
    - Implement `finalize_to_mp3()` using pydub for PCM to MP3 conversion at 64kbps
    - Implement `clear()` for memory cleanup
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [ ] 3.2 Write unit tests for AudioBuffer
    - Test chunk appending maintains order
    - Test duration calculation accuracy
    - Test PCM to MP3 conversion with correct bitrate and format
    - Test buffer size limit enforcement (30-minute max)
    - Test memory cleanup on clear()
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [ ] 3.3 Write property test for audio format compliance
    - **Property 2: PCM Format Compliance**
    - **Validates: Requirements 1.4**
    - Test that encoded audio chunks are 16-bit signed integers in little-endian format
    - Use Hypothesis to generate random audio data and verify format

- [x] 4. Implement AWS Transcribe streaming integration
  - [x] 4.1 Create TranscribeStreamingManager class
    - Implement `TranscribeStreamingManager` class using amazon-transcribe package
    - Implement `start_stream()` to initialize streaming transcription with AWS Transcribe Medical
    - Configure stream with language_code='en-US', specialty='PRIMARYCARE', and sample rate
    - Implement `send_audio_chunk()` to forward audio chunks to active stream
    - Implement `end_stream()` to signal completion and close stream
    - _Requirements: 3.1, 3.2, 3.3, 3.5_
  
  - [x] 4.2 Implement result handler for transcription streaming
    - Create `ResultHandler` class extending `TranscriptResultStreamHandler`
    - Implement `handle_transcript_event()` to process partial and final results
    - Emit results to Flask-SocketIO with format: type, is_partial, text, timestamp
    - Handle transcription errors and emit error events
    - _Requirements: 3.4, 4.1, 4.2, 4.3_
  
  - [ ]* 4.3 Write unit tests for TranscribeStreamingManager
    - Test stream initialization with correct parameters
    - Test audio chunk forwarding to AWS Transcribe
    - Test result handler emits to SocketIO correctly
    - Test stream completion signaling
    - Test error handling and logging
    - Mock AWS Transcribe streaming client
    - _Requirements: 3.1, 3.2, 3.5_

- [x] 5. Implement Flask-SocketIO server and event handlers
  - [x] 5.1 Configure Flask-SocketIO with eventlet async mode
    - Apply eventlet monkey patching in app initialization
    - Initialize SocketIO with Flask app, configure CORS, ping timeout (60s), ping interval (25s)
    - Set async_mode='eventlet' and max_http_buffer_size=1MB
    - _Requirements: 2.1, 11.7_
  
  - [x] 5.2 Implement WebSocket connection handler
    - Implement `@socketio.on('connect')` handler
    - Authenticate connection using Flask session (check user_id)
    - Register connection in SessionManager
    - Disconnect if authentication fails
    - _Requirements: 2.1, 8.1_
  
  - [x] 5.3 Implement session_start event handler
    - Implement `@socketio.on('session_start')` handler
    - Parse quality parameter and determine sample rate (low=8kHz, medium=16kHz, high=48kHz)
    - Create session in SessionManager
    - Initialize TranscribeStreamingManager and start stream
    - Create transcription record in database with status='IN_PROGRESS'
    - Emit session_ack message with job_id
    - Handle errors and emit error messages
    - _Requirements: 2.3, 3.1, 6.1, 6.2, 11.3, 11.4, 12.2, 12.3, 12.4, 12.5_
  
  - [x] 5.4 Implement audio_chunk event handler
    - Implement `@socketio.on('audio_chunk')` handler to receive binary audio data
    - Validate message format (byte 0 = 0x01, bytes 1-N = PCM data)
    - Forward chunk to TranscribeStreamingManager within 50ms
    - Append chunk to AudioBuffer for later S3 upload
    - Update session activity timestamp
    - Handle errors and emit error messages
    - _Requirements: 2.2, 3.2, 5.1, 8.1, 11.1_
  
  - [x] 5.5 Implement session_end event handler
    - Implement `@socketio.on('session_end')` handler
    - Stop TranscribeStreamingManager stream
    - Finalize AudioBuffer to MP3 format
    - Generate S3 key using pattern: `audio/{user_id}/{timestamp}_{uuid}.mp3`
    - Upload audio file to S3 with retry logic (2 retries)
    - Update transcription record status to 'COMPLETED' and store S3 key
    - Emit session_complete message with statistics
    - Remove session from SessionManager
    - Handle errors (S3 upload failures, database errors)
    - _Requirements: 3.5, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 6.4, 6.6, 8.2, 11.5, 11.6_
  
  - [x] 5.6 Implement disconnect event handler
    - Implement `@socketio.on('disconnect')` handler
    - Retrieve session from SessionManager
    - Clean up transcription stream and audio buffer
    - Update transcription record status if incomplete
    - Remove session from SessionManager
    - Log disconnect event
    - _Requirements: 8.2, 8.6_
  
  - [x] 5.7 Implement heartbeat mechanism
    - Create background task to send heartbeat messages every 30 seconds
    - Emit heartbeat to all connected clients
    - _Requirements: 11.7_
  
  - [ ]* 5.8 Write unit tests for Flask-SocketIO handlers
    - Test connection authentication and rejection
    - Test session_start creates session and starts transcription
    - Test audio_chunk forwards to transcribe and buffers
    - Test session_end uploads to S3 and saves to database
    - Test disconnect cleans up resources
    - Test error handling in each handler
    - Mock SocketIO emit, AWS services, database
    - _Requirements: 2.1, 3.1, 5.5, 6.1, 8.2_

- [x] 6. Checkpoint - Backend streaming infrastructure complete
  - Ensure all backend tests pass, verify AWS Transcribe integration works with test audio, ask the user if questions arise.

- [x] 7. Implement frontend audio capture module
  - [x] 7.1 Create AudioCapture class for microphone access
    - Implement `AudioCapture` class in `static/js/audio-capture.js`
    - Implement `initialize()` to request microphone permissions using `getUserMedia()`
    - Create AudioContext with target sample rate (8kHz, 16kHz, or 48kHz)
    - Handle permission denial with error event emission
    - _Requirements: 1.1, 1.2, 9.1_
  
  - [x] 7.2 Implement audio processing and chunking
    - Set up ScriptProcessorNode or AudioWorklet for audio processing
    - Configure buffer size to 4096 samples for 200-500ms chunks
    - Convert Float32Array to Int16Array PCM format
    - Emit 'chunk' events with PCM audio data
    - _Requirements: 1.3, 1.4_
  
  - [x] 7.3 Implement start and stop controls
    - Implement `start()` method to begin audio capture
    - Implement `stop()` method to terminate capture and cleanup resources
    - Disconnect audio nodes and close AudioContext on stop
    - _Requirements: 1.5_
  
  - [ ]* 7.4 Write unit tests for AudioCapture
    - Test microphone permission request
    - Test AudioContext initialization with correct sample rate
    - Test audio chunk generation and format
    - Test stop() cleanup and resource release
    - Test error handling for permission denial
    - Mock `navigator.mediaDevices.getUserMedia()` and AudioContext
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [ ]* 7.5 Write property test for audio chunk duration bounds
    - **Property 1: Audio Chunk Duration Bounds**
    - **Validates: Requirements 1.3**
    - Test that chunk duration is between 200ms and 500ms for various sample rates and buffer sizes
    - Use fast-check to generate random sample rates and buffer sizes

- [x] 8. Implement frontend WebSocket client
  - [x] 8.1 Create TranscriptionWebSocket class for WebSocket communication
    - Implement `TranscriptionWebSocket` class in `static/js/websocket-client.js`
    - Implement `connect()` to establish WebSocket connection using Socket.IO client
    - Implement connection event handlers: 'connect', 'disconnect', 'error'
    - Emit 'connected', 'closed', 'error' events to application
    - _Requirements: 2.1, 9.2_
  
  - [x] 8.2 Implement session initialization and audio transmission
    - Implement session_start message sending with user_id, session_id, quality, timestamp
    - Implement `sendAudioChunk()` to transmit binary audio data (byte 0 = 0x01, bytes 1-N = PCM)
    - Include session metadata with each transmission
    - Implement `endSession()` to send session_end message
    - _Requirements: 2.2, 2.3, 11.1, 11.3, 11.5_
  
  - [x] 8.3 Implement reconnection logic with exponential backoff
    - Implement automatic reconnection on connection failure
    - Use exponential backoff: 1s, 2s, 4s delays
    - Stop after 3 failed attempts and emit error event
    - _Requirements: 2.4, 9.2_
  
  - [x] 8.4 Implement audio buffering during connection interruptions
    - Create buffer to hold up to 5 seconds of audio during temporary disconnections
    - Implement buffer overflow handling
    - Retransmit buffered chunks on reconnection
    - _Requirements: 2.6_
  
  - [x] 8.5 Implement result and error message handlers
    - Implement handler for 'transcription_result' messages from server
    - Implement handler for 'session_ack' messages
    - Implement handler for 'session_complete' messages
    - Implement handler for 'error' messages
    - Implement handler for 'heartbeat' messages
    - Emit events to application layer
    - _Requirements: 4.1, 11.2, 11.4, 11.6, 11.7_
  
  - [ ]* 8.6 Write unit tests for TranscriptionWebSocket
    - Test connection establishment
    - Test session_start message format and content
    - Test audio chunk transmission format (binary with type byte)
    - Test session_end message
    - Test reconnection logic with exponential backoff
    - Test buffer behavior during connection interruption
    - Mock WebSocket API
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.6_
  
  - [ ]* 8.7 Write property test for audio transmission latency
    - **Property 3: Audio Transmission Latency**
    - **Validates: Requirements 2.2**
    - Test that audio chunk transmission completes within 100ms
    - Use fast-check to generate random audio data
  
  - [ ]* 8.8 Write property test for audio message format
    - **Property 25: Audio Message Format**
    - **Validates: Requirements 11.1**
    - Test that audio messages have byte 0 = 0x01 followed by PCM data
    - Use fast-check to generate random audio data

- [x] 9. Implement frontend transcription display
  - [x] 9.1 Create TranscriptionDisplay class for UI rendering
    - Implement `TranscriptionDisplay` class in `static/js/transcription-display.js`
    - Initialize with container DOM element
    - Create internal data structure to track segments (partial vs final)
    - _Requirements: 4.1, 4.2, 4.3_
  
  - [x] 9.2 Implement partial and final result rendering
    - Implement `updatePartial()` to update current segment in-place
    - Implement `appendFinal()` to replace partial with final and append to transcript
    - Ensure proper spacing and punctuation between segments
    - Apply visual highlight to current segment being transcribed
    - _Requirements: 4.2, 4.3, 4.4, 4.6_
  
  - [x] 9.3 Implement auto-scroll functionality
    - Implement auto-scroll to show most recent transcription text
    - Trigger scroll within 50ms of new text addition
    - _Requirements: 4.5_
  
  - [x] 9.4 Implement status and error display
    - Implement `showStatus()` to display connection status
    - Implement `showError()` to display error messages with retry button
    - Implement `clear()` to reset display
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
  
  - [ ]* 9.5 Write unit tests for TranscriptionDisplay
    - Test partial result updates (in-place replacement)
    - Test final result appending with spacing
    - Test auto-scroll behavior on new text
    - Test current segment highlighting
    - Test error message display
    - Test status indicator updates
    - Use DOM testing utilities (Jest + Testing Library)
    - _Requirements: 4.2, 4.3, 4.4, 4.5, 4.6_
  
  - [ ]* 9.6 Write property test for transcription display update consistency
    - **Property 8: Transcription Display Update Consistency**
    - **Validates: Requirements 4.2, 4.3**
    - Test that partial results update in-place and final results append
    - Use fast-check to generate random transcription results

- [x] 10. Integrate components and create main application controller
  - [x] 10.1 Create main transcription page controller
    - Create `static/js/transcription-controller.js` to orchestrate components
    - Initialize AudioCapture, TranscriptionWebSocket, and TranscriptionDisplay
    - Wire up event handlers between components
    - Implement start/stop recording button handlers
    - Handle component lifecycle (initialization, cleanup)
    - _Requirements: 1.1, 2.1, 4.1_
  
  - [x] 10.2 Create HTML page for live transcription
    - Create `templates/live_transcription.html` with UI elements
    - Add start/stop recording buttons
    - Add transcription display container
    - Add status indicator and error message areas
    - Include JavaScript modules (audio-capture.js, websocket-client.js, transcription-display.js, transcription-controller.js)
    - _Requirements: 1.1, 4.1, 9.1_
  
  - [x] 10.3 Add Flask route for live transcription page
    - Add route `/live-transcription` in Flask app
    - Require authentication (check session)
    - Render `live_transcription.html` template
    - _Requirements: 2.1_

- [x] 11. Checkpoint - Frontend integration complete
  - Ensure frontend components work together, test audio capture and WebSocket connection in browser, ask the user if questions arise.

- [x] 12. Implement error handling and recovery
  - [x] 12.1 Implement comprehensive error handling in backend
    - Add error handling for AWS Transcribe failures with appropriate error codes
    - Add error handling for S3 upload failures with retry logic (2 retries)
    - Add error handling for database errors with logging
    - Add error handling for session limit exceeded
    - Add error handling for buffer overflow (30-minute limit)
    - Emit structured error messages to clients
    - _Requirements: 3.6, 5.7, 8.4, 9.3, 9.4, 9.6_
  
  - [x] 12.2 Implement error display and recovery in frontend
    - Display user-friendly error messages for each error type
    - Implement retry button functionality for recoverable errors
    - Handle microphone access denial with permission instructions
    - Handle connection failures with reconnection status
    - Handle transcription service errors with retry option
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
  
  - [ ]* 12.3 Write integration tests for error scenarios
    - Test behavior when AWS Transcribe is unavailable
    - Test behavior when S3 upload fails
    - Test behavior when database is unavailable
    - Test behavior when session limit is reached
    - Test behavior when buffer overflows
    - Use fault injection and mocking
    - _Requirements: 3.6, 5.7, 8.4, 9.3, 9.4_

- [x] 13. Implement session cleanup and resource management
  - [x] 13.1 Implement idle session cleanup background task
    - Create background task to run every 60 seconds
    - Call `SessionManager.cleanup_idle_sessions()` to remove sessions idle >5 minutes
    - Log cleanup events with session count
    - _Requirements: 8.3_
  
  - [x] 13.2 Implement graceful shutdown handler
    - Register signal handler for SIGTERM/SIGINT
    - Close all active WebSocket connections within 30 seconds
    - Clean up all sessions and release resources
    - Log shutdown events
    - _Requirements: 8.5_
  
  - [ ]* 13.3 Write unit tests for session cleanup
    - Test idle session cleanup removes sessions after 5 minutes
    - Test graceful shutdown closes all connections
    - Test resource cleanup on session removal
    - _Requirements: 8.3, 8.5_

- [x] 14. Implement storage and database operations
  - [x] 14.1 Extend StorageManager for streaming audio uploads
    - Add method `upload_streaming_audio()` to upload MP3 files to S3
    - Implement S3 key generation following pattern: `audio/{user_id}/{timestamp}_{uuid}.mp3`
    - Add retry logic with exponential backoff (2 retries)
    - Measure and log upload latency
    - _Requirements: 5.4, 5.5, 5.6, 5.7_
  
  - [x] 14.2 Extend DatabaseManager for streaming transcription records
    - Add method `create_streaming_transcription()` to create record with streaming fields
    - Add method `update_transcription_status()` to update status and timestamp
    - Add method `append_transcript_text()` to append final results
    - Add method `get_transcription_by_session_id()` for session lookup
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.6_
  
  - [ ]* 14.3 Write unit tests for storage and database operations
    - Test S3 key generation follows correct pattern
    - Test MP3 upload with correct metadata
    - Test upload retry logic
    - Test transcription record creation with all fields
    - Test status updates and timestamp changes
    - Test transcript text appending
    - Mock boto3 S3 client and database connection
    - _Requirements: 5.4, 5.5, 5.6, 6.1, 6.2, 6.3, 6.4_
  
  - [ ]* 14.4 Write property test for S3 key pattern compliance
    - **Property 13: S3 Key Pattern Compliance**
    - **Validates: Requirements 5.4**
    - Test that generated S3 keys match pattern `audio/{user_id}/{timestamp}_{uuid}.mp3`
    - Use Hypothesis to generate random user_ids, timestamps, and UUIDs
  
  - [ ]* 14.5 Write property test for transcription record initialization
    - **Property 16: Transcription Record Initialization**
    - **Validates: Requirements 6.1, 6.2**
    - Test that transcription records contain required fields with correct initial status
    - Use Hypothesis to generate random record data
  
  - [ ]* 14.6 Write property test for transcription status lifecycle
    - **Property 18: Transcription Status Lifecycle**
    - **Validates: Requirements 6.4, 6.6**
    - Test that status transitions follow valid lifecycle and update timestamps
    - Use Hypothesis to generate random status transitions

- [x] 15. Implement configuration and quality settings
  - [x] 15.1 Add quality configuration support
    - Add quality parameter handling in session_start (low/medium/high)
    - Map quality to sample rates: low=8kHz, medium=16kHz, high=48kHz
    - Pass sample rate to AudioCapture, TranscribeStreamingManager, and database
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_
  
  - [ ]* 15.2 Write property test for sample rate configuration consistency
    - **Property 28: Sample Rate Configuration Consistency**
    - **Validates: Requirements 12.6**
    - Test that sample rate is consistent across capture, transmission, and transcription
    - Use Hypothesis to generate random quality settings

- [x] 16. Checkpoint - Core functionality complete
  - Ensure all core features work end-to-end, test with real audio input, verify S3 uploads and database records, ask the user if questions arise.

- [x] 17. Implement performance optimizations and monitoring
  - [x] 17.1 Add latency measurement and logging
    - Add timing instrumentation for audio capture buffering delay
    - Add timing instrumentation for backend processing overhead
    - Add timing instrumentation for display render latency
    - Add timing instrumentation for end-to-end latency (speech to display)
    - Log latency metrics to CloudWatch or application logs
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_
  
  - [x] 17.2 Optimize WebSocket message handling
    - Ensure audio_chunk handler processes within 100ms
    - Ensure result forwarding to client within 100ms
    - Use async/await patterns where appropriate
    - _Requirements: 3.2, 4.1_
  
  - [ ]* 17.3 Write performance tests for latency requirements
    - Test audio capture buffering delay <50ms
    - Test backend processing overhead <100ms
    - Test display render latency <50ms
    - Test end-to-end latency <3 seconds for 95th percentile
    - Test first partial result appears within 2 seconds
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ]* 18. Write integration tests for end-to-end flows
  - [ ]* 18.1 Write integration test for complete transcription session
    - Test full flow: connect → session_start → audio_chunks → results → session_end
    - Test partial and final result delivery
    - Test S3 upload and database persistence
    - Use real Flask-SocketIO test client with sample audio
    - _Requirements: 2.1, 3.1, 4.1, 5.5, 6.1_
  
  - [ ]* 18.2 Write integration test for session cleanup
    - Test session cleanup on normal closure
    - Test session cleanup on abnormal closure
    - Test resource release (audio buffer, transcribe stream)
    - _Requirements: 8.1, 8.2_
  
  - [ ]* 18.3 Write integration test for concurrent sessions
    - Test multiple concurrent sessions (up to 100)
    - Test session limit enforcement
    - Test session isolation (no cross-talk)
    - _Requirements: 8.4_

- [ ]* 19. Write load and stress tests
  - [ ]* 19.1 Write load tests for concurrent sessions
    - Test 100 concurrent sessions (maximum capacity)
    - Test session creation/cleanup under load
    - Test memory usage during 30-minute sessions
    - Test graceful degradation when approaching limits
    - _Requirements: 8.4, 10.6_
  
  - [ ]* 19.2 Write stress tests for edge cases
    - Test behavior beyond 100 concurrent sessions
    - Test rapid connect/disconnect cycles
    - Test large audio buffers (approaching 30-minute limit)
    - Test network interruption and recovery
    - _Requirements: 2.6, 8.3, 8.4_

- [x] 20. Final integration and documentation
  - [x] 20.1 Update API documentation
    - Document WebSocket protocol and message formats
    - Document error codes and recovery procedures
    - Document quality settings and sample rates
    - Add examples for client integration
  
  - [x] 20.2 Update deployment documentation
    - Document Terraform changes and deployment steps
    - Document environment variables and configuration
    - Document monitoring and logging setup
    - Add troubleshooting guide
  
  - [x] 20.3 Create user guide for live transcription feature
    - Document how to access live transcription page
    - Document browser requirements and permissions
    - Document quality settings and recommendations
    - Document error messages and solutions

- [x] 21. Final checkpoint - Feature complete
  - Run full test suite (unit, property, integration), verify all requirements are met, ensure documentation is complete, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation and provide opportunities for user feedback
- Property tests validate universal correctness properties across randomized inputs
- Unit tests validate specific examples, edge cases, and integration points
- The implementation uses Python (Flask, boto3, Hypothesis) for backend and JavaScript (Web Audio API, WebSocket, fast-check) for frontend
- Testing framework: pytest for Python, Jest for JavaScript
- All latency requirements are validated through performance tests
- Session management ensures proper resource cleanup and prevents memory leaks
