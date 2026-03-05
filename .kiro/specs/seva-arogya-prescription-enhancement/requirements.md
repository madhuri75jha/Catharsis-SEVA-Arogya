# Requirements Document

## Introduction

This document specifies requirements for enhancing the SEVA Arogya prescription management application. The enhancement adds comprehensive prescription workflow management including AI-powered content generation, section-by-section approval, role-based access control, audit logging, PDF generation, and soft delete capabilities. The system extends the existing application without rewriting core functionality.

## Glossary

- **Prescription_System**: The SEVA Arogya prescription management application
- **Prescription**: A medical prescription document containing multiple sections with patient and treatment information
- **Section**: A discrete component of a prescription (e.g., diagnosis, medications, instructions)
- **Doctor**: A medical professional who creates and finalizes prescriptions
- **Hospital_Admin**: An administrator who manages hospital settings and doctors, may also be a Doctor
- **Developer_Admin**: A system administrator with full cross-hospital access and system management capabilities
- **Bedrock_Service**: AWS Bedrock AI service that generates prescription content
- **PDF_Generator**: Lambda-based service that creates PDF documents from prescription data
- **CloudWatch_Service**: AWS CloudWatch logging service
- **Log_Viewer**: In-app UI component for viewing CloudWatch logs
- **Sidebar**: Navigation menu component that adapts to mobile and desktop layouts
- **Transition_Overlay**: Branded animation displayed during page navigation

## Requirements

### Requirement 1: Prescription State Management

**User Story:** As a Doctor, I want prescriptions to follow a defined lifecycle, so that I can track progress from creation to finalization

#### Acceptance Criteria

1. THE Prescription_System SHALL support four prescription states: Draft, InProgress, Finalized, and Deleted
2. WHEN a prescription is created, THE Prescription_System SHALL set the state to Draft
3. WHEN a Doctor opens the finalization view, THE Prescription_System SHALL transition the state from Draft to InProgress
4. WHEN a Doctor completes all section approvals, THE Prescription_System SHALL enable the finalize action
5. WHEN a Doctor finalizes a prescription, THE Prescription_System SHALL transition the state to Finalized and record finalized_at timestamp and finalized_by user identifier
6. WHILE a prescription is in Finalized state, THE Prescription_System SHALL prevent all content modifications
7. WHEN a Doctor deletes a prescription, THE Prescription_System SHALL transition the state to Deleted and record deleted_at timestamp and deleted_by user identifier and pre_deleted_state value

### Requirement 2: Bedrock AI Content Integration

**User Story:** As a Doctor, I want AI-generated prescription content loaded automatically, so that I can review and approve sections efficiently

#### Acceptance Criteria

1. WHEN a prescription transitions to InProgress state, THE Prescription_System SHALL load content from Bedrock_Service output into prescription sections
2. THE Prescription_System SHALL preserve the Bedrock_Service payload structure when populating sections
3. WHERE Bedrock_Service output is available, THE Prescription_System SHALL map content to corresponding section keys
4. WHEN Bedrock_Service content is loaded, THE Prescription_System SHALL set each section status to Pending

### Requirement 3: Section Approval Workflow

**User Story:** As a Doctor, I want to approve or reject individual prescription sections, so that I can ensure accuracy before finalization

#### Acceptance Criteria

1. WHILE a prescription is in InProgress state, THE Prescription_System SHALL display section status as Pending, Approved, or Rejected
2. WHEN a Doctor approves a section, THE Prescription_System SHALL set the section status to Approved
3. WHEN a Doctor rejects a section, THE Prescription_System SHALL set the section status to Rejected and enable inline editing for that section
4. WHEN a Doctor saves edited section content, THE Prescription_System SHALL set the section status to Pending
5. THE Prescription_System SHALL reuse the existing section edit UI component for rejected section editing
6. WHEN all required sections have Approved status, THE Prescription_System SHALL enable the finalize button
7. WHILE any required section has Pending or Rejected status, THE Prescription_System SHALL disable the finalize button

