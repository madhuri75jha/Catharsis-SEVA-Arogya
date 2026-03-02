# Design Document: Recent Consultations Display on Home Page

## Overview

This design specifies the technical implementation for displaying recent consultations on the home page of the SEVA Arogya medical transcription application. The feature enables healthcare providers to view their recent consultations, expand to see more, and navigate to detailed consultation views.

The implementation integrates with the existing Flask-based architecture, PostgreSQL database, and follows established patterns for authentication, data access, and UI rendering. The design emphasizes efficient data retrieval, responsive UI updates, and seamless navigation between views.

### Key Design Decisions

1. **Consultation Data Model**: A consultation is defined as a transcription record with an optionally associated prescription, joined by user_id and temporal proximity (prescriptions created within 1 hour of transcription)
2. **API-First Approach**: Implement a REST API endpoint for consultation retrieval to enable asynchronous data loading and future mobile app support
3. **Client-Side Rendering**: Use JavaScript to dynamically render consultation cards, enabling smooth expand/collapse interactions without page reloads
4. **Database Query Optimization**: Use a single SQL query with LEFT JOIN to retrieve both transcription and prescription data efficiently
5. **Relative Time Formatting**: Implement client-side time formatting to display human-readable timestamps without server-side processing

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser (Client)                      │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │  home.html     │  │  home.js     │  │  Consultation   │ │
│  │  (Template)    │◄─┤  (Logic)     │◄─┤  Cards (DOM)    │ │
│  └────────────────┘  └──────┬───────┘  └─────────────────┘ │
└────────────────────────────┼────────────────────────────────┘
                             │ AJAX Request
                             │ GET /api/consultations
┌────────────────────────────┼────────────────────────────────┐
│                    Flask Application (app.py)                │
│  ┌──────────────────────────┼──────────────────────────────┐│
│  │  Route: /api/consultations                              ││
│  │  - Authentication check (@login_required)               ││
│  │  - Extract user_id from session                         ││
│  │  - Call ConsultationService.get_recent_consultations()  ││
│  │  - Return JSON response                                 ││
│  └─────────────────────────┬───────────────────────────────┘│
└────────────────────────────┼────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────┐
│              ConsultationService (New Module)                │
│  ┌──────────────────────────┼──────────────────────────────┐│
│  │  get_recent_consultations(user_id, limit)               ││
│  │  - Query database via DatabaseManager                   ││
│  │  - Join transcriptions with prescriptions               ││
│  │  - Extract patient names from medical_entities          ││
│  │  - Format consultation objects                          ││
│  │  - Return list of consultation dictionaries             ││
│  └─────────────────────────┬───────────────────────────────┘│
└────────────────────────────┼────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────┐
│              DatabaseManager (Existing)                      │
│  ┌──────────────────────────┼──────────────────────────────┐│
│  │  execute_with_retry(query, params)                      ││
│  │  - Execute SQL query with connection pooling            ││
│  │  - Retry logic for transient failures                   ││
│  │  - Return query results                                 ││
│  └─────────────────────────┬───────────────────────────────┘│
└────────────────────────────┼────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────┐
│                   PostgreSQL Database                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Tables:                                                 ││
│  │  - transcriptions (transcription_id, user_id, status,   ││
│  │                    transcript_text, medical_entities,    ││
│  │                    created_at, updated_at)               ││
│  │  - prescriptions (prescription_id, user_id,             ││
│  │                   patient_name, medications, created_at) ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Page Load**: User navigates to /home, Flask renders home.html template
2. **Initial Data Fetch**: JavaScript executes on page load, sends GET request to /api/consultations?limit=10
3. **Authentication**: Flask @login_required decorator validates session, extracts user_id
4. **Data Retrieval**: ConsultationService queries database, joins transcriptions with prescriptions
5. **Response**: API returns JSON array of consultation objects
6. **Rendering**: JavaScript renders 2 consultation cards initially, stores remaining 8 for "View All"
7. **User Interaction**: User clicks "View All", JavaScript renders all 10 cards with smooth animation
8. **Navigation**: User clicks consultation card, JavaScript navigates to /consultation/<id> detail view

## Components and Interfaces

### 1. API Endpoint: `/api/consultations`

**Route Definition**:
```python
@app.route('/api/consultations', methods=['GET'])
@login_required
def api_get_consultations():
    """
    Retrieve recent consultations for authenticated user
    
    Query Parameters:
        limit (int, optional): Maximum consultations to return (default: 10, max: 50)
    
    Returns:
        JSON response with consultation list or error
    """
```

