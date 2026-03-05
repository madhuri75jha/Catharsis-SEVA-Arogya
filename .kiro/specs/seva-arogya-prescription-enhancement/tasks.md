# Implementation Plan: SEVA Arogya Prescription Enhancement

## Overview

This implementation plan breaks down the prescription enhancement feature into discrete coding tasks. The feature adds comprehensive workflow management, AI-powered content generation, section-by-section approval, role-based access control, audit logging, PDF generation, and soft delete capabilities to the existing SEVA Arogya prescription management application.

The implementation follows an incremental approach where each task builds on previous work, with checkpoints to ensure stability before proceeding. All tasks reference specific requirements for traceability.

## Tasks

- [x] 1. Database schema setup and migrations
  - [x] 1.1 Create database migration script for prescription state management
    - Add state, finalized_at, finalized_by, deleted_at, deleted_by, pre_deleted_state columns to prescriptions table
    - Add state constraint check for valid values (Draft, InProgress, Finalized, Deleted)
    - Add indexes for state, deleted_at, hospital_id, consultation_id
    - Set default state to 'Draft' for new prescriptions
    - _Requirements: 1.1, 1.2, 1.5, 1.7, 21.1, 21.3, 21.4_

  - [x] 1.2 Create database migration for prescription sections and metadata
    - Add sections JSONB column with default empty array
    - Add bedrock_payload JSONB column for audit storage
    - Add created_by_doctor_id, consultation_id, hospital_id columns
    - Add updated_at timestamp column
    - _Requirements: 2.2, 21.2, 21.5, 21.7, 21.8_

  - [x] 1.3 Create hospitals table and seed data
    - Create hospitals table with hospital_id, name, address, phone, email, registration_number, website, logo_url
    - Add timestamps (created_at, updated_at)
    - Create seed script for initial hospital data
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7_

  - [x] 1.4 Create doctors table and associations
    - Create doctors table with doctor_id, hospital_id, name, specialty, signature_url, availability
    - Add foreign key constraint to hospitals table
    - Create index on hospital_id
    - _Requirements: 15.2, 15.3, 15.4_

  - [x] 1.5 Create user_roles table for RBAC
    - Create user_roles table with user_id, role, hospital_id
    - Add role constraint check (Doctor, HospitalAdmin, DeveloperAdmin)
    - Create indexes on hospital_id and role
    - _Requirements: 8.1, 8.2, 8.3, 20.6, 20.7_

  - [ ]* 1.6 Write property test for database schema constraints
    - **Property 1: Prescription State Validity**
    - **Validates: Requirements 1.1, 21.1**


