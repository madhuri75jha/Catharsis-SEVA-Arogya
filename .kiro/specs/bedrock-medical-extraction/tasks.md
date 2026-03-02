# Implementation Plan: Bedrock Medical Extraction

## Overview

This implementation plan breaks down the Bedrock Medical Extraction feature into discrete coding tasks. The system integrates AWS Comprehend Medical for entity extraction with AWS Bedrock's function-calling capabilities to automatically populate prescription forms from medical transcripts. The implementation follows a bottom-up approach: core services first, then orchestration, then Flask API layer, and finally frontend integration with Jinja2 templates and vanilla JavaScript.

## Tasks

- [x] 1. Set up project structure and core data models
  - Create Python backend directory structure in aws_services/ for new Bedrock client
  - Define Pydantic data models for all domain objects (MedicalEntity, FieldDefinition, SectionDefinition, HospitalConfiguration, PrescriptionData, FunctionCallResponse, ValidationResult, error models) in models/
  - Set up testing framework (pytest + Hypothesis for backend property tests)
  - Use existing logger utility (utils/logger.py) for structured logging
  - _Requirements: 8.6, 9.9_

- [x] 2. Enhance existing AWS Comprehend Medical client
  - [x] 2.1 Extend ComprehendManager class in aws_services/comprehend_manager.py
    - Enhance extract_entities method to return structured MedicalEntity objects (already returns dicts with confidence)
    - Add entity categorization by detailed type (medication, dosage, frequency, duration, condition, procedure, anatomy) - currently only categorizes by broad category
    - Ensure confidence scores are preserved (already implemented)
    - Follow existing BaseAWSClient pattern for error handling and logging
    - _Requirements: 1.1, 1.2, 1.4_
  
  - [ ]* 2.2 Write property test for Comprehend Medical client
    - **Property 1: Comprehend Medical Integration** - Verify all transcripts are sent to Comprehend Medical
    - **Property 2: Entity Categorization** - Verify entity categorization for all response types
    - **Property 4: Confidence Score Preservation** - Verify confidence scores are preserved
    - **Validates: Requirements 1.1, 1.2, 1.4**
  
  - [x] 2.3 Enhance error handling and retry logic in ComprehendManager
    - Error handling already exists in BaseAWSClient pattern
    - Add exponential backoff retry (3 attempts: 1s, 2s, 4s delays) for rate limits
    - Ensure error logging includes request IDs (already implemented in BaseAWSClient)
    - _Requirements: 1.3, 4.1, 4.4, 4.5_
  
  - [ ]* 2.4 Write property test for error handling
    - **Property 3: Entity Extraction Error Handling** - Verify error handling for all error types
    - **Property 14: Exponential Backoff Retry** - Verify retry logic for rate limits
    - **Validates: Requirements 1.3, 4.4**

- [x] 3. Implement configuration management system
  - [x] 3.1 Extend ConfigManager class in aws_services/config_manager.py
    - Add load_hospital_configuration method to read JSON files from /config/hospitals/
    - Add get_default_hospital_configuration method for fallback
    - Add validate_hospital_configuration method using Pydantic validation
    - Add in-memory caching for loaded hospital configurations
    - Follow existing ConfigManager patterns (already handles AWS Secrets Manager)
    - _Requirements: 9.1, 9.2, 9.3, 9.7_
  
  - [ ]* 3.2 Write property tests for configuration management
    - **Property 30: Hospital Configuration Storage and Retrieval** - Verify storage/retrieval round-trip
    - **Property 31: Configuration JSON Structure** - Verify JSON structure for all configs
    - **Property 34: Configuration Validation** - Verify validation rejects all invalid configs
    - **Property 35: Configuration Serialization Round-Trip** - Verify serialization round-trip
    - **Property 36: Field Type Support** - Verify all field types are supported
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.8, 9.9, 9.10**
  
  - [x] 3.3 Implement configuration hot-reload mechanism
    - Add file watcher or cache invalidation for configuration updates
    - Ensure new configurations are applied without restart
    - _Requirements: 9.5_
  
  - [ ]* 3.4 Write property test for hot-reload
    - **Property 32: Configuration Hot-Reload** - Verify hot-reload behavior
    - **Validates: Requirements 9.5**
  
  - [x] 3.5 Create sample hospital configurations
    - Create default.json with standard prescription fields
    - Create sample hospital configurations (hosp_12345.json as per requirements)
    - Include all field types (text, number, dropdown, multiline)
    - _Requirements: 9.2, 9.7, 9.10_

