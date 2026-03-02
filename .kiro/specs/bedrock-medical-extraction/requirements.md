# Requirements Document

## Introduction

This feature integrates AWS Bedrock with AWS Comprehend Medical to automatically extract medical information from transcripts and auto-fill prescription forms. The system processes transcription text through Comprehend Medical to identify medical entities (medications, dosages, conditions), then uses Bedrock's function-calling capabilities to intelligently populate prescription fields, reducing manual data entry and improving accuracy.

## Glossary

- **Transcript**: Text output from AWS Transcribe containing medical consultation dialogue
- **Medical_Entity**: Structured medical information extracted by Comprehend Medical (medications, dosages, conditions, procedures, anatomy)
- **Comprehend_Medical**: AWS service that extracts medical information from unstructured text
- **Bedrock_Model**: AWS Bedrock foundation model with function-calling capability
- **Prescription_Form**: Web form containing fields for patient prescriptions (medication name, dosage, frequency, duration, instructions)
- **Extraction_Pipeline**: The complete workflow from transcript to filled prescription form
- **Function_Call**: Bedrock model's structured output that maps to prescription form fields
- **Medical_Extraction_Service**: The backend service that orchestrates Comprehend Medical and Bedrock integration
- **Hospital_Configuration**: JSON configuration defining prescription form fields and layout for a specific hospital
- **Form_Field_Definition**: Specification of a single prescription form field including name, type, validation rules, and display properties

## Requirements

### Requirement 1: Extract Medical Entities from Transcripts

**User Story:** As a healthcare provider, I want medical entities automatically extracted from transcripts, so that I can quickly identify medications, dosages, and conditions without manual review.

#### Acceptance Criteria

1. WHEN a transcript is submitted for processing, THE Medical_Extraction_Service SHALL send the transcript text to Comprehend_Medical
2. WHEN Comprehend_Medical returns entity data, THE Medical_Extraction_Service SHALL parse and structure the medical entities by category (medication, dosage, condition, procedure)
3. IF Comprehend_Medical returns an error, THEN THE Medical_Extraction_Service SHALL log the error and return a descriptive error message to the user
4. THE Medical_Extraction_Service SHALL preserve entity confidence scores from Comprehend_Medical for each extracted entity
5. WHEN entity extraction completes, THE Medical_Extraction_Service SHALL return structured medical entities within 5 seconds for transcripts up to 10000 characters

### Requirement 2: Generate Prescription Data Using Bedrock

**User Story:** As a healthcare provider, I want Bedrock to intelligently interpret medical entities and generate structured prescription data, so that prescription forms are accurately populated.

#### Acceptance Criteria

1. WHEN medical entities are extracted, THE Medical_Extraction_Service SHALL compile entities and transcript context into a prompt for the Bedrock_Model
2. THE Medical_Extraction_Service SHALL configure the Bedrock_Model with function definitions that map to Prescription_Form fields
3. WHEN the Bedrock_Model is invoked, THE Medical_Extraction_Service SHALL request function calls for prescription auto-fill
4. WHEN the Bedrock_Model returns function call data, THE Medical_Extraction_Service SHALL validate the function call structure matches expected prescription fields
5. IF the Bedrock_Model returns invalid or incomplete function call data, THEN THE Medical_Extraction_Service SHALL return a partial result with available fields and log the validation error
6. THE Medical_Extraction_Service SHALL complete Bedrock processing within 10 seconds for typical medical transcripts

### Requirement 3: Auto-Fill Prescription Form

**User Story:** As a healthcare provider, I want prescription forms automatically filled with extracted data, so that I can review and submit prescriptions quickly without manual typing.

#### Acceptance Criteria

1. WHEN Bedrock function call data is validated, THE Medical_Extraction_Service SHALL format the data for Prescription_Form consumption
2. THE Medical_Extraction_Service SHALL map function call outputs to specific Prescription_Form fields (medication_name, dosage, frequency, duration, special_instructions)
3. WHEN prescription data is returned to the frontend, THE Prescription_Form SHALL populate all available fields with the extracted data
4. THE Prescription_Form SHALL visually indicate which fields were auto-filled versus manually entered
5. THE Prescription_Form SHALL allow healthcare providers to edit any auto-filled field before submission
6. WHEN no prescription data can be extracted, THE Prescription_Form SHALL remain empty and display an informational message

### Requirement 4: Handle AWS Service Integration Errors

**User Story:** As a system administrator, I want graceful error handling for AWS service failures, so that users receive clear feedback and the system remains stable.

#### Acceptance Criteria

