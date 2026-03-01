# Bugfix Requirements Document

## Introduction

The transcription page (`/transcription` route) is not starting the actual transcription functionality. When users access this page, they see hardcoded dummy text instead of a functional transcription interface. The page displays static placeholder content ("Ramesh... 45 years old... History of fever for 3 days...") and only runs a simple timer, but does not initialize the audio capture, WebSocket connection, or transcription display components that are required for real-time transcription.

This bug prevents users from using the transcription feature through the `/transcription` route, forcing them to use the `/live-transcription` route instead. The expected behavior is that the transcription page should initialize the TranscriptionController and provide a functional real-time transcription interface similar to the live transcription page.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user navigates to the `/transcription` route THEN the system displays hardcoded dummy text ("Ramesh... 45 years old... History of fever for 3 days...") instead of initializing transcription functionality

1.2 WHEN the transcription page loads THEN the system does not include the required JavaScript modules (audio-capture.js, websocket-client.js, transcription-display.js, transcription-controller.js)

1.3 WHEN the transcription page loads THEN the system does not initialize the TranscriptionController to enable audio capture and real-time transcription

1.4 WHEN the transcription page loads THEN the system only runs a simple timer script without connecting to the transcription backend services

1.5 WHEN a user clicks "Stop and Review" on the transcription page THEN the system navigates to the final prescription page without having captured any actual transcription data

### Expected Behavior (Correct)

2.1 WHEN a user navigates to the `/transcription` route THEN the system SHALL initialize the TranscriptionController and display a functional transcription interface

2.2 WHEN the transcription page loads THEN the system SHALL include all required JavaScript modules (audio-capture.js, websocket-client.js, transcription-display.js, transcription-controller.js)

2.3 WHEN the transcription page loads THEN the system SHALL initialize the TranscriptionController with proper configuration (websocketUrl, userId, quality, sampleRate)

2.4 WHEN the transcription page loads THEN the system SHALL automatically start audio capture and establish WebSocket connection for real-time transcription

2.5 WHEN transcription data is received THEN the system SHALL display the actual transcribed text in real-time, replacing any placeholder content

2.6 WHEN a user clicks "Stop and Review" THEN the system SHALL stop the transcription session, save the captured data, and navigate to the final prescription page with the actual transcription

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user navigates to the `/live-transcription` route THEN the system SHALL CONTINUE TO function correctly with manual start/stop controls

3.2 WHEN the TranscriptionController is initialized on any page THEN the system SHALL CONTINUE TO properly capture audio, establish WebSocket connections, and display transcriptions

3.3 WHEN a user completes a transcription session THEN the system SHALL CONTINUE TO save the transcription data to the database

3.4 WHEN a user navigates to the final prescription page after transcription THEN the system SHALL CONTINUE TO have access to the transcription data

3.5 WHEN the transcription page UI is displayed THEN the system SHALL CONTINUE TO maintain the existing visual design and layout (recording pulse animation, timer display, smart suggestions area)