- [x] 4. Implement AWS Bedrock client
  - [x] 4.1 Create BedrockClient class in aws_services/bedrock_client.py following BaseAWSClient pattern
    - Implement generate_prescription_data method (sync, not async - Flask uses eventlet)
    - Implement _construct_prompt method to build prompts with transcript and entities
    - Implement _build_function_schema method to convert FieldDefinition to Bedrock function schema
    - Include field descriptions from hospital config in function schema
    - Load model configuration from ConfigManager (environment variables)
    - Follow existing aws_services patterns (BaseAWSClient, error handling, logging)
    - _Requirements: 2.1, 2.2, 2.3, 6.1, 6.4, 9.4, 9.11_
  
  - [ ]* 4.2 Write property tests for Bedrock client
    - **Property 5: Prompt Construction** - Verify prompts contain transcript and entities
    - **Property 6: Dynamic Function Definition Generation** - Verify function definitions match all config variations
    - **Property 7: Bedrock Function Calling Invocation** - Verify function calling is always requested
    - **Property 20: Model Configuration Usage** - Verify model configuration usage
    - **Validates: Requirements 2.1, 2.2, 2.3, 6.1, 6.4, 9.4, 9.11**
  
  - [x] 4.3 Implement model validation at startup
    - Validate configured model supports function calling capability
    - Fail fast if model doesn't support function calling
    - _Requirements: 6.2, 6.3_
  
  - [ ]* 4.4 Write property test for model validation
    - **Property 21: Function Calling Capability Validation** - Verify function calling capability validation
    - **Validates: Requirements 6.2**
  
  - [x] 4.5 Implement error handling for Bedrock API
    - Add exception classes (BedrockUnavailableError, BedrockRateLimitError) in utils/error_handler.py
    - Implement retry logic with exponential backoff following BaseAWSClient patterns
    - Use existing error logging with request IDs from BaseAWSClient
    - _Requirements: 4.2, 4.4, 4.5_

- [x] 5. Implement validation and normalization layer
  - [x] 5.1 Create ValidationLayer class in aws_services/validation_layer.py
    - Implement validate_function_call method to check structure against expected fields
    - Implement normalize_dosage method for standard unit conversion (mg, ml, tablets)
    - Add required field validation (medication_name, dosage)
    - Add optional field extraction (frequency, duration, special_instructions)
    - Handle partial results for invalid responses
    - Follow existing aws_services patterns for logging
    - _Requirements: 2.4, 2.5, 8.1, 8.2, 8.3, 8.5_
  
  - [ ]* 5.2 Write property tests for validation layer
    - **Property 8: Function Call Validation** - Verify validation for all function call structures
    - **Property 9: Partial Result Handling** - Verify partial results for all invalid responses
    - **Property 25: Function Call JSON Parsing** - Verify JSON parsing for valid responses
    - **Property 26: Required Field Validation** - Verify required field validation
    - **Property 27: Optional Field Extraction** - Verify optional field extraction
    - **Property 28: Dosage Normalization** - Verify dosage normalization for all formats
    - **Validates: Requirements 2.4, 2.5, 8.1, 8.2, 8.3, 8.5**
  
  - [ ]* 5.3 Write unit tests for edge cases
    - Test empty function call responses
    - Test malformed JSON handling
    - Test missing required fields
    - Test various dosage format conversions
    - _Requirements: 8.4_

