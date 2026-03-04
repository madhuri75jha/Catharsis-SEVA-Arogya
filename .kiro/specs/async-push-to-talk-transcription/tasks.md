# Implementation Plan: Async Push-to-Talk Transcription

## Overview

This implementation extends the existing real-time streaming transcription system to support asynchronous push-to-talk recording with chunked audio processing, visual feedback, and word-by-word text reveal animations. The system will allow doctors to record multiple audio clips without waiting for transcription, with real-time status updates via WebSocket.

## Tasks

- [x] 1. Database schema extensions
  - [x] 1.1 Add consultation and transcription clip ordering fields
    - Extend `consultations` table with status tracking fields
    - Add `clip_order` column to `transcriptions` table for ordering clips within a consultation
    - Add `chunk_sequence` column to track audio chunk order within a clip
    - Create indexes for efficient querying by consultation_id and clip_order
    - _Requirements: 7.1, 7.4, 7.5_
  
  - [ ]* 1.2 Write property test for database schema consistency
    - **Property 1: Unique clip ordering within consultation**
    - **Validates: Requirements 7.1, 7.2**

- [x] 2. Backend async queue infrastructure
  - [x] 2.1 Create transcription job queue manager
    - Implement FIFO queue for transcription jobs using Python asyncio.Queue
    - Add concurrent job processing with configurable limit (default 10)
    - Implement job retry logic with exponential backoff (max 3 retries)
    - Add job metadata tracking (status, timestamps, retry count)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 6.1, 6.2_
  
  - [ ]* 2.2 Write property test for queue FIFO ordering
    - **Property 5: Queue processes jobs in FIFO order**
    - **Validates: Requirements 2.2**
  
  - [x] 2.3 Implement session state manager for multi-clip consultations
    - Track active consultation sessions with multiple clips
    - Associate clips with consultation_id and maintain clip_order
    - Persist session state to database for recovery
    - _Requirements: 1.3, 7.1, 7.4_
  
  - [ ]* 2.4 Write property test for session state consistency
    - **Property 7: Session state persists across reconnections**
    - **Validates: Requirements 5.5, 5.6, 7.4**

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. WebSocket event handlers for async transcription
  - [x] 4.1 Add chunk_upload event handler
    - Handle audio chunk uploads (5-10 second intervals)
    - Enqueue transcription jobs for each chunk
    - Return immediate acknowledgment without blocking
    - Emit chunk_queued event with queue position
    - _Requirements: 11.1, 11.2, 2.3, 3.4_
  
  - [x] 4.2 Add transcription_progress event emitter
    - Emit real-time status updates (queued, transcribing, completed, failed)
    - Include queue position for queued jobs
    - Send partial transcription results as chunks complete
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.8, 11.3, 11.4_
  
  - [x] 4.3 Add clip_complete event handler
    - Finalize clip when recording ends
    - Process any remaining audio chunks
    - Update clip status to completed
    - Emit final transcription result
    - _Requirements: 11.6, 11.7, 4.1, 4.2_
  
  - [ ]* 4.4 Write property test for WebSocket event ordering
    - **Property 12: Events are delivered in causal order**
    - **Validates: Requirements 3.8, 4.5**

- [x] 5. Frontend audio chunking and upload
  - [x] 5.1 Implement audio chunker in JavaScript
    - Split recording into 5-10 second chunks using MediaRecorder
    - Maintain audio continuity across chunk boundaries
    - Generate unique chunk IDs with sequence numbers
    - _Requirements: 11.1, 11.5_
  
  - [x] 5.2 Implement chunk upload manager
    - Upload chunks immediately after recording
    - Track upload progress and status
    - Implement retry logic for failed uploads (max 3 retries)
    - Limit pending uploads per user to 5
    - _Requirements: 1.4, 5.1, 5.2, 6.3, 6.4_
  
  - [x] 5.3 Add recording session state management
    - Track multiple clips within a consultation
    - Assign clip_order to each recording
    - Allow starting new recording while previous clips are transcribing
    - _Requirements: 1.1, 1.2, 1.3, 4.3_
  
  - [ ]* 5.4 Write property test for chunk continuity
    - **Property 15: Audio chunks maintain continuity without gaps**
    - **Validates: Requirements 11.5**

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Visual feedback animations
  - [x] 7.1 Implement pulsing recording icon animation (CSS)
    - Add CSS keyframe animation for pulsing effect (0.5-1 Hz)
    - Apply subtle background color shift during recording
    - Trigger animation within 100ms of recording start
    - Stop animation immediately when recording ends
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_
  
  - [x] 7.2 Add recording state visual indicators (JavaScript)
    - Toggle CSS classes for recording/idle states
    - Ensure distinct visual states are clearly distinguishable
    - Update UI within 100ms of state changes
    - _Requirements: 9.5, 9.6_
  
  - [ ]* 7.3 Write unit tests for animation timing
    - Test animation starts within 100ms
    - Test animation stops immediately on recording end
    - _Requirements: 9.6_

