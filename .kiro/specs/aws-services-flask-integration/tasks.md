# Implementation Plan: AWS Services Flask Integration

## Overview

This implementation plan breaks down the AWS services integration into incremental, testable steps. The approach follows a bottom-up strategy: first establishing foundational components (configuration, AWS clients, database), then building service manager classes, and finally integrating everything into Flask routes. Each task builds on previous work, ensuring no orphaned code and enabling early validation of core functionality.

The implementation uses Python with Flask and boto3 SDK, integrating with existing Terraform-provisioned AWS infrastructure including Cognito, Transcribe Medical, Comprehend Medical, Secrets Manager, S3, and RDS PostgreSQL.

## Tasks

- [x] 1. Set up project structure and dependencies
  - Create `aws_services/` directory for AWS service manager modules
  - Create `models/` directory for database models
  - Create `utils/` directory for helper functions
  - Update `requirements.txt` with boto3, psycopg2-binary, python-dotenv, and testing libraries
  - Create `.env.example` file with all required environment variables
  - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [x] 2. Implement configuration management
  - [x] 2.1 Create config manager module (`aws_services/config_manager.py`)
    - Implement `ConfigManager` class to load environment variables
    - Add method to retrieve secrets from AWS Secrets Manager with fallback to environment variables
    - Implement secret caching for application lifetime
    - Add validation for required configuration values at startup
    - Include structured logging for configuration loading (without logging sensitive values)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_
  
  - [ ]* 2.2 Write property test for config manager
    - **Property 1: Secret retrieval consistency**
    - **Validates: Requirements 2.4, 2.5**
    - Test that cached secrets return same value on repeated calls
    - Test fallback behavior when Secrets Manager unavailable

- [x] 3. Implement AWS service client initialization
  - [x] 3.1 Create base AWS client manager (`aws_services/base_client.py`)
    - Implement `BaseAWSClient` class with boto3 client initialization
    - Add region configuration from environment
    - Support IAM role credentials for ECS and local AWS credentials
    - Implement error handling for client initialization failures
    - Add structured logging with service name and initialization status
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 11.1, 11.2, 11.3_
  
  - [ ]* 3.2 Write unit tests for base AWS client
    - Test client initialization with different credential sources
    - Test error handling for initialization failures
    - _Requirements: 1.5_

- [x] 4. Implement database connection and models
  - [x] 4.1 Create database manager (`aws_services/database_manager.py`)
    - Implement `DatabaseManager` class using psycopg2 with connection pooling
    - Configure connection pool with min 2, max 10 connections
    - Implement retry logic with exponential backoff (3 attempts)
    - Add connection health check method
    - Add graceful connection cleanup on shutdown
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_
  
  - [x] 4.2 Create database models (`models/prescription.py`, `models/transcription.py`)
    - Define `Prescription` model with fields: id, user_id, patient_name, medications, s3_key, created_at
    - Define `Transcription` model with fields: id, user_id, audio_s3_key, transcript_text, job_id, status, created_at
    - Add model methods for CRUD operations
    - _Requirements: 9.4_
  
  - [ ]* 4.3 Write property tests for database manager
    - **Property 2: Connection pool consistency**
    - **Validates: Requirements 10.2, 10.3**
    - Test that connection pool maintains configured limits
    - Test retry logic with transient failures

- [ ] 5. Checkpoint - Verify foundational components
  - Ensure configuration manager loads secrets correctly
  - Verify AWS client initialization works with local credentials
  - Test database connection and basic queries
  - Ask the user if questions arise