- [x] 2. Core backend services implementation
  - [x] 2.1 Implement PrescriptionService class with state management
    - Create services/prescription_service.py
    - Implement create_prescription() method with Draft state initialization
    - Implement transition_to_in_progress() with Bedrock content loading
    - Implement state transition validation logic
    - Implement can_finalize() method checking all required sections approved
    - _Requirements: 1.2, 1.3, 1.4, 2.1, 2.3, 2.4, 3.6_

  - [ ]* 2.2 Write property tests for prescription state transitions
    - **Property 2: Initial State is Draft**
    - **Property 3: Draft to InProgress Transition**
    - **Property 4: Finalization Requires All Approvals**
    - **Validates: Requirements 1.2, 1.3, 1.4, 3.6**

  - [x] 2.3 Implement section approval workflow methods
    - Implement approve_section() method setting status to Approved
    - Implement reject_section() method setting status to Rejected
    - Implement update_section_content() method resetting status to Pending
    - Implement finalize_prescription() with metadata recording
    - _Requirements: 1.5, 3.2, 3.3, 3.4, 3.7_

  - [ ]* 2.4 Write property tests for section approval workflow
    - **Property 11: Section Status Validity**
    - **Property 12: Section Approval Transition**
    - **Property 13: Section Rejection Transition**
    - **Property 14: Section Edit Resets Status**
    - **Property 15: Finalization Blocked by Pending Sections**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.7, 21.6**

  - [x] 2.5 Implement soft delete and restore methods
    - Implement soft_delete() method with metadata preservation
    - Implement restore_prescription() method with state restoration
    - Add validation for 30-day restore window
    - _Requirements: 1.7, 10.2, 10.3, 10.4, 10.5, 10.6_

  - [ ]* 2.6 Write property tests for soft delete and restore
    - **Property 7: Soft Delete Preserves Metadata**
    - **Property 16: Soft Delete Retains Record**
    - **Property 19: Restore Clears Deletion Metadata**
    - **Validates: Requirements 1.7, 10.2, 10.3, 10.6, 21.4**

  - [x] 2.7 Implement RBACService class for role-based access control
    - Create services/rbac_service.py
    - Implement get_user_role() fetching from user_roles table
    - Implement get_user_hospital() method
    - Implement can_view_prescription(), can_edit_prescription(), can_delete_prescription(), can_restore_prescription()
    - Implement filter_prescriptions_by_role() with SQL WHERE clause generation
    - Implement get_sidebar_menu_items() returning role-specific menu structure
    - _Requirements: 8.1, 8.2, 8.3, 14.2, 14.3, 14.4, 20.3, 20.4, 20.5, 20.6, 20.7_

  - [ ]* 2.8 Write property tests for RBAC filtering
    - **Property 37: Doctor Role Sees Own Prescriptions Only**
    - **Property 38: Hospital Admin Sees Hospital Prescriptions**
    - **Property 39: Developer Admin Sees All Prescriptions**
    - **Validates: Requirements 8.1, 8.2, 8.3, 20.6, 20.7**

  - [x] 2.9 Implement Bedrock integration for section population
    - Extend aws_services/bedrock_client.py with prescription extraction
    - Implement map_bedrock_to_sections() function
    - Implement format_medications() helper for list formatting
    - Define SECTION_DEFINITIONS with keys, titles, required flags, and order
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ]* 2.10 Write property tests for Bedrock content mapping
    - **Property 8: Bedrock Content Mapping**
    - **Property 9: Bedrock Payload Preservation**
    - **Property 10: Initial Section Status**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 21.7**

- [ ] 3. Checkpoint - Ensure core services tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [x] 4. PDF generation service implementation
  - [x] 4.1 Create PDFGenerator class with ReportLab
    - Create services/pdf_generator.py
    - Implement generate_pdf() method with document structure
    - Implement _render_header() with hospital branding
    - Implement _render_metadata() with prescription details
    - Implement _render_footer() with doctor signature
    - _Requirements: 11.2, 11.3, 13.1, 13.2, 13.3_

  - [x] 4.2 Implement dynamic section rendering
    - Implement _render_section() method iterating through sections array
    - Implement section ordering by order field
    - Implement conditional rendering (only existing sections)
    - Implement _format_list_as_table() for medications
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [ ]* 4.3 Write property tests for PDF generation
    - **Property 23: PDF Generation Produces Valid PDF**
    - **Property 25: PDF Sections Rendered in Order**
    - **Property 26: PDF Renders Only Existing Sections**
    - **Property 27: PDF Section Completeness**
    - **Property 28: PDF Dynamic Section Support**
    - **Property 29: PDF Layout Adapts to Section Count**
    - **Validates: Requirements 11.3, 11.4, 12.1, 12.2, 12.3, 12.4, 12.5**

  - [x] 4.4 Implement S3 upload and signed URL generation
    - Implement upload_to_s3() method with retry logic
    - Implement get_signed_url() with expiration parameter
    - Add error handling for S3 upload failures
    - _Requirements: 11.4, 11.5_

  - [ ]* 4.5 Write property tests for PDF hospital information
    - **Property 30: PDF Hospital Logo Inclusion**
    - **Property 31: PDF Hospital Name Inclusion**
    - **Property 32: PDF Hospital Address Inclusion**
    - **Property 33: PDF Conditional Hospital Fields**
    - **Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7**

- [-] 5. Cleanup scheduler service implementation
  - [x] 5.1 Create CleanupScheduler class with APScheduler
    - Create services/cleanup_scheduler.py
    - Implement run_cleanup() method with daily schedule
    - Implement find_expired_prescriptions() querying deleted_at > 30 days
    - Implement permanently_delete_prescription() removing database records
    - Implement delete_s3_objects() removing audio, transcription, and PDF files
    - Add logging for cleanup operations
    - _Requirements: 10.7, 10.8, 10.9, 10.10_

  - [ ]* 5.2 Write property tests for cleanup scheduler
    - **Property 20: Cleanup Identifies Expired Prescriptions**
    - **Property 21: Permanent Deletion Removes Record**
    - **Property 22: Cascading S3 Deletion**
    - **Validates: Requirements 10.8, 10.9, 10.10**

  - [x] 5.3 Initialize cleanup scheduler in app.py
    - Import CleanupScheduler in app.py
    - Initialize with database_manager and storage_manager
    - Call start() method to begin scheduling
    - Add environment variable CLEANUP_SCHEDULE_ENABLED
    - _Requirements: 10.7_

