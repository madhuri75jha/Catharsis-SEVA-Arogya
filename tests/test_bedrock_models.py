"""
Unit tests for Bedrock extraction data models

Tests model validation, serialization, and business logic.
"""

import pytest
from pydantic import ValidationError
from models.bedrock_extraction import (
    MedicalEntity, EntityType, FieldDefinition, FieldType,
    SectionDefinition, HospitalConfiguration, ExtractedField,
    ExtractedSection, PrescriptionData, ValidationResult,
    ExtractionRequest, ExtractionResponse, ErrorCode, ExtractionError
)


class TestMedicalEntity:
    """Tests for MedicalEntity model"""
    
    def test_valid_medical_entity(self):
        """Test creating a valid medical entity"""
        entity = MedicalEntity(
            entity_type=EntityType.MEDICATION,
            text="Amoxicillin",
            confidence=0.95,
            begin_offset=10,
            end_offset=21
        )
        assert entity.entity_type == EntityType.MEDICATION
        assert entity.text == "Amoxicillin"
        assert entity.confidence == 0.95
    
    def test_confidence_validation(self):
        """Test confidence score must be between 0 and 1"""
        with pytest.raises(ValidationError):
            MedicalEntity(
                entity_type=EntityType.MEDICATION,
                text="Test",
                confidence=1.5,  # Invalid
                begin_offset=0,
                end_offset=4
            )


class TestFieldDefinition:
    """Tests for FieldDefinition model"""
    
    def test_valid_text_field(self):
        """Test creating a valid text field"""
        field = FieldDefinition(
            field_name="patient_name",
            display_label="Patient Name",
            field_type=FieldType.TEXT,
            required=True,
            display_order=1,
            description="The patient's full name",
            max_length=100
        )
        assert field.field_name == "patient_name"
        assert field.field_type == FieldType.TEXT
        assert field.required is True
    
    def test_valid_dropdown_field(self):
        """Test creating a valid dropdown field"""
        field = FieldDefinition(
            field_name="frequency",
            display_label="Frequency",
            field_type=FieldType.DROPDOWN,
            required=True,
            display_order=1,
            description="Medication frequency",
            options=["OD", "BDS", "TDS", "QID"]
        )
        assert field.options == ["OD", "BDS", "TDS", "QID"]


class TestHospitalConfiguration:
    """Tests for HospitalConfiguration model"""
    
    def test_valid_configuration(self):
        """Test creating a valid hospital configuration"""
        config = HospitalConfiguration(
            hospital_id="hosp_123",
            hospital_name="Test Hospital",
            version="1.0",
            sections=[
                SectionDefinition(
                    section_id="patient_details",
                    section_label="Patient Details",
                    display_order=1,
                    fields=[
                        FieldDefinition(
                            field_name="patient_name",
                            display_label="Name",
                            field_type=FieldType.TEXT,
                            required=True,
                            display_order=1,
                            description="Patient name"
                        )
                    ]
                )
            ]
        )
        assert config.hospital_id == "hosp_123"
        assert len(config.sections) == 1
    
    def test_duplicate_section_ids_rejected(self):
        """Test that duplicate section IDs are rejected"""
        with pytest.raises(ValidationError, match="Duplicate section IDs"):
            HospitalConfiguration(
                hospital_id="hosp_123",
                hospital_name="Test Hospital",
                version="1.0",
                sections=[
                    SectionDefinition(
                        section_id="patient_details",
                        section_label="Patient Details",
                        display_order=1,
                        fields=[]
                    ),
                    SectionDefinition(
                        section_id="patient_details",  # Duplicate
                        section_label="Patient Details 2",
                        display_order=2,
                        fields=[]
                    )
                ]
            )
    
    def test_duplicate_field_names_rejected(self):
        """Test that duplicate field names within a section are rejected"""
        with pytest.raises(ValidationError, match="Duplicate field names"):
            HospitalConfiguration(
                hospital_id="hosp_123",
                hospital_name="Test Hospital",
                version="1.0",
                sections=[
                    SectionDefinition(
                        section_id="patient_details",
                        section_label="Patient Details",
                        display_order=1,
                        fields=[
                            FieldDefinition(
                                field_name="patient_name",
                                display_label="Name",
                                field_type=FieldType.TEXT,
                                required=True,
                                display_order=1,
                                description="Patient name"
                            ),
                            FieldDefinition(
                                field_name="patient_name",  # Duplicate
                                display_label="Name 2",
                                field_type=FieldType.TEXT,
                                required=True,
                                display_order=2,
                                description="Patient name 2"
                            )
                        ]
                    )
                ]
            )