- [x] 6. Implement storage manager for S3 operations
  - [x] 6.1 Create storage manager (`aws_services/storage_manager.py`)
    - Implement `StorageManager` class extending `BaseAWSClient`
    - Add method to upload audio files with validation (wav, mp3, flac, mp4)
    - Add method to upload PDF files with structured key format
    - Implement server-side encryption (AES256) for all uploads
    - Add method to generate presigned URLs with 1-hour expiration
    - Enforce 16MB file size limit for audio uploads
    - Add error handling and logging for S3 operations
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 9.1, 9.2, 9.3, 9.5, 9.6, 9.7, 15.1, 15.2, 15.3, 15.4, 15.5, 15.6_
  
  - [ ]* 6.2 Write unit tests for storage manager
    - Test file format validation
    - Test file size limit enforcement
    - Test presigned URL generation
    - _Requirements: 6.1, 6.6, 9.6_
  
  - [ ]* 6.3 Write property test for storage manager
    - **Property 3: Upload idempotency**
    - **Validates: Requirements 6.3, 9.3**
    - Test that uploading same file twice with same key produces consistent results

- [x] 7. Implement authentication manager for Cognito
  - [x] 7.1 Create auth manager (`aws_services/auth_manager.py`)
    - Implement `AuthManager` class extending `BaseAWSClient`
    - Add method for user authentication using USER_PASSWORD_AUTH flow
    - Add method for user registration with email as username
    - Add method for user verification with confirmation code
    - Add method for token refresh using refresh token
    - Add method for token validation and expiration checking
    - Add method for user logout and token revocation
    - Implement error handling for authentication failures without exposing sensitive details
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 5.1, 5.2, 5.3, 5.4, 5.5, 11.6, 15.1, 15.2, 15.4_
  
  - [ ]* 7.2 Write unit tests for auth manager
    - Test authentication flow with valid credentials
    - Test registration with password policy validation
    - Test token refresh logic
    - Test error handling for invalid credentials
    - _Requirements: 3.4, 4.5, 4.6_

- [x] 8. Implement transcription manager for Transcribe Medical
  - [x] 8.1 Create transcription manager (`aws_services/transcribe_manager.py`)
    - Implement `TranscribeManager` class extending `BaseAWSClient`
    - Add method to start transcription job with medical specialty vocabulary
    - Configure medical transcription mode
    - Add method to check transcription job status
    - Add method to retrieve completed transcript
    - Implement error handling with descriptive failure reasons
    - Add structured logging with job IDs and operation duration
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 11.1, 11.3, 11.5, 15.1, 15.2, 15.6_
  
  - [ ]* 8.2 Write unit tests for transcription manager
    - Test transcription job submission
    - Test job status polling
    - Test transcript retrieval
    - Test error handling for failed jobs
    - _Requirements: 7.7_

- [x] 9. Implement comprehend manager for medical entity extraction
  - [x] 9.1 Create comprehend manager (`aws_services/comprehend_manager.py`)
    - Implement `ComprehendManager` class extending `BaseAWSClient`
    - Add method to detect medical entities from transcript text
    - Extract entity types: medications, conditions, dosages, procedures, anatomy
    - Structure extracted entities as JSON with confidence scores
    - Filter entities with confidence scores below 0.5
    - Implement error handling that returns transcript without entities on failure
    - Add structured logging for entity extraction operations
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 11.1, 11.5, 15.1, 15.2_
  
  - [ ]* 9.2 Write property test for comprehend manager
    - **Property 4: Confidence score filtering**
    - **Validates: Requirements 8.5**
    - Test that all returned entities have confidence >= 0.5
  
  - [ ]* 9.3 Write unit tests for comprehend manager
    - Test entity extraction with sample medical text
    - Test confidence score filtering
    - Test error handling when service fails
    - _Requirements: 8.5, 8.6_

- [ ] 10. Checkpoint - Verify AWS service managers
  - Test each manager class independently with AWS services
  - Verify error handling and retry logic
  - Check structured logging output
  - Ask the user if questions arise

- [x] 11. Implement error handling utilities
  - [x] 11.1 Create error handling utilities (`utils/error_handler.py`)
    - Implement function to extract boto3 ClientError details
    - Add handlers for common AWS errors (throttling, access denied, not found)
    - Implement exponential backoff retry decorator
    - Add function to generate user-friendly error messages
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 11.4_
  
  - [ ]* 11.2 Write unit tests for error handling utilities
    - Test error code extraction from ClientError
    - Test retry logic with exponential backoff
    - Test user-friendly message generation
    - _Requirements: 15.3, 15.6_