- [ ] 6. Checkpoint - Ensure PDF and cleanup services tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [x] 7. CloudWatch logs service implementation
  - [x] 7.1 Create CloudWatchService class
    - Create services/cloudwatch_service.py
    - Implement __init__() with log_group_name and region from environment
    - Implement query_logs() with date range and filter pattern parameters
    - Implement get_log_events() with pagination support
    - Implement format_log_entry() for UI display
    - Add AWS credentials configuration from environment variables
    - _Requirements: 17.4, 17.5, 17.7, 17.8, 18.1, 18.2, 18.3, 18.4_

  - [ ]* 7.2 Write property tests for CloudWatch service
    - **Property 46: CloudWatch Logs Date Range Filter**
    - **Property 47: CloudWatch Logs Text Filter**
    - **Property 49: CloudWatch Calls Backend Only**
    - **Validates: Requirements 17.4, 17.5, 18.4**

- [-] 8. API endpoints for prescription management
  - [x] 8.1 Implement GET /api/v1/prescriptions endpoint
    - Add route with login_required decorator
    - Implement query parameter parsing (search, doctor_id, start_date, end_date, state, limit, offset)
    - Implement role-based filtering using RBACService
    - Implement search functionality matching patient name or prescription ID
    - Implement date range filtering on created_at
    - Return prescriptions list with section_statuses summary
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 8.1, 8.2, 8.3_

  - [ ]* 8.2 Write property tests for prescriptions list filtering
    - **Property 34: Search Filter Matches Query**
    - **Property 35: Doctor Filter Scopes Results**
    - **Property 36: Date Range Filter Scopes Results**
    - **Validates: Requirements 6.5, 6.6, 6.7**

  - [x] 8.3 Implement GET /api/v1/prescriptions/:id endpoint
    - Add route with login_required decorator
    - Fetch prescription with full details including sections and audio files
    - Implement permission checks using RBACService
    - Return prescription with permissions object (can_edit, can_delete, can_restore, can_download_pdf)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 20.1, 20.2_

  - [x] 8.4 Implement POST /api/v1/prescriptions endpoint
    - Add route with login_required decorator
    - Parse request body (consultation_id, patient_name, hospital_id)
    - Call PrescriptionService.create_prescription() with Draft state
    - Return prescription_id and state
    - _Requirements: 1.2, 21.2, 21.8_

  - [x] 8.5 Implement POST /api/v1/prescriptions/:id/transition-to-in-progress endpoint
    - Add route with login_required decorator
    - Parse bedrock_payload from request body
    - Call PrescriptionService.transition_to_in_progress()
    - Return updated state and sections array
    - _Requirements: 1.3, 2.1, 2.3, 2.4_

  - [x] 8.6 Implement section approval/rejection endpoints
    - Add POST /api/v1/prescriptions/:id/sections/:section_key/approve
    - Add POST /api/v1/prescriptions/:id/sections/:section_key/reject
    - Add PUT /api/v1/prescriptions/:id/sections/:section_key for content updates
    - Implement authorization checks (creator only)
    - Return updated section status and can_finalize flag
    - _Requirements: 3.2, 3.3, 3.4, 3.5_

  - [ ]* 8.7 Write property tests for section workflow endpoints
    - **Property 5: Finalization Sets Metadata**
    - **Property 6: Finalized Prescriptions are Immutable**
    - **Validates: Requirements 1.5, 1.6, 4.3, 20.1, 21.3**

  - [x] 8.8 Implement POST /api/v1/prescriptions/:id/finalize endpoint
    - Add route with login_required decorator
    - Validate all required sections have Approved status
    - Validate user is creator doctor
    - Call PrescriptionService.finalize_prescription()
    - Return success with redirect_url to /thank-you
    - _Requirements: 1.4, 1.5, 1.6, 3.6, 5.1, 20.3_

  - [ ]* 8.9 Write property tests for finalization authorization
    - **Property 42: Finalization Authorization**
    - **Validates: Requirements 20.3**

  - [x] 8.10 Implement DELETE /api/v1/prescriptions/:id endpoint
    - Add route with login_required decorator
    - Validate user is creator doctor or DeveloperAdmin
    - Call PrescriptionService.soft_delete()
    - Return success with restore_deadline (30 days from now)
    - _Requirements: 10.1, 10.2, 10.3, 20.4_

  - [ ]* 8.11 Write property tests for deletion authorization
    - **Property 43: Deletion Authorization**
    - **Property 41: Deleted Prescriptions are Immutable**
    - **Validates: Requirements 20.2, 20.4**

  - [x] 8.12 Implement POST /api/v1/prescriptions/:id/restore endpoint
    - Add route with login_required decorator
    - Validate user is creator doctor or DeveloperAdmin
    - Validate deleted_at is within 30 days
    - Call PrescriptionService.restore_prescription()
    - Return success with restored state
    - _Requirements: 10.4, 10.5, 10.6, 20.5_

  - [ ]* 8.13 Write property tests for restoration authorization
    - **Property 44: Restoration Authorization**
    - **Property 17: Restore Button Visibility for Creator**
    - **Property 18: Restore Button Visibility for Developer Admin**
    - **Property 40: Restore Button Permissions**
    - **Validates: Requirements 9.6, 10.4, 10.5, 20.5**

  - [x] 8.14 Implement POST /api/v1/prescriptions/:id/pdf endpoint
    - Add route with login_required decorator
    - Fetch prescription and hospital data from database
    - Call PDFGenerator.generate_pdf()
    - Upload PDF to S3 and update prescription.s3_key
    - Generate signed URL with 1-hour expiration
    - Return download_url
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [ ]* 8.15 Write property tests for PDF generation endpoint
    - **Property 24: PDF Generation Returns Signed URL**
    - **Validates: Requirements 11.5**

