# Bedrock Medical Extraction - Quick Start Guide

## Overview

The Bedrock Medical Extraction feature uses AWS Comprehend Medical and AWS Bedrock to automatically extract prescription data from medical transcripts. This guide will help you test the complete end-to-end flow.

## Prerequisites

1. **AWS Services Configured**:
   - AWS Comprehend Medical access
   - AWS Bedrock access (Claude 3 models)
   - IAM permissions configured (see `seva-arogya-infra/README_BEDROCK.md`)

2. **Environment Variables** (in `.env`):
   ```
   BEDROCK_REGION=us-east-1
   BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
   AWS_COMPREHEND_REGION=us-east-1
   ```

3. **Hospital Configuration**:
   - Default config available at `config/hospitals/default.json`
   - Custom configs can be added for specific hospitals

## Testing the Feature

### 1. Start the Application

```bash
python app.py
```

### 2. Navigate to Transcription Page

1. Log in to the application
2. Go to the transcription page (`/transcription`)
3. Record or simulate a medical consultation

### 3. Use AI Extraction

After recording, you'll see two buttons:
- **AI Extract Prescription** (blue gradient) - Uses Bedrock AI extraction
- **Manual Review** (gray) - Traditional manual entry

Click "AI Extract Prescription" to test the feature.

### 4. Review Extracted Data

The AI-assisted prescription page will display:
- **Dynamically rendered form** based on hospital configuration
- **Confidence indicators** for each field:
  - 🟢 Green border = High confidence (>80%)
  - 🟡 Yellow border = Medium confidence (50-80%)
  - 🔴 Red border = Low confidence (<50%)
  - ⚪ Gray border = Manual entry
- **Source context** - Click the info icon to see the original transcript excerpt
- **Editable fields** - All fields remain editable regardless of confidence

### 5. Test with Sample Transcript

Use this sample transcript for testing:

```
Patient name is John Smith, 45 years old, male, weighs 78 kilograms. 
Patient ID is CGH-9921. Blood pressure is 120 over 80, heart rate 72 beats per minute, 
temperature 98.6 Fahrenheit, oxygen saturation 98 percent.

Diagnosis is acute bacterial sinusitis.

I'm prescribing Amoxicillin capsules, 500 milligrams, three times daily for 7 days.
Also prescribe Paracetamol tablets, 650 milligrams, as needed for fever, for 3 days.

Patient should return if fever persists beyond 48 hours. Drink plenty of warm fluids.
```

## API Endpoints

### Extract Prescription Data

```http
POST /api/v1/extract
Content-Type: application/json

{
  "transcript": "Patient name is...",
  "hospital_id": "default",
  "request_id": "optional-uuid"
}
```

**Response**:
```json
{
  "status": "success",
  "prescription_data": {
    "sections": {
      "patient_details": {
        "patient_name": "John Smith",
        "patient_name_data": {
          "confidence": 0.95,
          "source_text": "Patient name is John Smith"
        },
        ...
      },
      "medications": [
        {
          "medicine_name": "Amoxicillin",
          "dose": "500mg",
          "frequency": "TDS",
          "duration": "7 Days",
          ...
        }
      ]
    }
  },
  "request_id": "uuid"
}
```

### Get Hospital Configuration

```http
GET /api/v1/config/{hospital_id}
```

**Response**: Hospital configuration JSON with sections and fields

## Troubleshooting

### Extraction Fails

1. **Check AWS credentials**: Ensure IAM role has Comprehend Medical and Bedrock permissions
2. **Check model availability**: Verify Bedrock model is available in your region
3. **Check transcript length**: Maximum 10,000 characters
4. **Check logs**: Review `logs/app.log` for detailed error messages

### No Data Extracted

1. **Transcript quality**: Ensure transcript contains medical information
2. **Field descriptions**: Check hospital config has clear field descriptions
3. **Model configuration**: Verify correct Bedrock model ID in environment

### Confidence Scores Low

1. **Transcript clarity**: Improve audio quality or transcription accuracy
2. **Field descriptions**: Enhance field descriptions in hospital config
3. **Medical terminology**: Use standard medical terms in transcripts

## Configuration Customization

### Adding Custom Hospital Configuration

1. Create a new JSON file in `config/hospitals/`:
   ```bash
   cp config/hospitals/default.json config/hospitals/hosp_12345.json
   ```

2. Customize sections and fields:
   - Add/remove sections
   - Modify field types (text, number, dropdown, multiline)
   - Update field descriptions for better LLM guidance
   - Set required fields

3. Use the custom config:
   ```javascript
   await extractPrescriptionData(transcript, 'hosp_12345');
   ```

### Field Types Supported

- **text**: Single-line text input
- **number**: Numeric input with min/max validation
- **dropdown**: Select from predefined options
- **multiline**: Multi-line text area

### Repeatable Sections

For sections like medications that can have multiple entries:
```json
{
  "section_id": "medications",
  "repeatable": true,
  "fields": [...]
}
```

## Performance Expectations

- **Entity Extraction**: < 5 seconds (Comprehend Medical)
- **AI Processing**: < 10 seconds (Bedrock)
- **Total Response Time**: < 15 seconds for typical transcripts

## Security Notes

- All AWS API calls use TLS 1.2+
- Transcript content is NOT logged (PHI protection)
- Error messages are sanitized to exclude patient information
- Audit logs include timestamps and user IDs only

## Next Steps

1. Test with real medical transcripts
2. Customize hospital configurations for your use case
3. Monitor extraction accuracy and confidence scores
4. Adjust field descriptions to improve extraction quality
5. Integrate with PDF generation for complete workflow

## Support

For issues or questions:
1. Check `BEDROCK_IMPLEMENTATION_STATUS.md` for implementation details
2. Review `seva-arogya-infra/README_BEDROCK.md` for AWS setup
3. Check application logs in `logs/app.log`
4. Review task list in `.kiro/specs/bedrock-medical-extraction/tasks.md`