- [x] 12. Implement logging configuration
  - [x] 12.1 Create logging configuration (`utils/logger.py`)
    - Configure structured JSON logging for CloudWatch integration
    - Add log formatters with timestamp, level, service name, and message
    - Implement context manager for logging AWS request IDs
    - Add log level configuration from environment variables
    - _Requirements: 11.2, 11.3, 11.5_
  
  - [ ]* 12.2 Write unit tests for logging configuration
    - Test JSON log format structure
    - Test log level filtering
    - _Requirements: 11.2_

- [x] 13. Update Flask app initialization
  - [x] 13.1 Update `app.py` with AWS service initialization
    - Initialize `ConfigManager` at application startup
    - Initialize all AWS service managers (Auth, Storage, Transcribe, Comprehend, Database)
    - Load configuration from Secrets Manager with environment variable fallback
    - Add application startup validation for required configuration
    - Implement graceful error handling for initialization failures
    - Add structured logging for application startup
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 12.1, 12.2, 12.3_
  
  - [ ]* 13.2 Write integration test for app initialization
    - Test successful initialization with all services
    - Test initialization failure handling
    - _Requirements: 1.5, 2.6, 12.3_

- [x] 14. Implement authentication routes
  - [x] 14.1 Update login route (`/api/v1/auth/login`)
    - Replace demo authentication with Cognito authentication
    - Call `AuthManager.authenticate()` with user credentials
    - Store Cognito tokens in server-side session
    - Return success response with user information
    - Implement error handling for authentication failures
    - Add logging for authentication attempts
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 5.1, 11.6_
  
  - [x] 14.2 Implement registration route (`/api/v1/auth/register`)
    - Create new endpoint for user registration
    - Call `AuthManager.register()` with user details
    - Handle verification code sending
    - Return appropriate error messages for existing users or policy violations
    - _Requirements: 4.1, 4.2, 4.5, 4.6_
  
  - [x] 14.3 Implement verification route (`/api/v1/auth/verify`)
    - Create endpoint to confirm user registration
    - Call `AuthManager.verify()` with confirmation code
    - Return success or error response
    - _Requirements: 4.3, 4.4_
  
  - [x] 14.4 Update logout route (`/api/v1/auth/logout`)
    - Call `AuthManager.logout()` to revoke tokens
    - Clear session data
    - Return success response
    - _Requirements: 5.2_
  
  - [x] 14.5 Update login_required decorator
    - Validate Cognito token from session
    - Check token expiration
    - Attempt token refresh if expired
    - Redirect to login if refresh fails
    - _Requirements: 3.5, 3.6, 3.7, 5.3, 5.4, 5.5_
  
  - [ ]* 14.6 Write integration tests for authentication routes
    - Test login flow with valid credentials
    - Test registration and verification flow
    - Test logout functionality
    - Test token refresh logic
    - _Requirements: 3.4, 3.7, 4.4, 5.4_

- [x] 15. Implement audio upload and transcription routes
  - [x] 15.1 Create audio upload route (`/api/v1/audio/upload`)
    - Validate uploaded file format and size
    - Generate unique S3 object key using user ID and timestamp
    - Call `StorageManager.upload_audio()` to upload to S3
    - Store audio metadata in database using `Transcription` model
    - Return S3 object key to client
    - Implement error handling for upload failures
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_
  
  - [x] 15.2 Update transcription route (`/api/v1/transcribe`)
    - Retrieve audio S3 key from request
    - Call `TranscribeManager.start_transcription()` with audio location
    - Store transcription job ID in database
    - Return job ID to client
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  
  - [x] 15.3 Create transcription status route (`/api/v1/transcribe/status/<job_id>`)
    - Call `TranscribeManager.get_job_status()` with job ID
    - Return job status to client
    - _Requirements: 7.5_
  
  - [x] 15.4 Create transcription result route (`/api/v1/transcribe/result/<job_id>`)
    - Call `TranscribeManager.get_transcript()` to retrieve completed transcript
    - Call `ComprehendManager.extract_entities()` with transcript text
    - Update database with transcript and extracted entities
    - Return transcript and entities to client
    - Implement error handling for transcription and entity extraction failures
    - _Requirements: 7.6, 7.7, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_
  
  - [ ]* 15.5 Write integration tests for audio and transcription routes
    - Test audio upload with valid file
    - Test file validation and size limits
    - Test transcription job submission
    - Test status polling
    - Test result retrieval with entity extraction
    - _Requirements: 6.6, 7.7, 8.6_