- [ ] 9. Checkpoint - Ensure prescription API endpoints tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [-] 10. API endpoints for hospital and user management
  - [x] 10.1 Implement hospital CRUD endpoints
    - Add GET /api/v1/hospitals (DeveloperAdmin only)
    - Add GET /api/v1/hospitals/:id (HospitalAdmin own hospital or DeveloperAdmin)
    - Add PUT /api/v1/hospitals/:id (HospitalAdmin own hospital or DeveloperAdmin)
    - Implement authorization using @require_role decorator
    - _Requirements: 16.1, 16.2, 16.3_

  - [ ]* 10.2 Write property tests for hospital settings
    - **Property 45: Hospital Settings Update**
    - **Validates: Requirements 16.3**

  - [x] 10.3 Implement doctor management endpoints
    - Add GET /api/v1/hospitals/:id/doctors
    - Add POST /api/v1/hospitals/:id/doctors
    - Add DELETE /api/v1/hospitals/:id/doctors/:doctor_id
    - Implement authorization (HospitalAdmin own hospital or DeveloperAdmin)
    - _Requirements: 16.4, 16.5_

  - [x] 10.4 Implement GET /api/v1/profile endpoint
    - Add route with login_required decorator
    - Fetch user profile from doctors table
    - Return profile with role, hospital, specialty, signature_url, availability
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

  - [x] 10.5 Implement GET /api/v1/logs endpoint
    - Add route with @require_role('DeveloperAdmin') decorator
    - Parse query parameters (start_time, end_time, filter_pattern, search, limit, next_token)
    - Call CloudWatchService.query_logs()
    - Return logs array with pagination token
    - Ensure AWS credentials never exposed in response
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7, 17.8, 17.9_

  - [ ]* 10.6 Write property tests for CloudWatch logs endpoint
    - **Property 48: AWS Credentials Not Exposed**
    - **Validates: Requirements 17.9**

  - [x] 10.7 Implement GET /thank-you route
    - Add route with login_required decorator
    - Render thank_you.html template
    - Pass randomly selected message from THANK_YOU_MESSAGES list
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 11. Frontend - Prescriptions list page
  - [x] 11.1 Create prescriptions list HTML template
    - Create templates/prescriptions_list.html
    - Add search box with debounced input
    - Add filter controls for doctor and date range
    - Add table with columns: Prescription ID, Patient, Doctor, Created Date/Time, State, Section Statuses
    - Add responsive table styling with horizontal scroll on mobile
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.8_

  - [x] 11.2 Implement prescriptions list JavaScript
    - Create static/js/prescriptions_list.js
    - Implement DebouncedSearch class with 300ms delay
    - Implement fetchPrescriptions() calling GET /api/v1/prescriptions
    - Implement renderPrescriptionsTable() with section status icons/pills
    - Implement filter change handlers
    - Implement row click navigation to /prescriptions/:id
    - _Requirements: 6.5, 6.6, 6.7, 6.8_

  - [x] 11.3 Integrate home page with prescriptions list
    - Update home page "View all" button to navigate to /prescriptions
    - Update home page search to navigate to /prescriptions with query parameter
    - Implement query parameter prefill in prescriptions list page
    - _Requirements: 7.1, 7.2, 7.3_

