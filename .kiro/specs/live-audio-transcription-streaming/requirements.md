# Requirements Document

## Introduction

This document specifies the requirements for implementing live audio transcription streaming capabilities in the SEVA Arogya medical transcription application. The feature enables real-time audio capture, streaming to AWS Transcribe, and live display of transcription results on the user interface. The system will store audio files in S3, persist transcription records in RDS, and provide a seamless real-time transcription experience for medical professionals.

## Glossary

- **Audio_Capture_Module**: Browser-based component that captures microphone audio using Web Audio API
- **Transcription_Service**: AWS Transcribe Medical service that converts speech to text
- **Streaming_Client**: WebSocket or HTTP client that transmits audio chunks to the backend
- **Transcription_Display**: UI component that renders transcription text in real-time
- **Audio_Storage**: S3 bucket designated for storing recorded audio files
- **Transcription_Database**: RDS PostgreSQL database storing transcription metadata and results
- **Flask_Backend**: Python Flask application server handling API requests and AWS service orchestration
- **Terraform_Infrastructure**: Infrastructure-as-code configuration managing AWS resources
- **Audio_Chunk**: Segment of audio data transmitted during streaming (typically 100-500ms)
- **Transcription_Job**: AWS Transcribe job instance processing audio input
- **WebSocket_Connection**: Bidirectional communication channel for real-time data exchange
- **Partial_Result**: Interim transcription output before final stabilization
- **Final_Result**: Stabilized transcription output for a speech segment

## Requirements

### Requirement 1: Real-Time Audio Capture

**User Story:** As a medical professional, I want to capture audio from my microphone in real-time, so that I can dictate patient notes hands-free during consultations.

#### Acceptance Criteria

1. WHEN the user navigates to the transcription page, THE Audio_Capture_Module SHALL request microphone permissions
2. WHEN microphone access is granted, THE Audio_Capture_Module SHALL initialize audio capture at 16kHz sample rate
3. WHILE audio capture is active, THE Audio_Capture_Module SHALL collect audio in chunks of 200-500ms duration
4. THE Audio_Capture_Module SHALL encode audio chunks in PCM format compatible with AWS Transcribe
5. WHEN the user clicks the stop button, THE Audio_Capture_Module SHALL terminate audio capture and finalize the recording
6. IF microphone access is denied, THEN THE Flask_Backend SHALL display an error message instructing the user to enable microphone permissions

### Requirement 2: Audio Streaming to Backend

**User Story:** As a medical professional, I want my audio to be transmitted immediately to the transcription service, so that I can see transcription results without delay.

#### Acceptance Criteria

1. WHEN audio capture begins, THE Streaming_Client SHALL establish a WebSocket connection to the Flask_Backend
2. WHILE the WebSocket connection is active, THE Streaming_Client SHALL transmit each Audio_Chunk within 100ms of capture
3. THE Streaming_Client SHALL include session metadata (user_id, timestamp) with each Audio_Chunk transmission
4. IF the WebSocket connection fails, THEN THE Streaming_Client SHALL attempt reconnection with exponential backoff up to 3 retries
5. WHEN the WebSocket connection cannot be established after retries, THE Streaming_Client SHALL fall back to HTTP chunked upload mode
6. THE Streaming_Client SHALL buffer up to 5 seconds of audio during temporary connection interruptions

### Requirement 3: AWS Transcribe Streaming Integration

**User Story:** As a system administrator, I want the backend to stream audio to AWS Transcribe in real-time, so that transcription results are generated with minimal latency.

#### Acceptance Criteria

1. WHEN the Flask_Backend receives the first Audio_Chunk, THE Flask_Backend SHALL initiate a streaming Transcription_Job with AWS Transcribe Medical
2. WHILE receiving Audio_Chunks, THE Flask_Backend SHALL forward each chunk to the active Transcription_Job within 50ms
3. THE Flask_Backend SHALL configure the Transcription_Job with language_code='en-US' and specialty='PRIMARYCARE'
4. THE Flask_Backend SHALL configure the Transcription_Job to return both partial and final results
5. WHEN the audio stream ends, THE Flask_Backend SHALL signal stream completion to the Transcription_Job
6. IF the Transcription_Job fails, THEN THE Flask_Backend SHALL log the error and return an error response to the client