**Request**:
- Method: GET
- Authentication: Required (session-based)
- Query Parameters:
  - `limit` (optional): Integer between 1 and 50, default 10

**Response Success (200)**:
```json
{
  "success": true,
  "consultations": [
    {
      "consultation_id": "trans_123",
      "patient_name": "Arjun Kumar",
      "patient_initials": "AK",
      "status": "COMPLETED",
      "created_at": "2024-01-15T14:30:00Z",
      "has_prescription": true,
      "prescription_id": "presc_456",
      "transcript_preview": "Patient complains of headache..."
    }
  ],
  "count": 10
}
```

**Response Error (401 Unauthorized)**:
```json
{
  "success": false,
  "error": "Authentication required"
}
```

**Response Error (500 Internal Server Error)**:
```json
{
  "success": false,
  "error": "Failed to retrieve consultations"
}
```

### 2. ConsultationService Module

**File**: `services/consultation_service.py` (new file)

**Class**: `ConsultationService`

**Method**: `get_recent_consultations(user_id: str, db_manager: DatabaseManager, limit: int = 10) -> List[Dict[str, Any]]`

**Purpose**: Retrieve and format recent consultations for a user

**Algorithm**:
1. Validate limit parameter (1 <= limit <= 50)
2. Execute SQL query to join transcriptions with prescriptions
3. For each result row:
   - Extract patient name from medical_entities JSONB or prescription patient_name
   - Generate patient initials from name
   - Format consultation object
4. Return list of consultation dictionaries

**SQL Query**:
```sql
SELECT 
    t.transcription_id,
    t.user_id,
    t.transcript_text,
    t.status,
    t.medical_entities,
    t.created_at,
    p.prescription_id,
    p.patient_name,
    p.medications
FROM transcriptions t
LEFT JOIN prescriptions p ON (
    t.user_id = p.user_id 
    AND p.created_at >= t.created_at 
    AND p.created_at <= t.created_at + INTERVAL '1 hour'
)
WHERE t.user_id = %s
ORDER BY t.created_at DESC
LIMIT %s
```

**Patient Name Extraction Logic**:
1. Check if prescription exists and has patient_name → use it
2. Else, check medical_entities for PERSON entities with Category="PROTECTED_HEALTH_INFORMATION" → use first match
3. Else, return "Unknown Patient"

**Initials Generation**:
- Split name by whitespace
- Take first character of first word and first character of last word
- Convert to uppercase
- If name is "Unknown Patient", return "?"

### 3. Frontend JavaScript Module

**File**: `static/js/home.js` (new file)

**Functions**:

```javascript
// Fetch consultations from API
async function fetchConsultations(limit = 10)

// Render consultation cards in DOM
function renderConsultations(consultations, showAll = false)

// Format timestamp to relative time
function formatRelativeTime(isoTimestamp)

// Generate status badge HTML
function getStatusBadge(status)

// Handle "View All" button click
function handleViewAllClick()

// Handle consultation card click
function handleConsultationClick(consultationId)
```