1. IF Comprehend_Medical is unavailable, THEN THE Medical_Extraction_Service SHALL return an error message indicating the medical extraction service is temporarily unavailable
2. IF Bedrock_Model is unavailable, THEN THE Medical_Extraction_Service SHALL return an error message indicating the AI processing service is temporarily unavailable
3. IF AWS credentials are invalid or expired, THEN THE Medical_Extraction_Service SHALL log the authentication error and return a generic service error to the user
4. IF AWS service rate limits are exceeded, THEN THE Medical_Extraction_Service SHALL implement exponential backoff retry logic up to 3 attempts
5. THE Medical_Extraction_Service SHALL log all AWS service errors with request identifiers for debugging
6. WHEN any AWS service error occurs, THE Medical_Extraction_Service SHALL ensure the application remains responsive and does not crash

### Requirement 5: Secure Medical Data Transmission

**User Story:** As a compliance officer, I want medical data transmitted securely to AWS services, so that patient privacy is protected and regulatory requirements are met.

#### Acceptance Criteria

1. THE Medical_Extraction_Service SHALL transmit all transcript data to AWS services using TLS 1.2 or higher
2. THE Medical_Extraction_Service SHALL use AWS IAM roles with least-privilege permissions for Comprehend_Medical and Bedrock access
3. THE Medical_Extraction_Service SHALL not log or store raw transcript content in application logs
4. THE Medical_Extraction_Service SHALL sanitize error messages to exclude patient-identifiable information before returning to the frontend
5. WHERE audit logging is enabled, THE Medical_Extraction_Service SHALL record extraction requests with timestamps and user identifiers without including medical content

### Requirement 6: Configure Bedrock Model Selection

**User Story:** As a system administrator, I want to configure which Bedrock model is used for medical extraction, so that I can optimize for cost, performance, or accuracy.

#### Acceptance Criteria

1. WHERE model configuration is provided, THE Medical_Extraction_Service SHALL use the specified Bedrock_Model identifier
2. THE Medical_Extraction_Service SHALL validate the configured Bedrock_Model supports function calling capability
3. IF the configured Bedrock_Model does not support function calling, THEN THE Medical_Extraction_Service SHALL log an error and fail to start
4. THE Medical_Extraction_Service SHALL load Bedrock_Model configuration from environment variables or configuration files
5. WHEN no model configuration is provided, THE Medical_Extraction_Service SHALL use a default Bedrock_Model with function calling support

### Requirement 7: Provide Extraction Confidence Indicators

**User Story:** As a healthcare provider, I want to see confidence levels for auto-filled prescription data, so that I can prioritize review of uncertain extractions.

#### Acceptance Criteria

1. WHEN medical entities have confidence scores, THE Medical_Extraction_Service SHALL include confidence scores in the response data
2. THE Prescription_Form SHALL display confidence indicators for each auto-filled field
3. THE Prescription_Form SHALL use visual cues (colors or icons) to indicate high confidence (above 0.8), medium confidence (0.5 to 0.8), and low confidence (below 0.5)
4. WHEN a field has low confidence, THE Prescription_Form SHALL highlight the field for provider review
5. THE Prescription_Form SHALL allow providers to view the original transcript context for any auto-filled field

### Requirement 8: Parse and Format Bedrock Function Call Responses

**User Story:** As a developer, I want Bedrock function call responses properly parsed and validated, so that prescription data is correctly structured for form population.

#### Acceptance Criteria

1. WHEN the Bedrock_Model returns a function call response, THE Medical_Extraction_Service SHALL parse the JSON function call structure
2. THE Medical_Extraction_Service SHALL validate that required prescription fields (medication_name, dosage) are present in the function call
3. THE Medical_Extraction_Service SHALL extract optional fields (frequency, duration, special_instructions) when available
4. IF the function call JSON is malformed, THEN THE Medical_Extraction_Service SHALL log the parsing error and return an empty prescription result
5. THE Medical_Extraction_Service SHALL normalize dosage formats to standard units (mg, ml, tablets) for consistency
6. FOR ALL valid function call responses, THE Medical_Extraction_Service SHALL produce a prescription data structure that can be serialized to JSON and deserialized back to an equivalent structure (round-trip property)


### Requirement 9: Configure Dynamic Prescription Form Fields Per Hospital

**User Story:** As a hospital administrator, I want to configure which fields appear on prescription forms for my hospital, so that the form matches our specific workflow and regulatory requirements without requiring code changes.

#### Acceptance Criteria