- [x] 6. Implement extraction pipeline orchestration
  - [x] 6.1 Create ExtractionPipeline class in aws_services/extraction_pipeline.py
    - Implement extract_prescription_data method as main orchestrator (sync, not async)
    - Wire together: ComprehendManager → ConfigManager → BedrockClient → ValidationLayer
    - Implement data flow: transcript → entities → config → function definitions → AI processing → validation → PrescriptionData
    - Add processing time tracking
    - Follow existing aws_services patterns
    - _Requirements: 3.1, 3.2_
  
  - [ ]* 6.2 Write property tests for pipeline
    - **Property 10: Prescription Data Formatting** - Verify data formatting for all valid inputs
    - **Property 29: Prescription Data Serialization Round-Trip** - Verify serialization round-trip
    - **Validates: Requirements 3.1, 3.2, 8.6**
  
  - [x] 6.3 Implement security and privacy controls
    - Ensure TLS 1.2+ for all AWS API calls (already handled by boto3)
    - Implement log sanitization in utils/logger.py to exclude transcript content and PHI
    - Sanitize error messages to exclude patient-identifiable information in utils/error_handler.py
    - Add audit logging with timestamps and user IDs (no medical content) using existing logger
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [ ]* 6.4 Write property tests for security controls
    - **Property 17: Transcript Content Exclusion from Logs** - Verify transcript exclusion from logs
    - **Property 18: Error Message Sanitization** - Verify error message sanitization
    - **Property 19: Audit Log Format** - Verify audit log format
    - **Validates: Requirements 5.3, 5.4, 5.5**
  
  - [x] 6.5 Implement error resilience
    - Add circuit breaker pattern for AWS service failures
    - Ensure pipeline doesn't crash on any error
    - Return appropriate error responses for all failure modes
    - _Requirements: 4.6_
  
  - [ ]* 6.6 Write property test for error resilience
    - **Property 15: Error Logging with Request IDs** - Verify error logging with request IDs
    - **Property 16: Error Resilience** - Verify error resilience
    - **Validates: Requirements 4.5, 4.6**

- [x] 7. Checkpoint - Backend core services complete
  - Ensure all backend unit tests pass
  - Ensure all backend property tests pass (100+ iterations each)
  - Verify AWS SDK integration with mocked services
  - Ask the user if questions arise

- [x] 8. Implement Flask API endpoints
  - [x] 8.1 Add extraction endpoints to app.py
    - Implement POST /api/v1/extract endpoint (accepts transcript, hospital_id, optional request_id)
    - Implement GET /api/v1/config/{hospital_id} endpoint
    - Add request validation using Pydantic models
    - Add response formatting (success/error structures)
    - Use existing @login_required decorator for authentication
    - Follow existing Flask route patterns in app.py
    - _Requirements: 3.1, 3.2, 3.6_
  
  - [x] 8.2 Implement rate limiting and request ID handling
    - Add rate limiting middleware to prevent abuse (use Flask-Limiter or similar)
    - Add request ID generation for idempotency tracking
    - Use existing session management for user authentication
    - _Requirements: 4.3, 5.2_
  
  - [x] 8.3 Add API error handling
    - Map internal exceptions to HTTP status codes using existing error_handler.py patterns
    - Return standardized error responses
    - Add correlation IDs for request tracing
    - _Requirements: 4.1, 4.2, 4.3_
  
  - [ ]* 8.4 Write integration tests for API endpoints
    - Test complete extraction flow from API to response
    - Test error scenarios (invalid input, service failures)
    - Test authentication and authorization
    - Mock AWS services to avoid external dependencies
    - _Requirements: 1.5, 2.6_