- [ ] 12. Frontend - Single prescription view page
  - [x] 12.1 Create single prescription view HTML template
    - Create templates/prescription_detail.html
    - Add audio playback controls for each audio file
    - Add transcription text display
    - Add read-only prescription sections display
    - Add Download PDF button
    - Add Delete button with confirmation modal
    - Add Restore button (conditional visibility)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [x] 12.2 Implement single prescription view JavaScript
    - Create static/js/prescription_detail.js
    - Implement fetchPrescription() calling GET /api/v1/prescriptions/:id
    - Implement renderPrescriptionDetails() with state-based UI
    - Implement handleDownloadPDF() calling POST /api/v1/prescriptions/:id/pdf
    - Implement handleDelete() with confirmation modal
    - Implement handleRestore() calling POST /api/v1/prescriptions/:id/restore
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 10.1, 10.2_

- [ ] 13. Checkpoint - Ensure prescriptions list and detail pages work
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 14. Frontend - Prescription finalization page
  - [x] 14.1 Create prescription finalization HTML template
    - Create templates/prescription_finalize.html
    - Add sections display with Bedrock-generated content
    - Add per-section approve/reject buttons
    - Add inline editing UI for rejected sections (reuse existing section edit component)
    - Add section status indicators (Pending/Approved/Rejected)
    - Add Finalize button (disabled until all required sections approved)
    - _Requirements: 3.1, 3.2, 3.3, 3.5, 3.6, 3.7, 22.5_

  - [x] 14.2 Implement prescription finalization JavaScript
    - Create static/js/prescription_finalize.js
    - Implement fetchPrescription() with transition to InProgress on page load
    - Implement handleApproveSection() calling POST /api/v1/prescriptions/:id/sections/:key/approve
    - Implement handleRejectSection() calling POST /api/v1/prescriptions/:id/sections/:key/reject
    - Implement handleSaveSection() calling PUT /api/v1/prescriptions/:id/sections/:key
    - Implement updateFinalizeButton() enabling when all required sections approved
    - Implement handleFinalize() calling POST /api/v1/prescriptions/:id/finalize
    - _Requirements: 1.3, 3.2, 3.3, 3.4, 3.6, 3.7_

  - [ ] 14.3 Implement read-only finalized prescription view
    - Update prescription_detail.html to hide controls when state is Finalized
    - Hide section approval controls
    - Hide section edit controls
    - Disable all modification actions
    - Display PDF download button
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 15. Frontend - Thank you page
  - [x] 15.1 Create thank you page HTML template
    - Create templates/thank_you.html
    - Display randomly selected confirmation message
    - Add "Back to Prescriptions" button
    - Style consistently with application theme
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 16. Frontend - Responsive sidebar navigation
  - [x] 16.1 Create sidebar HTML component
    - Create templates/components/sidebar.html
    - Add hamburger menu button for mobile (< 768px)
    - Add drawer overlay for mobile
    - Add sidebar with role-based menu items
    - Add user profile section at bottom
    - Add active route highlighting
    - _Requirements: 14.1, 14.2, 14.3, 14.4_

  - [x] 16.2 Implement sidebar JavaScript
    - Create static/js/sidebar.js
    - Implement mobile drawer open/close animations
    - Implement fetchUserRole() to get role-specific menu items
    - Implement renderMenuItems() based on role
    - Add responsive behavior (drawer < 768px, fixed sidebar ≥ 768px)
    - _Requirements: 14.2, 14.3, 14.4, 14.5, 14.6_

  - [x] 16.3 Implement sidebar CSS
    - Add mobile drawer styles with transform animations
    - Add desktop fixed sidebar styles
    - Add media query for 768px breakpoint
    - Add smooth transition effects
    - _Requirements: 14.5, 14.6_