1. THE Medical_Extraction_Service SHALL store a Hospital_Configuration for each hospital defining the prescription form fields
2. THE Hospital_Configuration SHALL be stored as JSON and include field definitions with name, type, required status, display order, and description for LLM extraction guidance
3. WHEN a prescription form is requested for a hospital, THE Medical_Extraction_Service SHALL retrieve the Hospital_Configuration for that hospital
4. THE Medical_Extraction_Service SHALL generate Bedrock function definitions dynamically based on the Hospital_Configuration fields, including field descriptions in the function schema to guide the LLM
5. WHEN Hospital_Configuration is updated, THE Medical_Extraction_Service SHALL apply the new configuration without requiring application restart or code deployment
6. THE Prescription_Form SHALL render fields dynamically based on the Hospital_Configuration retrieved from the backend
7. WHERE a hospital has not configured custom fields, THE Medical_Extraction_Service SHALL use a default Hospital_Configuration with standard prescription fields (medication_name, dosage, frequency, duration, special_instructions)
8. THE Medical_Extraction_Service SHALL validate Hospital_Configuration JSON structure on load and reject invalid configurations with descriptive error messages
9. FOR ALL valid Hospital_Configuration objects, THE Medical_Extraction_Service SHALL serialize the configuration to JSON, deserialize it, and produce an equivalent configuration object (round-trip property)
10. THE Hospital_Configuration SHALL support field types including text, number, dropdown, and multi-line text for flexible form design
11. WHEN generating Bedrock function call prompts, THE Medical_Extraction_Service SHALL include field descriptions from Hospital_Configuration to instruct the Bedrock_Model on what information to extract from transcripts for each field

#### Sample Hospital Configuration JSON

