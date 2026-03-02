"""
Bedrock Medical Extraction Data Models

This module defines Pydantic models for the Bedrock medical extraction feature.
These models ensure type safety and validation for medical entity extraction,
hospital configurations, and prescription data.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
from datetime import datetime


class EntityType(str, Enum):
    """Medical entity types from Comprehend Medical"""
    MEDICATION = "MEDICATION"
    DOSAGE = "DOSAGE"
    FREQUENCY = "FREQUENCY"
    DURATION = "DURATION"
    CONDITION = "CONDITION"
    PROCEDURE = "PROCEDURE"
    ANATOMY = "ANATOMY"
    TEST_NAME = "TEST_NAME"
    TREATMENT_NAME = "TREATMENT_NAME"


class MedicalEntity(BaseModel):
    """Structured medical entity from Comprehend Medical"""
    model_config = ConfigDict(use_enum_values=True)
    
    entity_type: EntityType
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    begin_offset: int
    end_offset: int
    attributes: Optional[List[Dict[str, Any]]] = None


class FieldType(str, Enum):
    """Supported form field types"""
    TEXT = "text"
    NUMBER = "number"
    DROPDOWN = "dropdown"
    MULTILINE = "multiline"


class FieldDefinition(BaseModel):
    """Definition of a single form field"""
    model_config = ConfigDict(use_enum_values=True)
    
    field_name: str
    display_label: str
    field_type: FieldType
    required: bool
    display_order: int
    description: str  # LLM extraction guidance
    max_length: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    options: Optional[List[str]] = None  # For dropdown
    placeholder: Optional[str] = None
    unit: Optional[str] = None
    rows: Optional[int] = None  # For multiline


class SectionDefinition(BaseModel):
    """Definition of a form section"""
    section_id: str
    section_label: str
    display_order: int
    repeatable: bool = False
    fields: List[FieldDefinition]


class HospitalConfiguration(BaseModel):
    """Complete hospital form configuration"""
    hospital_id: str
    hospital_name: str
    version: str
    sections: List[SectionDefinition]
    
    @field_validator('sections')
    @classmethod
    def validate_sections(cls, sections):
        """Ensure sections have unique IDs and valid ordering"""
        section_ids = [s.section_id for s in sections]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("Duplicate section IDs found")
        return sections
    
    @field_validator('sections')
    @classmethod
    def validate_field_names(cls, sections):
        """Ensure field names are unique within each section"""
        for section in sections:
            field_names = [f.field_name for f in section.fields]
            if len(field_names) != len(set(field_names)):
                raise ValueError(f"Duplicate field names in section {section.section_id}")
        return sections


class ExtractedField(BaseModel):
    """Single extracted field with confidence"""
    field_name: str
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_text: Optional[str] = None  # Original transcript snippet


class ExtractedSection(BaseModel):
    """Extracted data for a form section"""
    section_id: str
    fields: List[ExtractedField]


class PrescriptionData(BaseModel):
    """Complete prescription extraction result"""
    sections: List[ExtractedSection]
    processing_time_ms: int
    request_id: Optional[str] = None
    timestamp: Optional[datetime] = None


class FunctionDefinition(BaseModel):
    """Bedrock function definition"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema format


class FunctionCallResponse(BaseModel):
    """Parsed Bedrock function call response"""
    function_name: str
    arguments: Dict[str, Any]


class ValidationResult(BaseModel):
    """Result of function call validation"""
    is_valid: bool
    valid_fields: List[str]
    invalid_fields: List[str]
    errors: List[str]


class ErrorCode(str, Enum):
    """Standardized error codes"""
    COMPREHEND_UNAVAILABLE = "COMPREHEND_UNAVAILABLE"
    BEDROCK_UNAVAILABLE = "BEDROCK_UNAVAILABLE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    INVALID_INPUT = "INVALID_INPUT"


class ExtractionError(BaseModel):
    """Standardized error response"""
    model_config = ConfigDict(use_enum_values=True)
    
    status: Literal["error"]
    error_code: ErrorCode
    error_message: str
    request_id: str
    timestamp: str


class ExtractionRequest(BaseModel):
    """Request model for extraction API"""
    transcript: str = Field(min_length=1, max_length=10000)
    hospital_id: str
    request_id: Optional[str] = None
    
    @field_validator('transcript')
    @classmethod
    def validate_transcript(cls, v):
        """Ensure transcript is not empty or whitespace only"""
        if not v.strip():
            raise ValueError("Transcript cannot be empty or whitespace only")
        return v.strip()


class ExtractionResponse(BaseModel):
    """Success response model for extraction API"""
    status: Literal["success"]
    prescription_data: PrescriptionData
    request_id: str