- [x] 17. Frontend - Transition overlay component
  - [x] 17.1 Create transition overlay HTML component
    - Create templates/components/transition_overlay.html
    - Add overlay with "SEVA Arogya" text in login page font
    - Add animated login icon (medical_services)
    - Style with application theme colors
    - _Requirements: 19.1, 19.2, 19.3, 19.5_

  - [x] 17.2 Implement transition overlay JavaScript
    - Create static/js/transition_overlay.js
    - Implement TransitionOverlay class with show() and hide() methods
    - Implement setupRouteInterception() to intercept navigation
    - Add fade in/out animations (500ms duration)
    - Add icon slide-up animation
    - _Requirements: 19.1, 19.3, 19.4_

  - [x] 17.3 Integrate transition overlay in all pages
    - Include transition_overlay.html in base template
    - Initialize TransitionOverlay on page load
    - Test navigation between all routes
    - _Requirements: 19.1_

- [ ] 18. Frontend - CloudWatch logs viewer page
  - [x] 18.1 Create logs viewer HTML template
    - Create templates/logs_viewer.html
    - Add date range selector with default 24 hours
    - Add text search filter input
    - Add logs table with timestamp and message columns
    - Add pagination controls or "Load More" button
    - Add auto-refresh toggle
    - Add export logs button
    - _Requirements: 17.1, 17.2, 17.3, 17.6, 17.7_

  - [x] 18.2 Implement logs viewer JavaScript
    - Create static/js/logs_viewer.js
    - Implement fetchLogs() calling GET /api/v1/logs
    - Implement renderLogsTable() displaying log entries
    - Implement date range change handler
    - Implement search filter handler
    - Implement pagination with next_token
    - Implement auto-refresh with interval
    - _Requirements: 17.4, 17.5, 17.7_

- [ ] 19. Frontend - Hospital settings page
  - [x] 19.1 Create hospital settings HTML template
    - Create templates/hospital_settings.html
    - Add editable fields for hospital name, address, phone, email, registration_number, website, logo_url
    - Add doctors list table
    - Add controls to add/remove doctor associations
    - Add save button
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_

  - [x] 19.2 Implement hospital settings JavaScript
    - Create static/js/hospital_settings.js
    - Implement fetchHospital() calling GET /api/v1/hospitals/:id
    - Implement handleSaveHospital() calling PUT /api/v1/hospitals/:id
    - Implement fetchDoctors() calling GET /api/v1/hospitals/:id/doctors
    - Implement handleAddDoctor() calling POST /api/v1/hospitals/:id/doctors
    - Implement handleRemoveDoctor() calling DELETE /api/v1/hospitals/:id/doctors/:doctor_id
    - _Requirements: 16.2, 16.3, 16.4, 16.5_

- [ ] 20. Frontend - Profile page
  - [x] 20.1 Create profile page HTML template
    - Create templates/profile.html
    - Display doctor signature image
    - Display doctor name, specialty, availability
    - Display read-only fields (no editing)
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

  - [x] 20.2 Implement profile page JavaScript
    - Create static/js/profile.js
    - Implement fetchProfile() calling GET /api/v1/profile
    - Implement renderProfile() displaying all fields
    - _Requirements: 15.1_

- [ ] 21. Checkpoint - Ensure all frontend pages work correctly
  - Ensure all tests pass, ask the user if questions arise.


- [x] 22. Authentication and authorization middleware
  - [x] 22.1 Implement @require_role decorator
    - Create decorators/auth_decorators.py
    - Implement require_role() decorator checking user role from session
    - Return 403 Forbidden if role not in allowed_roles
    - _Requirements: 17.1, 20.6, 20.7_

  - [x] 22.2 Implement Cognito role synchronization
    - Create sync_user_role_from_cognito() function
    - Fetch custom:role and custom:hospital_id from Cognito attributes
    - Upsert to user_roles table on login
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 22.3 Add permission enforcement to prescription operations
    - Update finalize endpoint to verify creator
    - Update delete endpoint to verify creator
    - Update restore endpoint to verify creator or DeveloperAdmin
    - Update view endpoint to filter by role and hospital
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.6, 20.7_

  - [ ]* 22.4 Write integration tests for authorization
    - Test Doctor can only view own prescriptions
    - Test HospitalAdmin can view hospital prescriptions
    - Test DeveloperAdmin can view all prescriptions
    - Test unauthorized finalization attempts fail
    - Test unauthorized deletion attempts fail
    - Test unauthorized restoration attempts fail
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.6, 20.7_

