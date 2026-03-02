# Implementation Plan: Recent Consultations Display on Home Page

## Overview

This implementation plan breaks down the recent consultations feature into discrete coding tasks. The feature enables healthcare providers to view their recent consultations on the home page, expand to see more, and navigate to detailed consultation views. The implementation follows the existing Flask + PostgreSQL architecture with client-side JavaScript for dynamic UI updates.

## Tasks

- [x] 1. Create ConsultationService module for data retrieval
  - Create `services/` directory and `services/__init__.py`
  - Create `services/consultation_service.py` with `ConsultationService` class
  - Implement `get_recent_consultations(user_id, db_manager, limit=10)` method
  - Implement SQL query with LEFT JOIN between transcriptions and prescriptions
  - Implement patient name extraction logic from medical_entities JSONB or prescription
  - Implement patient initials generation logic
  - _Requirements: 1.1, 1.5, 4.1, 4.2, 4.3, 7.1, 7.4_

- [ ]* 1.1 Write property test for consultation retrieval limit
  - **Property 1: Consultation Retrieval Limit**
  - **Validates: Requirements 1.1, 1.5**

- [ ]* 1.2 Write property test for user data isolation
  - **Property 11: User Data Isolation**
  - **Validates: Requirements 4.1, 8.2**

- [ ]* 1.3 Write property test for transcription-prescription join logic
  - **Property 12: Transcription-Prescription Join Logic**
  - **Validates: Requirements 4.2**

- [ ]* 1.4 Write property test for transcription without prescription inclusion
  - **Property 13: Transcription Without Prescription Inclusion**
  - **Validates: Requirements 4.3**

- [ ]* 1.5 Write property test for patient initials generation
  - **Property 18: Patient Initials Generation**
  - **Validates: Requirements 7.4**

- [-] 1.6 Write unit tests for ConsultationService
  - Test with 0, 2, 10, and 100 consultations
  - Test patient name extraction from medical_entities
  - Test patient name extraction from prescription
  - Test "Unknown Patient" fallback
  - Test malformed JSONB handling
  - _Requirements: 1.1, 4.3, 7.1, 7.3_

- [-] 2. Implement API endpoint for consultation retrieval
  - Add `/api/consultations` GET route in `app.py`
  - Apply `@login_required` decorator for authentication
  - Extract user_id from session
  - Parse and validate `limit` query parameter (default 10, max 50)
  - Call `ConsultationService.get_recent_consultations()`
  - Return JSON response with consultation list
  - Implement error handling for database failures (log + user-friendly message)
  - Implement error handling for authentication failures (401 status)
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 4.5_

- [ ] 2.1 Write property test for API limit parameter handling
  - **Property 19: API Limit Parameter Handling**
  - **Validates: Requirements 8.3**

- [ ] 2.2 Write property test for API response format
  - **Property 20: API Response Format**
  - **Validates: Requirements 8.4**

- [ ] 2.3 Write property test for API success status code
  - **Property 21: API Success Status Code**
  - **Validates: Requirements 8.5**

- [ ] 2.4 Write property test for API authentication failure status code
  - **Property 22: API Authentication Failure Status Code**
  - **Validates: Requirements 8.6**

- [ ] 2.5 Write property test for database error handling
  - **Property 14: Database Error Handling**
  - **Validates: Requirements 4.5, 8.7**

- [ ] 2.6 Write unit tests for API endpoint
  - Test successful request with valid authentication
  - Test request without authentication (401)
  - Test with invalid limit parameter (graceful degradation)
  - Test with empty consultation list
  - Test database connection failure (500)
  - _Requirements: 8.1, 8.2, 8.5, 8.6, 4.5_

- [x] 3. Checkpoint - Ensure backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [-] 4. Create frontend JavaScript module for consultation display
  - Create `static/js/home.js`
  - Implement `fetchConsultations(limit)` async function to call `/api/consultations`
  - Implement `renderConsultations(consultations, showAll)` function to render cards
  - Implement `formatRelativeTime(isoTimestamp)` function for timestamp formatting
  - Implement `getStatusBadge(status)` function for status indicator HTML
  - Implement `handleViewAllClick()` function for expand/collapse logic
  - Implement `handleConsultationClick(consultationId)` function for navigation
  - Add event listeners for page load, "View All" button, and consultation cards
  - _Requirements: 1.2, 1.3, 2.1, 2.3, 3.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4_

- [ ]* 4.1 Write property test for initial display count
  - **Property 2: Initial Display Count**
  - **Validates: Requirements 1.2**

- [ ]* 4.2 Write property test for consultation card information completeness
  - **Property 3: Consultation Card Information Completeness**
  - **Validates: Requirements 1.3**