- [x] 16. Implement prescription routes
  - [x] 16.1 Update prescription creation route (`/api/v1/prescriptions`)
    - Extract prescription data from request (patient info, medications, entities)
    - Generate prescription PDF (reuse existing PDF generation logic if available)
    - Call `StorageManager.upload_pdf()` to store PDF in S3
    - Store prescription record in database with S3 key using `Prescription` model
    - Return prescription ID to client
    - Implement error handling to prevent database record creation if PDF upload fails
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.7_
  
  - [x] 16.2 Create prescription download route (`/api/v1/prescriptions/<prescription_id>/download`)
    - Retrieve prescription record from database
    - Call `StorageManager.generate_presigned_url()` for PDF
    - Return presigned URL to client
    - _Requirements: 9.5, 9.6_
  
  - [ ]* 16.3 Write integration tests for prescription routes
    - Test prescription creation with PDF upload
    - Test error handling when PDF upload fails
    - Test presigned URL generation
    - _Requirements: 9.7_

- [x] 17. Implement health check endpoint
  - [x] 17.1 Create health check route (`/health`)
    - Verify database connectivity using `DatabaseManager.health_check()`
    - Verify Secrets Manager connectivity by attempting to retrieve a test secret
    - Return HTTP 200 with status "healthy" and timestamp when all checks pass
    - Return HTTP 503 with failed check details when any check fails
    - Implement 5-second timeout for health check
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_
  
  - [ ]* 17.2 Write integration test for health check
    - Test health check with all services healthy
    - Test health check with database failure
    - Test timeout behavior
    - _Requirements: 13.5, 13.6_

- [x] 18. Implement CORS configuration
  - [x] 18.1 Add CORS configuration to Flask app
    - Install and configure Flask-CORS extension
    - Load allowed origins from environment configuration
    - Configure CORS for authenticated endpoints with credentials support
    - Add CORS headers to presigned URL responses
    - Validate request origin against configured allowed origins
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_
  
  - [ ]* 18.2 Write unit tests for CORS configuration
    - Test CORS headers on authenticated endpoints
    - Test origin validation
    - _Requirements: 14.4, 14.5_

- [x] 19. Update environment configuration
  - [x] 19.1 Update `.env.example` with all AWS configuration variables
    - Add AWS_REGION, AWS_COGNITO_USER_POOL_ID, AWS_COGNITO_CLIENT_ID
    - Add S3_AUDIO_BUCKET, S3_PDF_BUCKET
    - Add DB_SECRET_NAME, FLASK_SECRET_NAME, JWT_SECRET_NAME
    - Add CORS_ALLOWED_ORIGINS
    - Add LOG_LEVEL
    - Document each variable with description
    - _Requirements: 12.1, 12.4, 14.1_
  
  - [x] 19.2 Create deployment documentation
    - Document required IAM permissions for ECS task role
    - Document Secrets Manager secret structure
    - Document environment variable configuration for different environments
    - _Requirements: 1.3, 1.4, 2.1, 2.2, 2.3_

- [ ] 20. Final checkpoint and integration testing
  - Run full integration test suite
  - Test complete flow: login → upload audio → transcribe → extract entities → create prescription → download PDF
  - Verify error handling and logging across all endpoints
  - Test health check endpoint
  - Ensure all tests pass, ask the user if questions arise

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation of functionality
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end flows across multiple components
- All AWS service interactions use boto3 SDK with proper error handling and retry logic
- Structured logging enables CloudWatch integration for production monitoring