- [x] 23. Error handling and validation
  - [x] 23.1 Implement state transition validation
    - Create validate_state_transition() function
    - Define valid_transitions dictionary
    - Return error for invalid transitions
    - _Requirements: 1.1, 1.2, 1.3, 1.6, 1.7_

  - [x] 23.2 Implement authorization error handling
    - Create check_prescription_permission() function
    - Implement permission checks for all operations
    - Return 403 Forbidden with descriptive error messages
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5_

  - [x] 23.3 Implement PDF generation error handling
    - Add try-catch in PDF generation endpoint
    - Log errors without failing finalization
    - Return success with pdf_status: 'generation_failed'
    - Allow PDF regeneration on-demand later
    - _Requirements: 11.1, 11.3_

  - [x] 23.4 Implement S3 upload retry logic
    - Create upload_with_retry() function
    - Implement exponential backoff (2^attempt seconds)
    - Set max_retries to 3
    - _Requirements: 11.4_

  - [x] 23.5 Implement database transaction rollback
    - Wrap finalize_prescription in transaction
    - Rollback on any error
    - Log transaction failures
    - _Requirements: 1.5_

  - [x] 23.6 Implement consistent error response format
    - Create error response helper function
    - Return JSON with success: false, error: {code, message, details}
    - Use consistent error codes across all endpoints
    - _Requirements: 22.1, 22.2, 22.3, 22.4, 22.5, 22.6, 22.7_

  - [ ]* 23.7 Write unit tests for error handling
    - Test invalid state transitions
    - Test authorization failures
    - Test PDF generation failures
    - Test S3 upload retries
    - Test database transaction rollbacks
    - _Requirements: 1.6, 11.3, 11.4, 20.1, 20.2, 20.3, 20.4, 20.5_

- [x] 24. Integration and wiring
  - [x] 24.1 Register all API routes in app.py
    - Import all endpoint modules
    - Register prescription management routes
    - Register hospital management routes
    - Register logs viewer route
    - Register profile route
    - Register thank-you route
    - _Requirements: 23.1, 23.2, 23.3, 23.4, 23.5_

  - [x] 24.2 Initialize all services in app.py
    - Initialize PrescriptionService with database_manager
    - Initialize PDFGenerator with storage_manager
    - Initialize RBACService with database_manager
    - Initialize CloudWatchService with environment config
    - Initialize CleanupScheduler and start scheduling
    - _Requirements: 22.1, 22.2, 22.3, 22.4, 22.5, 22.6, 22.7_

  - [x] 24.3 Add environment variables configuration
    - Add CLOUDWATCH_LOG_GROUP_NAME
    - Add AWS_CLOUDWATCH_REGION
    - Add CLEANUP_SCHEDULE_ENABLED
    - Add CLEANUP_RETENTION_DAYS
    - Add PDF_GENERATION_TIMEOUT
    - Add PDF_MAX_FILE_SIZE_MB
    - Add ENABLE_PRESCRIPTION_WORKFLOW
    - Add ENABLE_CLOUDWATCH_LOGS_VIEWER
    - _Requirements: 18.1, 18.2, 18.3_

  - [x] 24.4 Update base template to include sidebar and transition overlay
    - Include sidebar.html in base template
    - Include transition_overlay.html in base template
    - Add sidebar initialization script
    - Add transition overlay initialization script
    - _Requirements: 14.1, 19.1_

  - [x] 24.5 Add route definitions for all new pages
    - Add /prescriptions route
    - Add /prescriptions/:id route
    - Add /prescriptions/:id/finalize route
    - Add /thank-you route
    - Add /logs route
    - Add /hospital-settings route
    - Add /profile route
    - _Requirements: 6.1, 9.1, 17.1, 23.1, 23.2, 23.3, 23.4_

  - [ ]* 24.6 Write integration tests for complete workflows
    - Test complete prescription lifecycle (Draft → InProgress → Finalized)
    - Test section rejection and edit flow
    - Test soft delete and restore flow
    - Test PDF generation flow
    - Test role-based access control across all endpoints
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 3.1, 3.2, 3.3, 3.4, 10.1, 10.2, 10.6, 11.1, 11.6_