- [ ] 4.3 Write property test for view all expansion
  - **Property 4: View All Expansion**
  - **Validates: Requirements 2.1**

- [ ]* 4.4 Write property test for expand-collapse round trip
  - **Property 5: Expand-Collapse Round Trip**
  - **Validates: Requirements 2.3**

- [ ]* 4.5 Write property test for consultation navigation
  - **Property 6: Consultation Navigation**
  - **Validates: Requirements 3.1**

- [ ]* 4.6 Write property test for status indicator mapping
  - **Property 15: Status Indicator Mapping**
  - **Validates: Requirements 5.2, 5.3, 5.4**

- [ ]* 4.7 Write property test for timestamp formatting rules
  - **Property 16: Timestamp Formatting Rules**
  - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

- [ ]* 4.8 Write unit tests for frontend JavaScript functions
  - Test formatRelativeTime with various timestamps
  - Test getStatusBadge with all status values
  - Test renderConsultations with 0, 2, and 10 consultations
  - Test handleViewAllClick expand/collapse behavior
  - _Requirements: 1.2, 1.4, 2.1, 2.3, 5.2, 5.3, 5.4, 6.2, 6.3, 6.4_

- [x] 5. Update home.html template for dynamic consultation display
  - Update "Recent Consultations" section to have `id="consultations-container"`
  - Update "View All" button to have `id="view-all-btn"` and onclick handler
  - Remove hardcoded consultation cards (will be rendered by JavaScript)
  - Add empty state message container with `id="empty-state"` (hidden by default)
  - Add loading state indicator
  - Include `home.js` script in `{% block extra_js %}`
  - _Requirements: 1.2, 1.3, 1.4, 2.1_

- [x] 6. Create consultation detail view route and template
  - Add `/consultation/<consultation_id>` GET route in `app.py`
  - Apply `@login_required` decorator
  - Query transcription by transcription_id
  - Query associated prescription (if exists)
  - Render `consultation_detail.html` template with data
  - Handle missing transcription (404 error)
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 7. Create consultation_detail.html template
  - Create `templates/consultation_detail.html` extending `base.html`
  - Add header section with patient name, date, and status badge
  - Add transcript section with full transcript text (scrollable)
  - Add medical entities section grouped by category (if available)
  - Add prescription section with medications (if available)
  - Add back button to navigate to `/home`
  - Handle missing data gracefully ("No transcript available", "Unknown Patient")
  - _Requirements: 3.2, 3.3, 3.4, 3.5, 7.2, 7.3_

- [ ]* 7.1 Write property test for detail view transcript display
  - **Property 7: Detail View Transcript Display**
  - **Validates: Requirements 3.2**

- [ ]* 7.2 Write property test for detail view medical entities display
  - **Property 8: Detail View Medical Entities Display**
  - **Validates: Requirements 3.3**

- [ ]* 7.3 Write property test for detail view prescription display
  - **Property 9: Detail View Prescription Display**
  - **Validates: Requirements 3.4**

- [ ]* 7.4 Write property test for detail view navigation round trip
  - **Property 10: Detail View Navigation Round Trip**
  - **Validates: Requirements 3.5**

- [ ]* 7.5 Write property test for incomplete data display
  - **Property 17: Incomplete Data Display**
  - **Validates: Requirements 7.3**

- [ ]* 7.6 Write unit tests for consultation detail view
  - Test with complete consultation data
  - Test with missing patient name
  - Test with missing transcript text
  - Test with empty medical_entities
  - Test with no prescription
  - Test with invalid consultation_id (404)
  - _Requirements: 3.2, 3.3, 3.4, 7.2, 7.3_

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Integration and final wiring
  - Verify API endpoint is accessible from frontend
  - Verify consultation cards render correctly on home page
  - Verify "View All" expand/collapse functionality
  - Verify navigation to consultation detail view
  - Verify back button returns to home page
  - Test with empty consultation list (displays "No recent consultations found")
  - Test error handling for API failures
  - _Requirements: 1.1, 1.2, 1.4, 2.1, 2.3, 3.1, 3.5, 4.5_

- [ ]* 9.1 Write integration tests for complete consultation flow
  - Test end-to-end flow: home page load → fetch consultations → render cards → click card → detail view → back button
  - Test expand/collapse flow
  - Test empty state display
  - Test error state display
  - _Requirements: 1.1, 1.2, 2.1, 3.1, 3.5_

- [x] 10. Final checkpoint - Verify feature completeness
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties across randomized inputs
- Unit tests validate specific examples and edge cases
- The implementation follows existing Flask patterns and PostgreSQL schema
- Frontend uses vanilla JavaScript for simplicity and consistency with existing code
- All consultation data is scoped to authenticated user (no cross-user data leakage)
