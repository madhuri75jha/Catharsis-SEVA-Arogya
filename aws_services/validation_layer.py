"""Validation Layer for Bedrock Function Call Responses"""
import logging
import re
from typing import Dict, Any, List
from models.bedrock_extraction import (
    ValidationResult, FieldDefinition, HospitalConfiguration,
    ExtractedField, ExtractedSection, PrescriptionData
)

logger = logging.getLogger(__name__)


class ValidationLayer:
    """Validates and normalizes extracted prescription data from Bedrock"""
    
    def __init__(self):
        """Initialize validation layer"""
        logger.info("Validation layer initialized")
    
    def validate_function_call(
        self,
        function_calls: Dict[str, Any],
        hospital_config: HospitalConfiguration
    ) -> ValidationResult:
        """
        Validate function call structure matches expected fields from hospital config
        
        Args:
            function_calls: Dictionary of function calls from Bedrock
            hospital_config: Hospital configuration with expected field definitions
            
        Returns:
            ValidationResult with valid/invalid fields and errors
        """
        valid_fields = []
        invalid_fields = []
        errors = []
        
        # Validate each section's function call
        for section in hospital_config.sections:
            function_name = f"fill_{section.section_id}"
            
            if function_name not in function_calls:
                # Section not provided - check if any required fields
                required_fields = [f.field_name for f in section.fields if f.required]
                if required_fields:
                    errors.append(f"Missing required section: {section.section_label}")
                    invalid_fields.extend(required_fields)
                continue
            
            function_data = function_calls[function_name]
            
            # Handle repeatable sections (arrays)
            if section.repeatable:
                if 'items' not in function_data or not isinstance(function_data['items'], list):
                    errors.append(f"Section {section.section_label} should be an array")
                    invalid_fields.extend([f.field_name for f in section.fields])
                    continue
                
                # Validate each item in the array
                for idx, item in enumerate(function_data['items']):
                    self._validate_section_fields(
                        item, section.fields, valid_fields, invalid_fields, errors,
                        prefix=f"{section.section_id}[{idx}]"
                    )
            else:
                # Validate single section
                self._validate_section_fields(
                    function_data, section.fields, valid_fields, invalid_fields, errors,
                    prefix=section.section_id
                )
        
        is_valid = len(errors) == 0 and len(invalid_fields) == 0
        
        logger.info(f"Validation result: valid={is_valid}, valid_fields={len(valid_fields)}, invalid_fields={len(invalid_fields)}")
        
        return ValidationResult(
            is_valid=is_valid,
            valid_fields=valid_fields,
            invalid_fields=invalid_fields,
            errors=errors
        )
    
    def _validate_section_fields(
        self,
        data: Dict[str, Any],
        field_definitions: List[FieldDefinition],
        valid_fields: List[str],
        invalid_fields: List[str],
        errors: List[str],
        prefix: str = ""
    ):
        """
        Validate fields in a section
        
        Args:
            data: Data dictionary for the section
            field_definitions: Expected field definitions
            valid_fields: List to append valid field names
            invalid_fields: List to append invalid field names
            errors: List to append error messages
            prefix: Prefix for field names in error messages
        """
        for field_def in field_definitions:
            field_name = field_def.field_name
            full_field_name = f"{prefix}.{field_name}" if prefix else field_name
            
            # Check if required field is present
            if field_def.required and (field_name not in data or data[field_name] is None or data[field_name] == ""):
                errors.append(f"Required field missing: {full_field_name}")
                invalid_fields.append(full_field_name)
                continue
            
            # Skip validation if field not provided and not required
            if field_name not in data or data[field_name] is None:
                continue
            
            value = data[field_name]
            
            # Validate field type
            if field_def.field_type == "number":
                if not isinstance(value, (int, float)):
                    try:
                        float(value)
                    except (ValueError, TypeError):
                        errors.append(f"Field {full_field_name} should be a number")
                        invalid_fields.append(full_field_name)
                        continue
            
            elif field_def.field_type == "dropdown":
                if field_def.options and value not in field_def.options:
                    errors.append(f"Field {full_field_name} has invalid option: {value}")
                    invalid_fields.append(full_field_name)
                    continue
            
            # Field is valid
            valid_fields.append(full_field_name)
    
    def normalize_dosage(self, dosage_str: str) -> str:
        """
        Normalize dosage to standard format
        
        Args:
            dosage_str: Dosage string in various formats
            
        Returns:
            Normalized dosage string
            
        Examples:
            "500 milligrams" -> "500mg"
            "2 tablets" -> "2 tablets"
            "10 milliliters" -> "10ml"
            "5 mcg" -> "5mcg"
        """
        if not dosage_str:
            return dosage_str
        
        dosage_str = dosage_str.strip()
        
        # Normalize common unit variations
        replacements = {
            r'\bmilligrams?\b': 'mg',
            r'\bmilliliters?\b': 'ml',
            r'\bmicrograms?\b': 'mcg',
            r'\bgrams?\b': 'g',
            r'\bliters?\b': 'l',
            r'\btablets?\b': 'tablets',
            r'\bcapsules?\b': 'capsules',
            r'\bteaspoons?\b': 'tsp',
            r'\btablespoons?\b': 'tbsp',
        }
        
        normalized = dosage_str
        for pattern, replacement in replacements.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Remove space before unit if it's a standard abbreviation
        normalized = re.sub(r'(\d+)\s+(mg|ml|mcg|g|l|tsp|tbsp)\b', r'\1\2', normalized, flags=re.IGNORECASE)
        
        logger.debug(f"Normalized dosage: '{dosage_str}' -> '{normalized}'")
        
        return normalized
    
    def format_prescription_data(
        self,
        function_calls: Dict[str, Any],
        hospital_config: HospitalConfiguration,
        processing_time_ms: int,
        request_id: str = None
    ) -> PrescriptionData:
        """
        Format validated function call data into PrescriptionData structure
        
        Args:
            function_calls: Validated function calls from Bedrock
            hospital_config: Hospital configuration
            processing_time_ms: Total processing time
            request_id: Optional request ID
            
        Returns:
            PrescriptionData with extracted sections and fields
        """
        sections = []
        
        for section_def in hospital_config.sections:
            function_name = f"fill_{section_def.section_id}"
            
            if function_name not in function_calls:
                continue
            
            function_data = function_calls[function_name]
            
            # Handle repeatable sections
            if section_def.repeatable:
                items = function_data.get('items', [])
                for idx, item in enumerate(items):
                    section_fields = self._extract_fields(item, section_def.fields)
                    if section_fields:
                        sections.append(ExtractedSection(
                            section_id=f"{section_def.section_id}_{idx}",
                            fields=section_fields
                        ))
            else:
                section_fields = self._extract_fields(function_data, section_def.fields)
                if section_fields:
                    sections.append(ExtractedSection(
                        section_id=section_def.section_id,
                        fields=section_fields
                    ))
        
        return PrescriptionData(
            sections=sections,
            processing_time_ms=processing_time_ms,
            request_id=request_id
        )
    
    def _extract_fields(
        self,
        data: Dict[str, Any],
        field_definitions: List[FieldDefinition]
    ) -> List[ExtractedField]:
        """
        Extract fields from data dictionary
        
        Args:
            data: Data dictionary
            field_definitions: Field definitions
            
        Returns:
            List of ExtractedField objects
        """
        fields = []
        
        for field_def in field_definitions:
            field_name = field_def.field_name
            
            if field_name not in data or data[field_name] is None:
                continue
            
            value = str(data[field_name])
            
            # Normalize dosage fields
            if 'dose' in field_name.lower() or 'dosage' in field_name.lower():
                value = self.normalize_dosage(value)
            
            # Create extracted field with default confidence
            # (Bedrock doesn't provide per-field confidence, so we use 1.0)
            fields.append(ExtractedField(
                field_name=field_name,
                value=value,
                confidence=1.0,  # Bedrock function calls don't have per-field confidence
                source_text=None  # Could be enhanced to track source
            ))
        
        return fields
