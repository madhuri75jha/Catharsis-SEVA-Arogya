# Requirements Document

## Introduction

This feature enables healthcare providers to view their recent consultations on the home page and access detailed consultation information. The system will display consultation cards showing patient information and timestamps, with the ability to expand the view to see all consultations and navigate to individual consultation details.

## Glossary

- **Consultation**: A complete medical interaction consisting of a transcription record and optionally an associated prescription
- **Consultation_Card**: A UI component displaying summary information about a single consultation
- **Home_Page**: The main landing page after user authentication
- **Consultation_Detail_View**: A page displaying complete information about a specific consultation including transcript, medical entities, and prescription data
- **Database_Manager**: The system component responsible for retrieving consultation data from PostgreSQL
- **User**: An authenticated healthcare provider using the application

## Requirements

### Requirement 1: Display Recent Consultations on Home Page

**User Story:** As a healthcare provider, I want to see my recent consultations on the home page, so that I can quickly access recent patient interactions.

#### Acceptance Criteria

1. WHEN the Home_Page loads, THE System SHALL retrieve the 10 most recent consultations for the authenticated User from the database
2. THE System SHALL display the 2 most recent consultations as Consultation_Cards in the "Recent Consultations" section
3. THE Consultation_Card SHALL display patient name, consultation timestamp, and consultation status
4. WHEN no consultations exist for the User, THE System SHALL display a message "No recent consultations found"
5. THE System SHALL order consultations by creation timestamp in descending order

### Requirement 2: View All Consultations

**User Story:** As a healthcare provider, I want to view all my recent consultations, so that I can access consultations beyond the 2 most recent ones.

#### Acceptance Criteria

1. WHEN the User clicks the "View All" button, THE System SHALL display all retrieved consultations (up to 10) in an expanded view
2. THE System SHALL maintain the descending chronological order in the expanded view
3. WHEN the expanded view is displayed, THE System SHALL provide a way to collapse back to showing only 2 consultations
4. THE expanded view SHALL display all Consultation_Cards with the same information format as the initial 2 cards

### Requirement 3: Navigate to Consultation Details

**User Story:** As a healthcare provider, I want to click on a consultation card, so that I can view the complete details of that consultation.

#### Acceptance Criteria

1. WHEN the User clicks on a Consultation_Card, THE System SHALL navigate to the Consultation_Detail_View for that consultation
2. THE Consultation_Detail_View SHALL display the complete transcript text
3. THE Consultation_Detail_View SHALL display extracted medical entities if available
4. WHERE a prescription exists for the consultation, THE Consultation_Detail_View SHALL display the prescription information
5. THE Consultation_Detail_View SHALL provide a way to navigate back to the Home_Page

### Requirement 4: Retrieve Consultation Data

**User Story:** As a healthcare provider, I want the system to efficiently retrieve my consultation data, so that the home page loads quickly.

#### Acceptance Criteria

1. THE Database_Manager SHALL query transcriptions and prescriptions for the authenticated User
2. THE System SHALL join transcription and prescription data by matching user_id and temporal proximity
3. WHEN a transcription has no associated prescription, THE System SHALL still include it as a consultation with null prescription data
4. THE System SHALL complete the data retrieval within 2 seconds under normal database load
5. IF the database query fails, THEN THE System SHALL log the error and display a user-friendly error message

### Requirement 5: Display Consultation Status

**User Story:** As a healthcare provider, I want to see the status of each consultation, so that I know which consultations are complete or in progress.

#### Acceptance Criteria

1. THE Consultation_Card SHALL display a status indicator based on the transcription status
2. WHEN the transcription status is "COMPLETED", THE System SHALL display a "Complete" status indicator
3. WHEN the transcription status is "IN_PROGRESS", THE System SHALL display an "In Progress" status indicator
4. WHEN the transcription status is "FAILED", THE System SHALL display a "Failed" status indicator
5. THE status indicator SHALL use distinct visual styling for each status type

### Requirement 6: Format Consultation Timestamps

**User Story:** As a healthcare provider, I want to see when each consultation occurred in a readable format, so that I can quickly identify recent vs older consultations.

#### Acceptance Criteria

1. THE System SHALL format timestamps as relative time for consultations within the last 24 hours
2. WHEN a consultation occurred less than 1 hour ago, THE System SHALL display "X minutes ago"
3. WHEN a consultation occurred between 1 and 24 hours ago, THE System SHALL display "X hours ago"
4. WHEN a consultation occurred more than 24 hours ago, THE System SHALL display the date in "MMM DD, YYYY" format
5. THE System SHALL use the consultation's created_at timestamp for all time calculations

### Requirement 7: Handle Missing Patient Information

**User Story:** As a healthcare provider, I want the system to handle consultations with missing patient names gracefully, so that all consultations are displayed even if data is incomplete.

#### Acceptance Criteria

1. WHEN a consultation has no patient name extracted, THE System SHALL display "Unknown Patient" on the Consultation_Card
2. WHEN a consultation has no transcript text, THE System SHALL display "No transcript available" in the Consultation_Detail_View
3. THE System SHALL display all consultations regardless of data completeness
4. THE Consultation_Card SHALL generate initials from the patient name if available, or use "?" for unknown patients

### Requirement 8: API Endpoint for Consultation Retrieval

**User Story:** As a frontend developer, I want a REST API endpoint to retrieve consultations, so that I can fetch consultation data asynchronously.

#### Acceptance Criteria

1. THE System SHALL provide a GET endpoint at "/api/consultations" for retrieving user consultations
2. THE endpoint SHALL require authentication and return only consultations for the authenticated User
3. THE endpoint SHALL accept an optional "limit" query parameter with a default value of 10
4. THE endpoint SHALL return consultation data in JSON format with transcription and prescription information
5. WHEN the request is successful, THE System SHALL return HTTP status 200 with the consultation list
6. IF authentication fails, THEN THE System SHALL return HTTP status 401
7. IF the database query fails, THEN THE System SHALL return HTTP status 500 with an error message