**Relative Time Formatting Logic**:
```javascript
function formatRelativeTime(isoTimestamp) {
    const now = new Date();
    const then = new Date(isoTimestamp);
    const diffMs = now - then;
    const diffMinutes = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMinutes < 60) {
        return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''} ago`;
    } else if (diffHours < 24) {
        return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    } else {
        // Format as "MMM DD, YYYY"
        const options = { year: 'numeric', month: 'short', day: 'numeric' };
        return then.toLocaleDateString('en-US', options);
    }
}
```

### 4. Consultation Detail View

**Route**: `/consultation/<consultation_id>`

**Template**: `templates/consultation_detail.html` (new file)

**Purpose**: Display complete consultation information including transcript, medical entities, and prescription

**Data Retrieved**:
- Transcription record by transcription_id
- Associated prescription (if exists)
- Medical entities from transcription
- Formatted medications from prescription

**UI Sections**:
1. Header: Patient name, consultation date, status badge
2. Transcript: Full transcript text in scrollable container
3. Medical Entities: Extracted entities grouped by type (Medications, Conditions, Procedures)
4. Prescription: Medication list with dosage and frequency (if available)
5. Navigation: Back button to return to home page

### 5. Database Manager Extension

**File**: `aws_services/database_manager.py` (existing, no changes needed)

The existing `execute_with_retry` method provides all necessary functionality for executing the consultation query. No modifications required.

## Data Models

### Consultation Object (API Response)

```python
{
    "consultation_id": str,          # transcription_id
    "patient_name": str,             # Extracted from entities or prescription
    "patient_initials": str,         # Generated from patient_name
    "status": str,                   # COMPLETED | IN_PROGRESS | FAILED
    "created_at": str,               # ISO 8601 timestamp
    "has_prescription": bool,        # True if prescription exists
    "prescription_id": str | None,   # prescription_id if exists
    "transcript_preview": str        # First 100 chars of transcript
}
```

### Database Schema (Existing)

**transcriptions table**:
- transcription_id: SERIAL PRIMARY KEY
- user_id: VARCHAR(255) NOT NULL
- audio_s3_key: VARCHAR(512) NOT NULL
- job_id: VARCHAR(255) NOT NULL UNIQUE
- transcript_text: TEXT
- status: VARCHAR(50) NOT NULL DEFAULT 'PENDING'
- medical_entities: JSONB
- created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- updated_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- session_id: VARCHAR(255)
- streaming_job_id: VARCHAR(255)
- is_streaming: BOOLEAN
- audio_duration_seconds: FLOAT
- sample_rate: INTEGER
- quality: VARCHAR(50)

**prescriptions table**:
- prescription_id: SERIAL PRIMARY KEY
- user_id: VARCHAR(255) NOT NULL
- patient_name: VARCHAR(255) NOT NULL
- medications: JSONB NOT NULL
- s3_key: VARCHAR(512) NOT NULL
- created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### Medical Entities Structure (JSONB)

```json
[
  {
    "Text": "Arjun Kumar",
    "Category": "PROTECTED_HEALTH_INFORMATION",
    "Type": "NAME",
    "Score": 0.99,
    "BeginOffset": 0,
    "EndOffset": 11
  },
  {
    "Text": "headache",
    "Category": "MEDICAL_CONDITION",
    "Type": "DX_NAME",
    "Score": 0.95,
    "BeginOffset": 30,
    "EndOffset": 38
  }
]
```


## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property Reflection

After analyzing all acceptance criteria, the following redundancies were identified and eliminated:

- **2.2** (maintain order in expanded view) is redundant with **1.5** (order by timestamp) - if consultations are correctly ordered initially, displaying all maintains that order
- **2.4** (expanded cards same format) is redundant with **1.3** (card display requirements) - all cards must follow the same format
- **5.1** (display status indicator) is redundant with **1.3** (card displays status) - already covered
- **8.2** (endpoint authentication) is redundant with **4.1** (query filters by user) - same authentication requirement
- **8.7** (endpoint error handling) is redundant with **4.5** (database error handling) - same error handling logic

Status mapping properties **5.2, 5.3, 5.4** can be combined into a single comprehensive property about status indicator mapping.

Time formatting properties **6.2, 6.3, 6.4** can be combined into a single comprehensive property about timestamp formatting rules.

### Property 1: Consultation Retrieval Limit

For any authenticated user and any database state, when the home page loads and requests consultations, the system should return at most 10 consultations, ordered by created_at timestamp in descending order.

**Validates: Requirements 1.1, 1.5**

### Property 2: Initial Display Count

For any set of retrieved consultations, the home page should initially display exactly min(2, consultation_count) consultation cards in the "Recent Consultations" section.

**Validates: Requirements 1.2**

### Property 3: Consultation Card Information Completeness

For any consultation card rendered in the UI, the card HTML should contain the patient name (or "Unknown Patient"), the formatted timestamp, and the status indicator.

**Validates: Requirements 1.3**

### Property 4: View All Expansion

For any set of consultations where count > 2, when the user clicks "View All", the system should display all retrieved consultations (up to 10) in the consultation list.

**Validates: Requirements 2.1**

### Property 5: Expand-Collapse Round Trip

For any consultation list, expanding to view all consultations and then collapsing should return the display to showing exactly min(2, consultation_count) consultations.

**Validates: Requirements 2.3**

### Property 6: Consultation Navigation

For any consultation card, when clicked, the system should navigate to the consultation detail view with the URL path `/consultation/<consultation_id>` where consultation_id matches the clicked consultation's transcription_id.

**Validates: Requirements 3.1**

### Property 7: Detail View Transcript Display

For any consultation with non-null transcript_text, the consultation detail view should display the complete transcript text in the transcript section.

**Validates: Requirements 3.2**

### Property 8: Detail View Medical Entities Display

For any consultation with non-empty medical_entities array, the consultation detail view should display the extracted medical entities grouped by category.

**Validates: Requirements 3.3**

### Property 9: Detail View Prescription Display

For any consultation where has_prescription is true, the consultation detail view should display the prescription information including medications, dosage, and frequency.

**Validates: Requirements 3.4**

### Property 10: Detail View Navigation Round Trip

For any consultation, navigating from home page to consultation detail view and clicking the back button should return the user to the home page.

**Validates: Requirements 3.5**

### Property 11: User Data Isolation

For any authenticated user, the consultations API endpoint should return only consultations where the transcription user_id matches the authenticated user's user_id, and should not return consultations belonging to other users.

**Validates: Requirements 4.1, 8.2**

### Property 12: Transcription-Prescription Join Logic

For any transcription and prescription pair where both have the same user_id and the prescription created_at is between transcription created_at and transcription created_at + 1 hour, the consultation object should have has_prescription=true and include the prescription_id.

**Validates: Requirements 4.2**

### Property 13: Transcription Without Prescription Inclusion

For any transcription that has no prescription matching the join criteria (same user_id, within 1 hour), the consultation object should still be included in results with has_prescription=false and prescription_id=null.

**Validates: Requirements 4.3**

### Property 14: Database Error Handling

For any database query failure (connection error, timeout, or query error), the system should log the error with sufficient detail for debugging and return a user-friendly error message without exposing internal details.

**Validates: Requirements 4.5, 8.7**

### Property 15: Status Indicator Mapping

For any consultation, the status indicator displayed should map as follows: "COMPLETED" → "Complete", "IN_PROGRESS" → "In Progress", "FAILED" → "Failed", with each status having a distinct visual representation.

**Validates: Requirements 5.2, 5.3, 5.4**

### Property 16: Timestamp Formatting Rules

For any consultation timestamp, the formatted display should follow these rules: if less than 1 hour ago, display "X minutes ago"; if between 1 and 24 hours ago, display "X hours ago"; if more than 24 hours ago, display date in "MMM DD, YYYY" format.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4**

### Property 17: Incomplete Data Display

For any consultation, regardless of whether patient_name, transcript_text, or medical_entities are null or empty, the consultation should still be included in the consultation list and be navigable.

**Validates: Requirements 7.3**

### Property 18: Patient Initials Generation

For any patient name string, the initials should be generated by taking the first character of the first word and the first character of the last word, converted to uppercase; for "Unknown Patient" or null names, the initials should be "?".

**Validates: Requirements 7.4**

### Property 19: API Limit Parameter Handling

For any request to /api/consultations, if the limit query parameter is provided, it should be used (capped at 50); if not provided, the default limit of 10 should be used.

**Validates: Requirements 8.3**

### Property 20: API Response Format

For any successful request to /api/consultations, the response should be valid JSON with a "success" boolean field, a "consultations" array field, and a "count" integer field.

**Validates: Requirements 8.4**

### Property 21: API Success Status Code

For any successful request to /api/consultations where the database query succeeds, the HTTP response status code should be 200.

**Validates: Requirements 8.5**

### Property 22: API Authentication Failure Status Code

For any request to /api/consultations without valid authentication (no session or invalid token), the HTTP response status code should be 401.

**Validates: Requirements 8.6**

## Error Handling

### Error Scenarios and Responses

1. **Database Connection Failure**
   - Detection: DatabaseManager.execute_with_retry raises OperationalError after max retries
   - Logging: Log error with connection details (host, port, database name)
   - User Response: Return JSON `{"success": false, "error": "Unable to retrieve consultations. Please try again later."}`
   - HTTP Status: 500

2. **Database Query Timeout**
   - Detection: Query exceeds statement_timeout (5 seconds)
   - Logging: Log query and parameters (sanitized)
   - User Response: Return JSON `{"success": false, "error": "Request timed out. Please try again."}`
   - HTTP Status: 500

3. **Authentication Failure**
   - Detection: @login_required decorator finds no user_id in session
   - Logging: Log attempted access with IP address
   - User Response: Redirect to /login for page requests, return JSON `{"success": false, "error": "Authentication required"}` for API requests
   - HTTP Status: 401

4. **Invalid Limit Parameter**
   - Detection: limit parameter is not an integer or is outside valid range
   - Logging: Log invalid parameter value
   - User Response: Use default limit of 10, log warning
   - HTTP Status: 200 (graceful degradation)

5. **Empty Consultation List**
   - Detection: Database query returns empty result set
   - Logging: Log info message with user_id
   - User Response: Return JSON `{"success": true, "consultations": [], "count": 0}`
   - HTTP Status: 200
   - UI Behavior: Display "No recent consultations found" message

6. **Malformed Medical Entities JSON**
   - Detection: JSON parsing of medical_entities JSONB field fails
   - Logging: Log error with transcription_id
   - User Response: Set medical_entities to empty array, continue processing
   - HTTP Status: 200 (graceful degradation)

7. **Missing Patient Name**
   - Detection: No patient name in prescription and no PERSON entity in medical_entities
   - Logging: Log warning with transcription_id
   - User Response: Set patient_name to "Unknown Patient", patient_initials to "?"
   - HTTP Status: 200 (graceful degradation)

### Error Recovery Strategies

1. **Retry Logic**: DatabaseManager already implements exponential backoff retry (3 attempts) for transient database errors
2. **Connection Pooling**: Connection pool maintains 2-10 connections, automatically recovers from connection failures
3. **Graceful Degradation**: Missing optional data (patient name, medical entities) doesn't prevent consultation display
4. **User Feedback**: All errors provide clear, actionable messages without exposing internal implementation details

## Testing Strategy

### Dual Testing Approach

This feature requires both unit testing and property-based testing to ensure comprehensive coverage:

- **Unit Tests**: Verify specific examples, edge cases, and error conditions
- **Property Tests**: Verify universal properties across all inputs through randomized testing

Both approaches are complementary and necessary. Unit tests catch concrete bugs in specific scenarios, while property tests verify general correctness across a wide range of inputs.

### Property-Based Testing Configuration

**Library Selection**: Use `hypothesis` for Python property-based testing

**Test Configuration**:
- Minimum 100 iterations per property test (due to randomization)
- Each property test must reference its design document property in a comment
- Tag format: `# Feature: recent-consultations-home-display, Property {number}: {property_text}`