### Requirement 4: Read-Only Finalized Prescriptions

**User Story:** As a Doctor, I want finalized prescriptions to be immutable, so that the medical record remains accurate and unaltered

#### Acceptance Criteria

1. WHILE a prescription is in Finalized state, THE Prescription_System SHALL hide all section approval controls
2. WHILE a prescription is in Finalized state, THE Prescription_System SHALL hide all section edit controls
3. WHILE a prescription is in Finalized state, THE Prescription_System SHALL disable all section modification actions
4. WHILE a prescription is in Finalized state, THE Prescription_System SHALL display section content in read-only mode
5. WHILE a prescription is in Finalized state, THE Prescription_System SHALL display the PDF download button

### Requirement 5: Post-Finalization Thank You Page

**User Story:** As a Doctor, I want confirmation after finalizing a prescription, so that I know the action succeeded

#### Acceptance Criteria

1. WHEN a prescription finalization succeeds, THE Prescription_System SHALL redirect to the thank you page
2. WHEN the thank you page loads, THE Prescription_System SHALL display a randomly selected message from a predefined list
3. THE Prescription_System SHALL display a "Back to Prescriptions" button on the thank you page
4. WHEN the Doctor clicks "Back to Prescriptions", THE Prescription_System SHALL navigate to the prescriptions list page

### Requirement 6: Prescriptions List Page

**User Story:** As a Doctor, I want to view all my prescriptions in a searchable table, so that I can find and manage them efficiently

#### Acceptance Criteria

1. THE Prescription_System SHALL provide a prescriptions list page at route /prescriptions
2. THE Prescription_System SHALL display a search box with debounced input on the prescriptions list page
3. THE Prescription_System SHALL display filter controls for Doctor and date range on the prescriptions list page
4. THE Prescription_System SHALL display a table with columns: Prescription ID, Patient identifier, Doctor, Created date and time, Prescription state, Section statuses
5. WHEN a user enters search text, THE Prescription_System SHALL filter prescriptions matching the search query within 300 milliseconds of the last keystroke
6. WHEN a user selects a Doctor filter, THE Prescription_System SHALL display only prescriptions created by that Doctor
7. WHEN a user selects a date range filter, THE Prescription_System SHALL display only prescriptions created within that range
8. THE Prescription_System SHALL display section statuses as compact icons or pills for each prescription row

### Requirement 7: Home Page Integration with Prescriptions List

**User Story:** As a Doctor, I want to navigate from the home page to the prescriptions list, so that I can access my prescriptions quickly

#### Acceptance Criteria

1. WHEN a user clicks "View all" on the home page, THE Prescription_System SHALL navigate to /prescriptions
2. WHEN a user submits a search on the home page, THE Prescription_System SHALL navigate to /prescriptions with the search query as a URL parameter
3. WHEN the prescriptions list page loads with a query parameter, THE Prescription_System SHALL prefill the search box and execute the search

### Requirement 8: Role-Based Prescription Scoping

**User Story:** As a Hospital_Admin, I want to see all prescriptions in my hospital, so that I can monitor operations

#### Acceptance Criteria

1. WHEN a Doctor views the prescriptions list, THE Prescription_System SHALL display only prescriptions created by that Doctor
2. WHEN a Hospital_Admin views the prescriptions list, THE Prescription_System SHALL display all prescriptions within the admin's hospital
3. WHEN a Developer_Admin views the prescriptions list, THE Prescription_System SHALL display all prescriptions across all hospitals

### Requirement 9: Single Prescription View

**User Story:** As a Doctor, I want to view complete prescription details including audio and transcription, so that I can review all information in one place

#### Acceptance Criteria