### Requirement 4: Real-Time Transcription Display

**User Story:** As a medical professional, I want to see transcription text appear on screen as I speak, so that I can verify accuracy and make corrections if needed.

#### Acceptance Criteria

1. WHEN the Flask_Backend receives a Partial_Result from the Transcription_Service, THE Flask_Backend SHALL transmit it to the Transcription_Display via WebSocket within 100ms
2. WHILE receiving Partial_Results, THE Transcription_Display SHALL update the current text segment with the latest partial transcription
3. WHEN the Flask_Backend receives a Final_Result, THE Transcription_Display SHALL replace the corresponding Partial_Result with the Final_Result
4. THE Transcription_Display SHALL append Final_Results to the transcription text with proper spacing and punctuation
5. THE Transcription_Display SHALL auto-scroll to show the most recent transcription text
6. THE Transcription_Display SHALL highlight the current segment being transcribed with a visual indicator

### Requirement 5: Audio File Storage

**User Story:** As a system administrator, I want recorded audio files stored securely in S3, so that they can be retrieved for audit or reprocessing purposes.

#### Acceptance Criteria

1. WHILE receiving Audio_Chunks, THE Flask_Backend SHALL accumulate chunks in memory for the complete recording
2. WHEN audio capture completes, THE Flask_Backend SHALL combine all Audio_Chunks into a single audio file
3. THE Flask_Backend SHALL encode the complete audio file in MP3 format with 64kbps bitrate
4. THE Flask_Backend SHALL generate a unique S3 key using the pattern: `audio/{user_id}/{timestamp}_{uuid}.mp3`
5. THE Flask_Backend SHALL upload the audio file to the Audio_Storage bucket within 5 seconds of recording completion
6. WHEN the upload succeeds, THE Flask_Backend SHALL store the S3 key in the Transcription_Database
7. IF the upload fails, THEN THE Flask_Backend SHALL retry up to 2 times before returning an error

### Requirement 6: Transcription Record Persistence

**User Story:** As a medical professional, I want my transcription records saved to the database, so that I can access them later for prescription generation.

#### Acceptance Criteria

1. WHEN a Transcription_Job is initiated, THE Flask_Backend SHALL create a transcription record in the Transcription_Database with status='IN_PROGRESS'
2. THE Flask_Backend SHALL store the job_id, user_id, audio_s3_key, and creation timestamp in the transcription record
3. WHILE receiving Final_Results, THE Flask_Backend SHALL append each Final_Result to the transcript_text field in the database
4. WHEN the Transcription_Job completes successfully, THE Flask_Backend SHALL update the transcription record status to 'COMPLETED'
5. IF the Transcription_Job fails, THEN THE Flask_Backend SHALL update the transcription record status to 'FAILED' and store the failure reason
6. THE Flask_Backend SHALL update the transcription record's updated_at timestamp with each database modification

### Requirement 7: Terraform Infrastructure Configuration

**User Story:** As a DevOps engineer, I want Terraform to provision AWS Transcribe permissions and configuration, so that the Flask application can use the transcription service.

#### Acceptance Criteria

1. THE Terraform_Infrastructure SHALL create an IAM policy granting transcribe:StartStreamTranscription permission to the ECS task role
2. THE Terraform_Infrastructure SHALL create an IAM policy granting transcribe:StartMedicalStreamTranscription permission to the ECS task role
3. THE Terraform_Infrastructure SHALL attach the transcribe policies to the existing ECS task role
4. THE Terraform_Infrastructure SHALL add AWS_TRANSCRIBE_REGION environment variable to the ECS task definition
5. THE Terraform_Infrastructure SHALL configure the ECS task role with permissions to access the Audio_Storage bucket for transcription output
6. WHEN Terraform apply completes, THE Terraform_Infrastructure SHALL output the transcribe service endpoint URL

### Requirement 8: Session Management and Cleanup

**User Story:** As a system administrator, I want proper cleanup of streaming resources, so that the system doesn't leak connections or memory.

#### Acceptance Criteria