**Example Property Test Structure**:
```python
from hypothesis import given, strategies as st
import hypothesis

# Feature: recent-consultations-home-display, Property 1: Consultation Retrieval Limit
@given(
    user_id=st.text(min_size=1, max_size=255),
    consultation_count=st.integers(min_value=0, max_value=100)
)
@hypothesis.settings(max_examples=100)
def test_consultation_retrieval_limit(user_id, consultation_count):
    # Setup: Create consultation_count consultations for user_id
    # Execute: Call get_recent_consultations(user_id, limit=10)
    # Assert: len(result) <= 10 and len(result) <= consultation_count
    pass
```

### Unit Testing Focus Areas

1. **Specific Examples**:
   - Test with exactly 2 consultations (boundary case)
   - Test with exactly 10 consultations (limit boundary)
   - Test with 0 consultations (empty state)

2. **Edge Cases**:
   - Consultation with no patient name → displays "Unknown Patient"
   - Consultation with no transcript text → displays "No transcript available" in detail view
   - Consultation with empty medical_entities array
   - Prescription created exactly 1 hour after transcription (boundary of join window)

3. **Integration Points**:
   - API endpoint authentication flow
   - Database query execution and result parsing
   - JSON serialization of consultation objects
   - Frontend JavaScript rendering of consultation cards