1. THE Prescription_System SHALL provide a single prescription view page at route /prescriptions/:id
2. THE Prescription_System SHALL display audio playback controls for each audio file associated with the prescription
3. THE Prescription_System SHALL display transcription text linked to each audio file
4. THE Prescription_System SHALL display prescription sections in read-only visual format
5. THE Prescription_System SHALL display a "Download PDF" button on the single prescription view
6. THE Prescription_System SHALL display delete and restore buttons based on prescription state and user permissions

### Requirement 10: Soft Delete with Restore Capability

**User Story:** As a Doctor, I want to delete prescriptions with the ability to restore them, so that I can recover from accidental deletions

#### Acceptance Criteria

1. WHEN a Doctor clicks the delete button, THE Prescription_System SHALL display a confirmation modal
2. WHEN a Doctor confirms deletion, THE Prescription_System SHALL set prescription state to Deleted and record deleted_at timestamp and deleted_by user identifier and pre_deleted_state value
3. WHEN a prescription is deleted, THE Prescription_System SHALL retain the database record
4. WHILE a prescription is in Deleted state and deleted_at is within 30 days, THE Prescription_System SHALL display a restore button to the creator Doctor
5. WHILE a prescription is in Deleted state and deleted_at is within 30 days, THE Prescription_System SHALL display a restore button to Developer_Admin users
6. WHEN a Doctor clicks restore, THE Prescription_System SHALL set prescription state to the pre_deleted_state value and clear deleted_at and deleted_by fields
7. THE Prescription_System SHALL provide a scheduled cleanup process that executes daily
8. WHEN the cleanup process runs, THE Prescription_System SHALL identify prescriptions with state Deleted and deleted_at older than 30 days
9. WHEN the cleanup process identifies expired deleted prescriptions, THE Prescription_System SHALL permanently delete the database records
10. WHEN the cleanup process permanently deletes a prescription, THE Prescription_System SHALL delete associated audio files and transcription files and PDF files from S3 storage

### Requirement 11: On-Demand PDF Generation

**User Story:** As a Doctor, I want to generate prescription PDFs on demand, so that I can download them when needed without storage overhead

#### Acceptance Criteria

1. WHEN a user clicks "Download PDF", THE Prescription_System SHALL call the PDF generation endpoint with the prescription identifier
2. WHEN the PDF generation endpoint receives a request, THE PDF_Generator SHALL fetch prescription data and hospital data from the database
3. WHEN the PDF_Generator has fetched data, THE PDF_Generator SHALL render a PDF document using section-based layout
4. WHEN the PDF_Generator renders the document, THE PDF_Generator SHALL save the file to S3 storage
5. WHEN the PDF_Generator saves the file, THE PDF_Generator SHALL return a signed URL to the client
6. WHEN the client receives the signed URL, THE Prescription_System SHALL initiate file download

### Requirement 12: Dynamic PDF Section Rendering

**User Story:** As a Developer_Admin, I want the PDF generator to support new sections automatically, so that I can add prescription sections without modifying PDF code

#### Acceptance Criteria

1. THE PDF_Generator SHALL iterate through prescription sections in defined order
2. THE PDF_Generator SHALL render only sections that exist in the prescription data
3. FOR ALL sections in the prescription, THE PDF_Generator SHALL display section title and content block
4. WHEN a new section type is added to prescription data, THE PDF_Generator SHALL render it without code modifications
5. THE PDF_Generator SHALL use a section-driven layout algorithm that adapts to variable section counts

### Requirement 13: Hospital Data in PDF

**User Story:** As a Doctor, I want hospital information displayed on prescription PDFs, so that patients can contact the facility

#### Acceptance Criteria

1. THE PDF_Generator SHALL include hospital logo_url in the PDF header
2. THE PDF_Generator SHALL include hospital name in the PDF header
3. THE PDF_Generator SHALL include hospital address in the PDF header
4. WHERE hospital phone is available, THE PDF_Generator SHALL include it in the PDF header
5. WHERE hospital email is available, THE PDF_Generator SHALL include it in the PDF header
6. WHERE hospital registration_number is available, THE PDF_Generator SHALL include it in the PDF header
7. WHERE hospital website is available, THE PDF_Generator SHALL include it in the PDF header