- [x] 8. Word-by-word text reveal animation
  - [x] 8.1 Implement text reveal animation component (JavaScript)
    - Split transcribed text into words
    - Animate each word appearing with 50-100ms delay
    - Use smooth, subtle transition effects (fade-in or slide-in)
    - Maintain readability during animation
    - _Requirements: 10.1, 10.2, 10.3, 10.5, 10.6_
  
  - [x] 8.2 Add non-blocking animation rendering
    - Ensure animation doesn't block user interaction
    - Allow users to interact with other UI elements during animation
    - Display final static text when animation completes
    - _Requirements: 10.4, 10.6_
  
  - [ ]* 8.3 Write unit tests for text reveal timing
    - Test word reveal timing (50-100ms per word)
    - Test non-blocking behavior
    - _Requirements: 10.3, 10.4_

- [x] 9. Status tracking and display
  - [x] 9.1 Implement status tracker component (JavaScript)
    - Display status for each clip (recording, uploading, queued, transcribing, completed, failed)
    - Show queue position for queued clips
    - Display upload progress indicators
    - Show partial transcription results as they arrive
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 11.3, 11.4, 11.7_
  
  - [x] 9.2 Add transcription result display
    - Append transcriptions in recording order
    - Display partial results with "processing" indicator
    - Show final complete transcription when ready
    - Persist transcriptions across page navigation
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 11.7_
  
  - [ ]* 9.3 Write property test for status consistency
    - **Property 20: Status updates reflect actual system state**
    - **Validates: Requirements 3.1, 3.8**

- [x] 10. Error handling and recovery
  - [x] 10.1 Implement upload retry logic
    - Retry failed uploads up to 3 times
    - Show retry button for manual retry after all attempts fail
    - Display error messages to user
    - _Requirements: 5.1, 5.2_
  
  - [x] 10.2 Implement transcription job retry logic
    - Retry failed transcription jobs up to 3 times with exponential backoff
    - Don't block other jobs when one fails
    - Provide manual retry button for failed jobs
    - _Requirements: 2.5, 5.3, 5.4_
  
  - [x] 10.3 Add WebSocket reconnection handling
    - Detect WebSocket disconnection
    - Automatically reconnect with exponential backoff
    - Synchronize state after reconnection
    - Resume status updates for pending jobs
    - _Requirements: 5.5, 5.6_
  
  - [ ]* 10.4 Write property test for error recovery
    - **Property 25: System recovers from transient failures**
    - **Validates: Requirements 5.1, 5.3, 5.5**

- [x] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Resource management and optimization
  - [x] 12.1 Implement concurrent job limiting
    - Limit concurrent transcription jobs to configured maximum (default 10)
    - Queue additional jobs without rejecting them
    - _Requirements: 6.1, 6.2_
  
  - [x] 12.2 Add audio compression before upload
    - Compress audio chunks to minimize bandwidth
    - Use appropriate codec (MP3 or Opus)
    - Maintain acceptable audio quality for transcription
    - _Requirements: 6.6_
  
  - [x] 12.3 Implement job metadata cleanup
    - Clean up completed job metadata after 24 hours
    - Preserve transcription results in database
    - _Requirements: 6.5_
  
  - [ ]* 12.4 Write property test for resource limits
    - **Property 28: System respects concurrent job limits**
    - **Validates: Requirements 6.1, 6.2**

- [x] 13. Performance optimization
  - [x] 13.1 Optimize recording start latency
    - Ensure recording starts within 100ms of user input
    - Pre-initialize audio context and media recorder
    - _Requirements: 8.1_
  
  - [x] 13.2 Optimize upload performance
    - Complete uploads within 5 seconds for 60-second clips
    - Use parallel chunk uploads where possible
    - _Requirements: 8.2_
  
  - [x] 13.3 Optimize transcription processing
    - Start processing within 2 seconds of job queuing
    - Complete transcription within 30 seconds for 60-second clips under normal load
    - _Requirements: 8.3, 8.6_
  
  - [x] 13.4 Optimize UI update latency
    - Update UI within 500ms of status change events
    - Use efficient DOM updates (virtual DOM or batching)
    - _Requirements: 8.4_
  
  - [ ]* 13.5 Write performance tests
    - Test recording start latency (<100ms)
    - Test upload completion time (<5s for 60s clips)
    - Test UI update latency (<500ms)
    - _Requirements: 8.1, 8.2, 8.4_

- [x] 14. Integration and wiring
  - [x] 14.1 Wire frontend components to WebSocket handlers
    - Connect audio chunker to chunk_upload event
    - Connect status tracker to transcription_progress events
    - Connect error handlers to error events
    - _Requirements: 1.1, 1.2, 3.8, 4.1_
  
  - [x] 14.2 Wire backend queue to transcription service
    - Connect job queue to AWS Transcribe streaming manager
    - Route transcription results to WebSocket emitters
    - Update database with transcription results
    - _Requirements: 2.6, 4.1, 7.4_
  
  - [x] 14.3 Wire visual feedback to recording state
    - Connect recording state changes to animation triggers
    - Connect transcription results to text reveal animation
    - _Requirements: 9.1, 9.4, 10.1_
  
  - [ ]* 14.4 Write integration tests
    - Test end-to-end flow: record → chunk → upload → transcribe → display
    - Test multi-clip consultation workflow
    - Test error recovery flows
    - _Requirements: 1.1, 2.1, 3.1, 4.1_

- [x] 15. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Implementation uses Python (backend) and JavaScript (frontend)
- Existing streaming transcription infrastructure will be extended, not replaced
