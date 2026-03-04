# Requirements Document

## Introduction

This feature enables asynchronous push-to-talk audio recording and transcription for medical consultations. Currently, users must wait for each audio clip to be transcribed before recording the next one, which blocks the consultation workflow. This feature decouples recording from transcription, allowing doctors to record multiple audio clips in rapid succession while transcription happens asynchronously in the background.

## Glossary

- **Audio_Recording_System**: The client-side component that captures audio when the user presses and holds a button
- **Transcription_Queue**: A server-side queue that manages pending transcription jobs
- **Recording_Session**: A single press-and-hold audio capture instance that produces one audio clip
- **Transcription_Job**: An asynchronous task that processes one audio clip and produces text
- **Status_Tracker**: The component that monitors and reports the state of each recording and transcription
- **Consultation_Context**: The medical consultation session that contains multiple audio clips and their transcriptions

## Requirements

### Requirement 1: Asynchronous Recording

**User Story:** As a doctor, I want to record multiple audio clips without waiting for transcription, so that I can efficiently document patient consultations.

#### Acceptance Criteria

1. WHEN a user completes a Recording_Session, THE Audio_Recording_System SHALL immediately allow starting a new Recording_Session
2. THE Audio_Recording_System SHALL NOT block user interaction while Transcription_Jobs are processing
3. WHEN a Recording_Session completes, THE Audio_Recording_System SHALL assign a unique identifier to the audio clip
4. THE Audio_Recording_System SHALL upload completed audio clips to storage within 5 seconds of recording completion
5. WHEN an audio clip upload completes, THE Audio_Recording_System SHALL enqueue a Transcription_Job without blocking the user interface

### Requirement 2: Transcription Queue Management

**User Story:** As a system, I want to process transcription jobs asynchronously, so that recording and transcription can happen independently.

#### Acceptance Criteria

1. THE Transcription_Queue SHALL accept new Transcription_Jobs while other jobs are processing
2. THE Transcription_Queue SHALL process Transcription_Jobs in the order they were received (FIFO)
3. WHEN a Transcription_Job is added to the queue, THE Transcription_Queue SHALL return immediately without waiting for processing
4. THE Transcription_Queue SHALL process multiple Transcription_Jobs concurrently up to a configured limit
5. IF a Transcription_Job fails, THEN THE Transcription_Queue SHALL retry the job up to 3 times with exponential backoff
6. WHEN a Transcription_Job completes successfully, THE Transcription_Queue SHALL update the Consultation_Context with the transcribed text

### Requirement 3: Status Visibility

**User Story:** As a doctor, I want to see the status of each audio clip, so that I know which recordings have been transcribed.

#### Acceptance Criteria

1. THE Status_Tracker SHALL display the current state for each audio clip (recording, uploading, queued, transcribing, completed, failed)
2. WHEN a Recording_Session starts, THE Status_Tracker SHALL show "recording" status
3. WHEN an audio clip is uploading, THE Status_Tracker SHALL show "uploading" status with progress indication
4. WHEN a Transcription_Job is queued, THE Status_Tracker SHALL show "queued" status with queue position
5. WHEN a Transcription_Job is processing, THE Status_Tracker SHALL show "transcribing" status
6. WHEN a Transcription_Job completes, THE Status_Tracker SHALL show "completed" status and display the transcribed text
7. IF a Transcription_Job fails after all retries, THEN THE Status_Tracker SHALL show "failed" status with an error message
8. THE Status_Tracker SHALL update status in real-time using WebSocket events

### Requirement 4: Transcription Result Delivery

**User Story:** As a doctor, I want transcribed text to appear automatically when ready, so that I can review it without manual intervention.

#### Acceptance Criteria

1. WHEN a Transcription_Job completes, THE Status_Tracker SHALL display the transcribed text in the Consultation_Context
2. THE Status_Tracker SHALL append transcribed text to the Consultation_Context in the order recordings were made
3. WHILE a user is recording a new clip, THE Status_Tracker SHALL still display completed transcriptions from previous clips
4. THE Status_Tracker SHALL preserve all transcribed text even if the user navigates away and returns to the Consultation_Context
5. WHEN multiple Transcription_Jobs complete simultaneously, THE Status_Tracker SHALL display results in recording order

### Requirement 5: Error Handling and Recovery

**User Story:** As a doctor, I want the system to handle errors gracefully, so that I can continue working even if some transcriptions fail.

#### Acceptance Criteria

1. IF an audio upload fails, THEN THE Audio_Recording_System SHALL retry the upload up to 3 times
2. IF an audio upload fails after all retries, THEN THE Status_Tracker SHALL notify the user and allow manual retry
3. IF a Transcription_Job fails, THEN THE Transcription_Queue SHALL not block other jobs from processing
4. WHEN a Transcription_Job fails, THE Status_Tracker SHALL provide a retry button for that specific clip
5. IF the WebSocket connection is lost, THEN THE Audio_Recording_System SHALL reconnect and resume status updates
6. WHEN the WebSocket reconnects, THE Status_Tracker SHALL synchronize the current state of all pending and completed jobs