1. WHEN a WebSocket connection is established, THE Flask_Backend SHALL register the connection in an active sessions registry
2. WHEN a WebSocket connection closes normally, THE Flask_Backend SHALL remove the connection from the registry and release associated resources
3. IF a WebSocket connection is idle for more than 5 minutes, THEN THE Flask_Backend SHALL terminate the connection and clean up resources
4. THE Flask_Backend SHALL limit concurrent streaming sessions to 100 per server instance
5. WHEN the server receives a shutdown signal, THE Flask_Backend SHALL gracefully close all active WebSocket connections within 30 seconds
6. THE Flask_Backend SHALL log session start, end, and error events for monitoring purposes

### Requirement 9: Error Handling and User Feedback

**User Story:** As a medical professional, I want clear error messages when transcription fails, so that I can take appropriate action to resolve issues.

#### Acceptance Criteria

1. IF audio capture fails to initialize, THEN THE Transcription_Display SHALL show an error message: "Unable to access microphone. Please check permissions."
2. IF the WebSocket connection fails after all retries, THEN THE Transcription_Display SHALL show an error message: "Connection lost. Please check your internet connection."
3. IF the Transcription_Job fails, THEN THE Transcription_Display SHALL show an error message: "Transcription service unavailable. Please try again."
4. IF S3 upload fails after retries, THEN THE Flask_Backend SHALL return an error response with message: "Failed to save audio file. Please try again."
5. WHEN an error occurs, THE Transcription_Display SHALL provide a "Retry" button to restart the transcription session
6. THE Flask_Backend SHALL log all errors with sufficient context for debugging (user_id, job_id, error_code, stack_trace)

### Requirement 10: Performance and Latency Requirements

**User Story:** As a medical professional, I want transcription to appear quickly as I speak, so that the system feels responsive and natural.

#### Acceptance Criteria

1. THE system SHALL display the first Partial_Result within 2 seconds of the user starting to speak
2. THE system SHALL maintain end-to-end latency (speech to display) of less than 3 seconds for 95% of transcription segments
3. THE Audio_Capture_Module SHALL introduce less than 50ms of buffering delay
4. THE Flask_Backend SHALL process and forward Audio_Chunks with less than 100ms of processing overhead
5. THE Transcription_Display SHALL render transcription updates within 50ms of receiving results from the backend
6. THE system SHALL support continuous transcription sessions of up to 30 minutes without performance degradation

### Requirement 11: WebSocket Protocol Specification

**User Story:** As a developer, I want a well-defined WebSocket protocol, so that the frontend and backend can communicate reliably.

#### Acceptance Criteria

1. THE Streaming_Client SHALL send audio data messages in binary format with message type identifier in the first byte
2. THE Flask_Backend SHALL send transcription result messages in JSON format with fields: type, is_partial, text, timestamp
3. THE Streaming_Client SHALL send a session_start message containing user_id and session_id when initiating a session
4. THE Flask_Backend SHALL respond to session_start with a session_ack message containing job_id
5. THE Streaming_Client SHALL send a session_end message when the user stops recording
6. THE Flask_Backend SHALL send a session_complete message with final statistics when transcription finishes
7. THE Flask_Backend SHALL send heartbeat messages every 30 seconds to maintain connection liveness

### Requirement 12: Audio Format and Quality Configuration

**User Story:** As a system administrator, I want configurable audio quality settings, so that I can balance transcription accuracy with bandwidth usage.

#### Acceptance Criteria

1. THE Audio_Capture_Module SHALL support sample rates of 8kHz, 16kHz, and 48kHz
2. THE Flask_Backend SHALL accept a quality parameter with values: 'low' (8kHz), 'medium' (16kHz), 'high' (48kHz)
3. WHERE quality='low', THE Audio_Capture_Module SHALL capture audio at 8kHz sample rate
4. WHERE quality='medium', THE Audio_Capture_Module SHALL capture audio at 16kHz sample rate (default)
5. WHERE quality='high', THE Audio_Capture_Module SHALL capture audio at 48kHz sample rate
6. THE Flask_Backend SHALL configure the Transcription_Job with the sample rate matching the quality parameter