4. **Error Conditions**:
   - Database connection failure
   - Invalid limit parameter values
   - Malformed JSONB data in medical_entities
   - Missing required fields in database results

### Property Testing Focus Areas

1. **Universal Properties**:
   - Consultation retrieval always returns ≤ limit consultations
   - Consultations always ordered by created_at DESC
   - User data isolation (no cross-user data leakage)
   - Round-trip properties (expand/collapse, navigate/back)

2. **Data Transformation Properties**:
   - Patient initials generation for any valid name
   - Timestamp formatting for any valid timestamp
   - Status indicator mapping for any valid status

3. **Comprehensive Input Coverage**:
   - Random user_ids, consultation counts, timestamps
   - Random patient names (including unicode, special characters)
   - Random status values, medical entities structures

### Test File Organization

```
tests/
├── unit/
│   ├── test_consultation_service.py
│   ├── test_api_consultations.py
│   ├── test_consultation_detail_view.py
│   └── test_patient_name_extraction.py
├── property/
│   ├── test_consultation_properties.py
│   ├── test_timestamp_formatting_properties.py
│   └── test_data_isolation_properties.py
└── integration/
    ├── test_consultation_flow.py
    └── test_error_handling.py
```

### Coverage Goals

- **Line Coverage**: Minimum 90% for new code
- **Branch Coverage**: Minimum 85% for conditional logic
- **Property Coverage**: All 22 correctness properties must have corresponding property tests
- **Edge Case Coverage**: All edge cases from requirements must have unit tests