### Requirement 14: Role-Based Sidebar Navigation

**User Story:** As a user, I want navigation options appropriate to my role, so that I can access relevant features efficiently

#### Acceptance Criteria

1. THE Prescription_System SHALL display a responsive sidebar navigation menu
2. WHEN a Doctor logs in, THE Sidebar SHALL display menu items: Home, Create Prescription, Prescriptions, Profile, Dashboard
3. WHEN a Hospital_Admin logs in, THE Sidebar SHALL display all Doctor menu items plus Hospital Settings
4. WHEN a Developer_Admin logs in, THE Sidebar SHALL display menu items: Prescriptions, Hospitals CRUD, CloudWatch Logs
5. WHEN the viewport width is less than 768 pixels, THE Sidebar SHALL render as a mobile drawer
6. WHEN the viewport width is 768 pixels or greater, THE Sidebar SHALL render as a fixed sidebar

### Requirement 15: Doctor Profile Display

**User Story:** As a Doctor, I want to view my profile information, so that I can verify my displayed credentials

#### Acceptance Criteria

1. THE Prescription_System SHALL provide a profile page displaying doctor signature
2. THE Prescription_System SHALL display doctor name on the profile page
3. THE Prescription_System SHALL display doctor specialty on the profile page
4. THE Prescription_System SHALL display doctor availability on the profile page
5. WHILE viewing the profile page, THE Prescription_System SHALL prevent editing of profile fields

### Requirement 16: Hospital Settings Management

**User Story:** As a Hospital_Admin, I want to edit hospital information and manage doctors, so that I can maintain accurate facility data

#### Acceptance Criteria

1. THE Prescription_System SHALL provide a hospital settings page accessible to Hospital_Admin users
2. THE Prescription_System SHALL display editable fields for hospital name, address, phone, email, registration_number, website, and logo_url
3. WHEN a Hospital_Admin saves hospital changes, THE Prescription_System SHALL update the hospital record in the database
4. THE Prescription_System SHALL display a list of doctors associated with the hospital
5. THE Prescription_System SHALL provide controls to add and remove doctor associations

### Requirement 17: CloudWatch Logs Viewer

**User Story:** As a Developer_Admin, I want to view application logs in the UI, so that I can troubleshoot issues without accessing AWS console

#### Acceptance Criteria

1. THE Prescription_System SHALL provide a logs viewer page at route /logs accessible only to Developer_Admin users
2. THE Log_Viewer SHALL display a date range selector with default range of 24 hours
3. THE Log_Viewer SHALL display a text search filter
4. WHEN a Developer_Admin selects a date range, THE Log_Viewer SHALL fetch logs from CloudWatch_Service for that range
5. WHEN a Developer_Admin enters search text, THE Log_Viewer SHALL filter displayed logs to entries containing that text
6. THE Log_Viewer SHALL display log entries with timestamp and message
7. THE Log_Viewer SHALL display pagination controls or a "Load more" button
8. THE Prescription_System SHALL provide a backend endpoint that calls CloudWatch_Service APIs using credentials from environment configuration
9. THE Prescription_System SHALL prevent exposure of AWS credentials to the browser

### Requirement 18: CloudWatch Integration Configuration

**User Story:** As a Developer_Admin, I want the system to use environment configuration for CloudWatch access, so that credentials remain secure

#### Acceptance Criteria

1. THE Prescription_System SHALL read CloudWatch service ARN from environment variables
2. THE Prescription_System SHALL read AWS credentials from environment variables
3. THE Prescription_System SHALL use environment configuration to authenticate with CloudWatch_Service
4. THE Prescription_System SHALL execute CloudWatch API calls only from backend services

### Requirement 19: Transition Overlay Branding

**User Story:** As a user, I want to see branded transitions between pages, so that the application feels polished and professional

#### Acceptance Criteria