- [ ] 25. Checkpoint - Ensure all integration tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 26. Property-based tests for remaining properties
  - [ ]* 26.1 Write property tests for prescription metadata
    - **Property 50: Prescription Has Creator ID**
    - **Property 51: Section Structure Completeness**
    - **Property 52: Prescription Has Hospital ID**
    - **Property 53: Prescription Audio Associations**
    - **Validates: Requirements 21.2, 21.5, 21.8, 21.9**

  - [ ]* 26.2 Write property tests for immutability constraints
    - **Property 6: Finalized Prescriptions are Immutable**
    - **Property 41: Deleted Prescriptions are Immutable**
    - **Validates: Requirements 1.6, 4.3, 20.1, 20.2**

- [x] 27. Database migration execution and data seeding
  - [x] 27.1 Create migration execution script
    - Create scripts/run_migrations.py
    - Execute all migration SQL files in order
    - Add rollback capability for failed migrations
    - Log migration execution status
    - _Requirements: 21.1, 21.2, 21.3, 21.4, 21.5, 21.6, 21.7, 21.8_

  - [x] 27.2 Create seed data script for hospitals
    - Create scripts/seed_hospitals.py
    - Insert sample hospital records
    - Insert sample doctor records
    - Insert sample user_roles records
    - _Requirements: 13.1, 13.2, 13.3, 15.2, 15.3_

  - [x] 27.3 Create migration for existing prescriptions
    - Create scripts/migrate_existing_prescriptions.py
    - Set state to 'Draft' for all existing prescriptions
    - Set created_by_doctor_id from user_id
    - Set hospital_id from user's hospital
    - Initialize sections as empty array
    - _Requirements: 1.2, 21.1, 21.2, 21.5, 21.8_

  - [ ]* 27.4 Write unit tests for migration scripts
    - Test migration execution succeeds
    - Test rollback on failure
    - Test existing prescriptions migrated correctly
    - Test seed data inserted correctly
    - _Requirements: 21.1, 21.2, 21.3, 21.4, 21.5, 21.8_

- [x] 28. Documentation and deployment preparation
  - [x] 28.1 Create API documentation
    - Document all API endpoints with request/response examples
    - Document authentication and authorization requirements
    - Document error response formats
    - Document rate limits and pagination
    - _Requirements: 22.1, 22.2, 22.3, 22.4, 22.5, 22.6, 22.7_

  - [x] 28.2 Create deployment guide
    - Document database migration steps
    - Document environment variables configuration
    - Document AWS services setup (Bedrock, CloudWatch, S3)
    - Document rollout strategy (phased deployment)
    - Document rollback procedures
    - _Requirements: 18.1, 18.2, 18.3, 22.1, 22.2, 22.3, 22.4, 22.5, 22.6, 22.7_

  - [x] 28.3 Create monitoring and alerting configuration
    - Define key metrics to monitor (prescription creation rate, PDF generation success rate, etc.)
    - Configure CloudWatch alarms for critical failures
    - Document alert thresholds and escalation procedures
    - _Requirements: 17.1, 17.8_

  - [x] 28.4 Create user guide for new features
    - Document prescription workflow (Draft → InProgress → Finalized)
    - Document section approval process
    - Document soft delete and restore functionality
    - Document PDF generation
    - Document role-based access control
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 3.1, 3.2, 3.3, 10.1, 10.6, 11.1_

- [x] 29. Final checkpoint - End-to-end testing and validation
  - Run all unit tests, property tests, and integration tests
  - Verify all 53 correctness properties pass
  - Test complete workflows in staging environment
  - Verify backward compatibility with existing prescriptions
  - Verify performance meets targets (< 500ms list, < 5s PDF generation)
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional property-based tests and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation and allow for user feedback
- Property tests validate universal correctness properties across all inputs
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows
- The implementation follows existing Flask patterns and reuses existing components where possible
- All AWS credentials remain server-side and are never exposed to the frontend
- The design supports future extensibility (new sections, new roles) without code changes