- [x] 9. Implement IAM roles and infrastructure configuration
  - [x] 9.1 Create IAM policy documents
    - Define least-privilege IAM policy for Comprehend Medical access
    - Define least-privilege IAM policy for Bedrock access
    - Document required permissions in seva-arogya-infra/ Terraform code
    - _Requirements: 5.2_
  
  - [x] 9.2 Set up environment configuration
    - Add Bedrock configuration to .env.example (model ID, region)
    - Document Bedrock model configuration in README
    - Add configuration validation at startup in ConfigManager
    - _Requirements: 6.1, 6.4, 6.5_
  
  - [x] 9.3 Create deployment documentation
    - Document AWS service setup requirements in README
    - Document environment variable configuration
    - Document hospital configuration file setup in /config/hospitals/
    - _Requirements: 9.1, 9.2, 9.3_

- [x] 10. Implement frontend prescription form with vanilla JavaScript
  - [x] 10.1 Create prescription form template in templates/bedrock_prescription.html
    - Extend base.html template (Tailwind CSS already available)
    - Implement dynamic form rendering based on HospitalConfiguration using vanilla JavaScript
    - Render fields in sections with correct display order
    - Support all field types (text, number, dropdown, multiline)
    - Handle repeatable sections (medications) with add/remove buttons
    - Follow existing template patterns from templates/final_prescription.html
    - _Requirements: 9.6, 9.10_
  
  - [ ]* 10.2 Write property test for dynamic rendering
    - **Property 33: Dynamic Form Rendering** - Verify dynamic rendering for all configs
    - **Validates: Requirements 9.6**
  
  - [x] 10.3 Implement form field population with vanilla JavaScript
    - Add JavaScript in static/js/bedrock_prescription.js for state management
    - Populate fields from API response
    - Apply visual indicators for auto-filled fields (CSS class or data attribute)
    - Ensure all fields remain editable after auto-fill
    - Use existing Tailwind CSS classes for styling
    - _Requirements: 3.3, 3.4, 3.5_
  
  - [ ]* 10.4 Write property tests for field population
    - **Property 11: Form Field Population** - Verify field population for all prescription data
    - **Property 12: Auto-Fill Visual Indication** - Verify auto-fill indicators for all fields
    - **Property 13: Field Editability** - Verify editability for all auto-filled fields
    - **Validates: Requirements 3.3, 3.4, 3.5**
  
  - [x] 10.5 Implement confidence indicators with vanilla JavaScript
    - Display confidence scores for each auto-filled field
    - Apply visual cues based on confidence thresholds (high >0.8, medium 0.5-0.8, low <0.5)
    - Highlight low confidence fields for review
    - Add tooltip or modal to show original transcript context (source_text)
    - Use Tailwind CSS for styling confidence indicators
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [ ]* 10.6 Write property tests for confidence indicators
    - **Property 22: Confidence Level Visual Classification** - Verify confidence visual classification
    - **Property 23: Low Confidence Field Highlighting** - Verify low confidence highlighting
    - **Property 24: Source Context Availability** - Verify source context availability
    - **Validates: Requirements 7.2, 7.3, 7.4, 7.5**
  
  - [ ]* 10.7 Write unit tests for form component
    - Test form rendering with various configurations
    - Test user interactions (editing fields, viewing context)
    - Test empty state when no data is extracted
    - Use simple JavaScript unit testing (no fast-check)
    - _Requirements: 3.6_

- [x] 11. Implement frontend transcript submission component
  - [x] 11.1 Create transcript submission template or enhance existing transcription.html
    - Add text area for transcript input with character count (max 10,000 characters)
    - Add submit button with loading state
    - Add hospital selection dropdown
    - Use existing Tailwind CSS styling patterns
    - Follow existing template structure from templates/transcription.html
    - _Requirements: 1.1_
  
  - [x] 11.2 Implement API integration with vanilla JavaScript
    - Create JavaScript module in static/js/bedrock_extraction.js for API calls
    - Implement POST /api/v1/extract API call
    - Handle loading, success, and error states
    - Display error messages to user
    - Navigate to prescription form on success with extracted data
    - _Requirements: 3.1, 4.1, 4.2_
  
  - [ ]* 11.3 Write unit tests for transcript component
    - Test transcript submission
    - Test loading states
    - Test error display
    - Test character limit validation
    - Use simple JavaScript unit testing