1. WHEN a route change occurs, THE Transition_Overlay SHALL display before the new page renders
2. THE Transition_Overlay SHALL display "SEVA Arogya" text in the same font as the login page
3. THE Transition_Overlay SHALL animate the login icon with fade or slide effect
4. WHEN the new page is ready, THE Transition_Overlay SHALL fade out within 500 milliseconds
5. THE Transition_Overlay SHALL use styling consistent with the existing application theme

### Requirement 20: Permission Enforcement for Prescription Operations

**User Story:** As a system administrator, I want permissions enforced consistently, so that users can only perform authorized actions

#### Acceptance Criteria

1. WHILE a prescription is in Finalized state, THE Prescription_System SHALL prevent all users from modifying prescription content
2. WHILE a prescription is in Deleted state, THE Prescription_System SHALL prevent all users from modifying prescription content
3. WHEN a Doctor attempts to finalize a prescription, THE Prescription_System SHALL verify the Doctor is the creator before allowing the action
4. WHEN a Doctor attempts to delete a prescription, THE Prescription_System SHALL verify the Doctor is the creator before allowing the action
5. WHEN a Doctor attempts to restore a prescription, THE Prescription_System SHALL verify the Doctor is the creator or is a Developer_Admin before allowing the action
6. WHEN a Hospital_Admin attempts to view prescriptions, THE Prescription_System SHALL filter results to only prescriptions within the admin's hospital
7. WHEN a Developer_Admin attempts to view prescriptions, THE Prescription_System SHALL display all prescriptions without filtering

### Requirement 21: Data Model Extensions

**User Story:** As a developer, I want the database schema to support all new features, so that data is stored correctly

#### Acceptance Criteria

1. THE Prescription_System SHALL store prescription state as one of: Draft, InProgress, Finalized, Deleted
2. THE Prescription_System SHALL store created_by_doctor_id for each prescription
3. THE Prescription_System SHALL store finalized_at timestamp and finalized_by user identifier for finalized prescriptions
4. THE Prescription_System SHALL store deleted_at timestamp and deleted_by user identifier and pre_deleted_state value for deleted prescriptions
5. THE Prescription_System SHALL store sections as an array where each section contains key, title, content, and status fields
6. THE Prescription_System SHALL store section status as one of: Pending, Approved, Rejected
7. WHERE Bedrock_Service payload is available, THE Prescription_System SHALL store bedrock_payload for audit purposes
8. THE Prescription_System SHALL store hospital_id for each prescription
9. THE Prescription_System SHALL store audio and transcription records associated with each prescription

### Requirement 22: Existing Pattern Preservation

**User Story:** As a developer, I want new features to follow existing code patterns, so that the codebase remains consistent and maintainable

#### Acceptance Criteria

1. THE Prescription_System SHALL reuse existing API endpoint patterns for new routes
2. THE Prescription_System SHALL reuse existing authentication middleware for new routes
3. THE Prescription_System SHALL reuse existing state management patterns for new features
4. THE Prescription_System SHALL reuse existing UI component patterns for new pages
5. THE Prescription_System SHALL reuse the existing section edit UI component for rejected section editing
6. THE Prescription_System SHALL follow existing folder structure conventions for new files
7. THE Prescription_System SHALL follow existing naming conventions for new components and functions

### Requirement 23: Minimal Route Additions

**User Story:** As a developer, I want to add only necessary routes, so that the application structure remains simple

#### Acceptance Criteria

1. THE Prescription_System SHALL add route /prescriptions for the prescriptions list page
2. THE Prescription_System SHALL add route /prescriptions/:id for the single prescription view page
3. THE Prescription_System SHALL add route /thank-you for the post-finalization confirmation page
4. THE Prescription_System SHALL add route /logs for the CloudWatch logs viewer accessible to Developer_Admin only
5. THE Prescription_System SHALL add backend endpoint /prescriptions/:id/pdf for PDF generation