```json
{
  "hospital_id": "hosp_12345",
  "hospital_name": "City General Hospital",
  "version": "1.0",
  "sections": [
    {
      "section_id": "patient_details",
      "section_label": "Patient Details",
      "display_order": 1,
      "fields": [
        {
          "field_name": "patient_name",
          "display_label": "Name",
          "field_type": "text",
          "required": true,
          "display_order": 1,
          "max_length": 100,
          "description": "The full name of the patient as mentioned in the consultation. Look for phrases like 'patient name is', 'this is', or names mentioned at the beginning of the transcript. Extract the complete first and last name."
        },
        {
          "field_name": "patient_age",
          "display_label": "Age",
          "field_type": "number",
          "required": true,
          "display_order": 2,
          "min_value": 0,
          "max_value": 150,
          "description": "The patient's age in years. Look for phrases like 'years old', 'age is', or age mentioned in patient demographics. Extract only the numeric value."
        },
        {
          "field_name": "patient_sex",
          "display_label": "Sex",
          "field_type": "dropdown",
          "required": true,
          "display_order": 3,
          "options": ["Male", "Female", "Other"],
          "description": "The patient's biological sex or gender. Look for pronouns (he/she/they), explicit mentions of 'male', 'female', or gender-specific medical terms. Map to one of: Male, Female, or Other."
        },
        {
          "field_name": "patient_weight",
          "display_label": "Weight",
          "field_type": "text",
          "required": false,
          "display_order": 4,
          "placeholder": "e.g., 78 kg",
          "unit": "kg",
          "description": "The patient's body weight with unit. Look for phrases like 'weighs', 'weight is', or weight mentioned in vitals. Extract the numeric value and unit (kg, lbs, pounds). Convert to kg if possible and format as 'X kg'."
        },
        {
          "field_name": "patient_id",
          "display_label": "Patient ID",
          "field_type": "text",
          "required": true,
          "display_order": 5,
          "max_length": 50,
          "description": "The unique patient identifier or medical record number. Look for phrases like 'patient ID', 'MRN', 'medical record number', 'patient number', or alphanumeric codes mentioned in patient identification. Extract the complete identifier."
        }
      ]
    },
    {
      "section_id": "vitals",
      "section_label": "Vitals",
      "display_order": 2,
      "fields": [
        {
          "field_name": "blood_pressure",
          "display_label": "BP",
          "field_type": "text",
          "required": false,
          "display_order": 1,
          "placeholder": "e.g., 120/80",
          "unit": "mmHg",
          "description": "The patient's blood pressure reading in systolic/diastolic format. Look for phrases like 'blood pressure', 'BP is', or vital signs. Extract in format 'X/Y' where X is systolic and Y is diastolic (e.g., 120/80)."
        },
        {
          "field_name": "heart_rate",
          "display_label": "HR",
          "field_type": "text",
          "required": false,
          "display_order": 2,
          "placeholder": "e.g., 72 bpm",
          "unit": "bpm",
          "description": "The patient's heart rate in beats per minute. Look for phrases like 'heart rate', 'pulse', 'HR', or vital signs. Extract the numeric value and format as 'X bpm'."
        },
        {
          "field_name": "temperature",
          "display_label": "TEMP",
          "field_type": "text",
          "required": false,
          "display_order": 3,
          "placeholder": "e.g., 98.6°F",
          "unit": "°F",
          "description": "The patient's body temperature with unit. Look for phrases like 'temperature', 'temp', 'fever', or vital signs. Extract the numeric value and unit (°F, °C, Fahrenheit, Celsius). Format as 'X°F' or 'X°C'."
        },
        {
          "field_name": "oxygen_saturation",
          "display_label": "SPO2",
          "field_type": "text",
          "required": false,
          "display_order": 4,
          "placeholder": "e.g., 98%",
          "unit": "%",
          "description": "The patient's oxygen saturation level as a percentage. Look for phrases like 'oxygen saturation', 'SpO2', 'O2 sat', or vital signs. Extract the numeric value and format as 'X%'."
        }
      ]
    },
    {
      "section_id": "diagnosis",
      "section_label": "Diagnosis",
      "display_order": 3,
      "fields": [
        {
          "field_name": "diagnosis",
          "display_label": "Diagnosis",
          "field_type": "multiline",
          "required": true,
          "display_order": 1,
          "rows": 4,
          "max_length": 1000,
          "description": "The primary medical diagnosis or condition identified during the consultation. Look for phrases like 'diagnosis is', 'diagnosed with', 'condition', 'suffering from', or the doctor's assessment section. Extract the complete medical condition name and any relevant qualifiers (acute, chronic, mild, severe). Include ICD codes if mentioned."
        }
      ]
    },
    {
      "section_id": "medications",
      "section_label": "Medications",
      "display_order": 4,
      "repeatable": true,
      "fields": [
        {
          "field_name": "medicine_name",
          "display_label": "Medicine Name",
          "field_type": "text",
          "required": true,
          "display_order": 1,
          "max_length": 200,
          "description": "The generic or brand name of the medication prescribed. Look for phrases like 'I'm prescribing', 'take', 'medication', 'give', 'start on', or prescription instructions. Extract the complete drug name (generic preferred, but include brand name if that's what's mentioned)."
        },
        {
          "field_name": "medicine_type",
          "display_label": "Medicine Type",
          "field_type": "text",
          "required": false,
          "display_order": 2,
          "placeholder": "e.g., Capsule, Tablet, Syrup",
          "max_length": 50,
          "description": "The pharmaceutical form of the medication. Look for words like 'tablet', 'capsule', 'syrup', 'injection', 'cream', 'drops', 'inhaler' mentioned with the medication name. Extract the form type."
        },
        {
          "field_name": "dose",
          "display_label": "Dose",
          "field_type": "text",
          "required": true,
          "display_order": 3,
          "placeholder": "e.g., 500mg, 10ml",
          "max_length": 50,
          "description": "The dosage amount and unit for each administration. Look for numeric values followed by units like 'mg', 'ml', 'mcg', 'tablets', 'capsules', 'teaspoons' in medication instructions. Extract the numeric value and unit (e.g., 500mg, 2 tablets, 10ml). If a range is given, use the standard dose."
        },
        {
          "field_name": "frequency",
          "display_label": "Frequency",
          "field_type": "dropdown",
          "required": true,
          "display_order": 4,
          "options": ["OD", "BDS", "TDS", "QID", "PRN", "STAT"],
          "description": "How often the medication should be taken. Look for phrases describing frequency and map to standard abbreviations: 'once daily/once a day/one time' → OD, 'twice daily/twice a day/two times' → BDS, 'three times daily/thrice' → TDS, 'four times daily' → QID, 'as needed/when required/if needed' → PRN, 'immediately/right now/stat' → STAT."
        },
        {
          "field_name": "duration",
          "display_label": "Duration",
          "field_type": "text",
          "required": true,
          "display_order": 5,
          "placeholder": "e.g., 7 Days, 2 Weeks",
          "max_length": 50,
          "description": "The total length of time the medication should be taken. Look for phrases like 'for X days', 'for X weeks', 'for X months', 'continue for', 'course of'. Extract the numeric value and time unit. Format as 'X Days', 'X Weeks', or 'X Months'. If ongoing, use 'Ongoing' or 'Until review'."
        }
      ]
    },
    {
      "section_id": "clinical_notes",
      "section_label": "Clinical Notes",
      "display_order": 5,
      "fields": [
        {
          "field_name": "clinical_notes",
          "display_label": "Clinical Notes",
          "field_type": "multiline",
          "required": false,
          "display_order": 1,
          "rows": 6,
          "max_length": 2000,
          "description": "Additional clinical observations, patient history, examination findings, or special instructions not captured in other fields. Look for the doctor's notes, observations, patient complaints, examination findings, follow-up instructions, warnings, or any other relevant clinical information. Summarize key points concisely."
        }
      ]
    }
  ]
}
```

This sample configuration demonstrates:
- Grouped fields by section (patient_details, vitals, diagnosis, medications, clinical_notes)
- Multiple field types (text, number, dropdown, multiline)
- Required vs optional fields
- Display ordering within sections
- Dropdown options for standardized values (sex, frequency)
- Unit specifications for fields with measurements
- Placeholders for user guidance
- Validation constraints (min/max values, max_length)
- Repeatable sections for medications (multiple rows)
- Flexibility to add or remove fields per hospital needs