class TestExtractionRequest:
    """Tests for ExtractionRequest model"""
    
    def test_valid_request(self):
        """Test creating a valid extraction request"""
        request = ExtractionRequest(
            transcript="Patient presents with fever and cough.",
            hospital_id="hosp_123"
        )
        assert request.transcript == "Patient presents with fever and cough."
        assert request.hospital_id == "hosp_123"
    
    def test_empty_transcript_rejected(self):
        """Test that empty transcript is rejected"""
        with pytest.raises(ValidationError):
            ExtractionRequest(
                transcript="",
                hospital_id="hosp_123"
            )
    
    def test_whitespace_only_transcript_rejected(self):
        """Test that whitespace-only transcript is rejected"""
        with pytest.raises(ValidationError):
            ExtractionRequest(
                transcript="   \n\t  ",
                hospital_id="hosp_123"
            )
    
    def test_transcript_too_long_rejected(self):
        """Test that transcript exceeding max length is rejected"""
        with pytest.raises(ValidationError):
            ExtractionRequest(
                transcript="x" * 10001,  # Exceeds 10000 char limit
                hospital_id="hosp_123"
            )
    
    def test_transcript_whitespace_trimmed(self):
        """Test that transcript whitespace is trimmed"""
        request = ExtractionRequest(
            transcript="  Patient presents with fever.  \n",
            hospital_id="hosp_123"
        )
        assert request.transcript == "Patient presents with fever."


class TestPrescriptionData:
    """Tests for PrescriptionData model"""
    
    def test_valid_prescription_data(self):
        """Test creating valid prescription data"""
        data = PrescriptionData(
            sections=[
                ExtractedSection(
                    section_id="medications",
                    fields=[
                        ExtractedField(
                            field_name="medicine_name",
                            value="Amoxicillin",
                            confidence=0.95,
                            source_text="I'm prescribing Amoxicillin"
                        )
                    ]
                )
            ],
            processing_time_ms=3500
        )
        assert len(data.sections) == 1
        assert data.processing_time_ms == 3500


class TestValidationResult:
    """Tests for ValidationResult model"""
    
    def test_valid_result(self):
        """Test creating a valid validation result"""
        result = ValidationResult(
            is_valid=True,
            valid_fields=["medicine_name", "dosage"],
            invalid_fields=[],
            errors=[]
        )
        assert result.is_valid is True
        assert len(result.valid_fields) == 2
    
    def test_invalid_result_with_errors(self):
        """Test creating an invalid validation result with errors"""
        result = ValidationResult(
            is_valid=False,
            valid_fields=["medicine_name"],
            invalid_fields=["dosage"],
            errors=["Dosage field is missing"]
        )
        assert result.is_valid is False
        assert len(result.errors) == 1


class TestSerializationRoundTrip:
    """Tests for model serialization and deserialization"""
    
    def test_hospital_configuration_round_trip(self):
        """Test HospitalConfiguration serialization round-trip (Property 35)"""
        original = HospitalConfiguration(
            hospital_id="hosp_123",
            hospital_name="Test Hospital",
            version="1.0",
            sections=[
                SectionDefinition(
                    section_id="patient_details",
                    section_label="Patient Details",
                    display_order=1,
                    fields=[
                        FieldDefinition(
                            field_name="patient_name",
                            display_label="Name",
                            field_type=FieldType.TEXT,
                            required=True,
                            display_order=1,
                            description="Patient name",
                            max_length=100
                        )
                    ]
                )
            ]
        )
        
        # Serialize to JSON
        json_str = original.model_dump_json()
        
        # Deserialize back
        restored = HospitalConfiguration.model_validate_json(json_str)
        
        # Verify equivalence
        assert restored.hospital_id == original.hospital_id
        assert restored.hospital_name == original.hospital_name
        assert restored.version == original.version
        assert len(restored.sections) == len(original.sections)
        assert restored.sections[0].section_id == original.sections[0].section_id
        assert len(restored.sections[0].fields) == len(original.sections[0].fields)
        assert restored.sections[0].fields[0].field_name == original.sections[0].fields[0].field_name
    
    def test_prescription_data_round_trip(self):
        """Test PrescriptionData serialization round-trip (Property 29)"""
        original = PrescriptionData(
            sections=[
                ExtractedSection(
                    section_id="medications",
                    fields=[
                        ExtractedField(
                            field_name="medicine_name",
                            value="Amoxicillin",
                            confidence=0.95,
                            source_text="prescribing Amoxicillin"
                        )
                    ]
                )
            ],
            processing_time_ms=3500,
            request_id="req_123"
        )
        
        # Serialize to JSON
        json_str = original.model_dump_json()
        
        # Deserialize back
        restored = PrescriptionData.model_validate_json(json_str)
        
        # Verify equivalence
        assert len(restored.sections) == len(original.sections)
        assert restored.sections[0].section_id == original.sections[0].section_id
        assert len(restored.sections[0].fields) == len(original.sections[0].fields)
        assert restored.sections[0].fields[0].field_name == original.sections[0].fields[0].field_name
        assert restored.sections[0].fields[0].value == original.sections[0].fields[0].value
        assert restored.sections[0].fields[0].confidence == original.sections[0].fields[0].confidence
        assert restored.processing_time_ms == original.processing_time_ms
        assert restored.request_id == original.request_id