- [x] 12. Implement frontend configuration loading
  - [x] 12.1 Create configuration loading JavaScript module
    - Implement API client in static/js/bedrock_extraction.js for GET /api/v1/config/{hospital_id}
    - Cache configuration in browser sessionStorage or memory
    - Handle configuration loading errors
    - _Requirements: 9.3, 9.6_
  
  - [x] 12.2 Wire configuration to prescription form
    - Pass configuration to form rendering logic for dynamic field generation
    - Update form when hospital selection changes
    - _Requirements: 9.6_

- [x] 13. Checkpoint - Frontend components complete
  - Ensure all frontend unit tests pass
  - Ensure all frontend property tests pass (100+ iterations each)
  - Test form rendering with various hospital configurations
  - Test complete user flow: transcript submission → extraction → form population
  - Ask the user if questions arise

- [x] 14. Integration and end-to-end wiring
  - [x] 14.1 Wire frontend to Flask backend API
    - Configure API base URL in JavaScript
    - CORS already configured in app.py
    - Test complete flow from frontend to backend
    - _Requirements: 3.1, 3.2, 3.3_
  
  - [x] 14.2 Implement error handling UI
    - Display user-friendly error messages for all error codes in JavaScript
    - Show retry option for transient failures
    - Display informational message when no data is extracted
    - _Requirements: 3.6, 4.1, 4.2_
  
  - [ ]* 14.3 Write end-to-end integration tests
    - Test complete extraction flow with real components
    - Test error scenarios end-to-end
    - Test configuration changes and hot-reload
    - Mock AWS services for consistent testing

- [ ] 15. Performance optimization and testing
  - [ ] 15.1 Add performance monitoring
    - Track processing time for each pipeline stage
    - Add metrics for API response times
    - Log performance data for analysis
    - _Requirements: 1.5, 2.6_
  
  - [ ] 15.2 Optimize API response times
    - Ensure entity extraction completes within 5 seconds
    - Ensure Bedrock processing completes within 10 seconds
    - Add timeout configurations
    - _Requirements: 1.5, 2.6_
  
  - [ ]* 15.3 Run load testing
    - Simulate concurrent extraction requests
    - Measure 95th percentile response times
    - Verify rate limit handling under load
    - Test with maximum transcript length (10,000 characters)

- [ ] 16. Security hardening and compliance
  - [ ] 16.1 Verify TLS configuration
    - Ensure all AWS API calls use TLS 1.2+
    - Verify certificate validation
    - _Requirements: 5.1_
  
  - [ ] 16.2 Audit log sanitization
    - Review all log statements for PHI leakage
    - Verify transcript content is never logged
    - Verify error messages are sanitized
    - _Requirements: 5.3, 5.4_
  
  - [ ] 16.3 IAM permissions review
    - Verify least-privilege IAM policies
    - Test with restricted IAM roles
    - Document required permissions
    - _Requirements: 5.2_
  
  - [ ]* 16.4 Run security tests
    - Test for PHI leakage in logs and error messages
    - Test authentication bypass attempts
    - Verify input sanitization

- [ ] 17. Final checkpoint - Complete system validation
  - Run complete test suite (unit + property + integration)
  - Verify all acceptance criteria are met
  - Test with sample hospital configurations
  - Test complete user workflow from transcript to prescription
  - Ensure all tests pass, ask the user if questions arise

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Backend uses Python 3.11+ with Flask, boto3, Pydantic, eventlet, pytest, and Hypothesis
- Frontend uses Jinja2 templates with vanilla JavaScript and Tailwind CSS (CDN)
- AWS services: Comprehend Medical, Bedrock Runtime
- All AWS API calls use TLS 1.2+ and IAM least-privilege roles
- Configuration files stored as JSON in /config/hospitals/ directory
- Checkpoints ensure incremental validation and provide opportunities for user feedback
- Follow existing codebase patterns: BaseAWSClient for AWS services, existing error handling, existing logger utility