### Requirement 6: Resource Management

**User Story:** As a system administrator, I want the system to manage resources efficiently, so that it can handle multiple concurrent users.

#### Acceptance Criteria

1. THE Transcription_Queue SHALL limit concurrent transcription jobs to a configured maximum (default 10)
2. WHEN the queue reaches capacity, THE Transcription_Queue SHALL queue additional jobs without rejecting them
3. THE Audio_Recording_System SHALL limit the maximum number of pending uploads per user to 5
4. IF a user exceeds the pending upload limit, THEN THE Audio_Recording_System SHALL display a warning and block new recordings until uploads complete
5. THE Transcription_Queue SHALL clean up completed job metadata after 24 hours
6. THE Audio_Recording_System SHALL compress audio clips before upload to minimize bandwidth usage

### Requirement 7: Data Consistency

**User Story:** As a system, I want to maintain data consistency between recordings and transcriptions, so that no data is lost or duplicated.

#### Acceptance Criteria

1. THE Audio_Recording_System SHALL associate each audio clip with exactly one Transcription_Job
2. THE Transcription_Queue SHALL ensure each audio clip is transcribed exactly once
3. IF a Transcription_Job is retried, THEN THE Transcription_Queue SHALL not create duplicate transcriptions
4. THE Status_Tracker SHALL persist the association between audio clips and transcriptions in the database
5. WHEN a Consultation_Context is loaded, THE Status_Tracker SHALL display all audio clips and their transcription status
6. THE Audio_Recording_System SHALL prevent duplicate uploads of the same audio clip

### Requirement 8: Performance Requirements

**User Story:** As a doctor, I want the system to be responsive, so that I can work efficiently without delays.

#### Acceptance Criteria

1. THE Audio_Recording_System SHALL start a new Recording_Session within 100 milliseconds of user input
2. THE Audio_Recording_System SHALL complete audio upload within 5 seconds for clips up to 60 seconds long
3. THE Transcription_Queue SHALL start processing a Transcription_Job within 2 seconds of it being queued
4. THE Status_Tracker SHALL update the user interface within 500 milliseconds of receiving a status change event
5. THE Audio_Recording_System SHALL support recording clips up to 5 minutes in duration
6. THE Transcription_Queue SHALL complete transcription within 30 seconds for a 60-second audio clip under normal load

### Requirement 9: Visual Recording Feedback

**User Story:** As a doctor, I want clear visual feedback when recording is active, so that I know the system is capturing my voice.

#### Acceptance Criteria

1. WHEN a Recording_Session starts, THE Audio_Recording_System SHALL display a pulsing animation on the recording icon
2. WHILE a Recording_Session is active, THE Audio_Recording_System SHALL apply a subtle background color shift to indicate recording state
3. THE Audio_Recording_System SHALL pulse the recording icon at a frequency between 0.5 Hz and 1 Hz for visibility
4. WHEN a Recording_Session ends, THE Audio_Recording_System SHALL immediately stop the pulsing animation
5. THE Audio_Recording_System SHALL use distinct visual indicators that are clearly distinguishable from the idle state
6. THE Audio_Recording_System SHALL ensure visual feedback appears within 100 milliseconds of recording start

### Requirement 10: Streaming Transcription Display

**User Story:** As a doctor, I want to see transcribed text appear word-by-word, so that the interface feels fast and responsive.

#### Acceptance Criteria

1. WHEN transcribed text becomes available, THE Status_Tracker SHALL display it with a word-by-word reveal animation
2. THE Status_Tracker SHALL animate each word appearing with a smooth, subtle transition effect
3. THE Status_Tracker SHALL complete the word reveal animation within 50-100 milliseconds per word
4. WHILE text is being revealed, THE Status_Tracker SHALL allow users to interact with other interface elements
5. THE Status_Tracker SHALL maintain readability during the animation without distracting visual effects
6. WHEN all words have been revealed, THE Status_Tracker SHALL display the complete text in its final static state

### Requirement 11: Chunked Audio Processing

**User Story:** As a doctor, I want to see partial transcription results as I record, so that I get immediate feedback instead of waiting for the full clip.

#### Acceptance Criteria

1. WHILE a Recording_Session is active, THE Audio_Recording_System SHALL send audio chunks to the server at 5-10 second intervals
2. WHEN an audio chunk is received, THE Transcription_Queue SHALL process it immediately without waiting for the full recording
3. WHEN a chunk is transcribed, THE Status_Tracker SHALL display the partial transcription result immediately
4. THE Status_Tracker SHALL append new partial results to previously displayed text as additional chunks are processed
5. THE Audio_Recording_System SHALL maintain audio continuity across chunk boundaries to prevent word truncation
6. WHEN a Recording_Session completes, THE Transcription_Queue SHALL process any remaining audio and finalize the complete transcription
7. THE Status_Tracker SHALL indicate when partial results are being displayed versus when the final complete transcription is ready
