"""Bedrock Client for AWS Bedrock Runtime"""
import logging
import json
import time
from enum import Enum
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError
from .base_client import BaseAWSClient
from models.bedrock_extraction import (
    MedicalEntity, FieldDefinition, FunctionDefinition,
    FunctionCallResponse, HospitalConfiguration
)

logger = logging.getLogger(__name__)


class BedrockUnavailableError(Exception):
    """Raised when Bedrock service is unavailable"""
    pass


class BedrockRateLimitError(Exception):
    """Raised when Bedrock rate limit is exceeded"""
    pass


class BedrockClient(BaseAWSClient):
    """Manages AWS Bedrock operations for medical data extraction using function calling"""
    
    # Retry configuration for rate limits
    MAX_RETRIES = 3
    RETRY_DELAYS = [1.0, 2.0, 4.0]  # Exponential backoff: 1s, 2s, 4s
    
    def __init__(self, region: str, model_id: str):
        """
        Initialize Bedrock Client
        
        Args:
            region: AWS region
            model_id: Bedrock model identifier (e.g., 'anthropic.claude-3-sonnet-20240229-v1:0')
        """
        super().__init__('bedrock-runtime', region)
        self.model_id = model_id
        logger.info(f"Bedrock client initialized with model: {model_id}")
        
        # Validate model supports function calling at initialization
        self._validate_function_calling_support()
    
    def _validate_function_calling_support(self):
        """
        Validate that the configured model supports function calling
        
        Raises:
            ValueError: If model doesn't support function calling
        """
        if not self.model_id or not isinstance(self.model_id, str):
            raise ValueError(
                "BEDROCK_MODEL_ID is not configured. Set BEDROCK_MODEL_ID in environment/secrets."
            )

        # Models known to support tool/function calling in this code path.
        supported_models = [
            'anthropic.claude-3-sonnet',
            'anthropic.claude-3-opus',
            'anthropic.claude-3-haiku',
            'anthropic.claude-3-5-sonnet',
            'amazon.nova-lite',
            'amazon.nova-pro',
            'amazon.nova-micro',
        ]
        
        model_supports_functions = any(
            supported in self.model_id for supported in supported_models
        )
        
        if not model_supports_functions:
            error_msg = (
                f"Model '{self.model_id}' does not support function calling. "
                f"Please use a supported Claude 3/3.5 or Amazon Nova model."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Model '{self.model_id}' supports function calling")

    def _is_anthropic_model(self) -> bool:
        """Return True if configured model is Anthropic Claude."""
        return self.model_id.startswith("anthropic.")

    def _invoke_with_tools(self, prompt: str, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Invoke model with tool definitions.
        Uses InvokeModel for Anthropic and Converse API for Amazon Nova.
        """
        if self._is_anthropic_model():
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "tools": tools
            }
            response = self._call_with_retry(
                lambda: self.client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(request_body)
                )
            )
            return json.loads(response['body'].read())

        converse_tools = []
        for tool in tools:
            converse_tools.append({
                "toolSpec": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "inputSchema": {
                        "json": tool["input_schema"]
                    }
                }
            })

        response = self._call_with_retry(
            lambda: self.client.converse(
                modelId=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ],
                inferenceConfig={"maxTokens": 4096},
                toolConfig={"tools": converse_tools}
            )
        )
        return response

    def _extract_function_calls(self, response_body: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize tool/function calls from InvokeModel/Converse responses."""
        function_calls: Dict[str, Any] = {}

        if self._is_anthropic_model():
            for content_block in response_body.get('content', []):
                if content_block.get('type') == 'tool_use':
                    function_name = content_block.get('name')
                    function_input = content_block.get('input', {})
                    if function_name:
                        function_calls[function_name] = function_input
            return function_calls

        output_message = response_body.get("output", {}).get("message", {})
        for content_block in output_message.get("content", []):
            tool_use = content_block.get("toolUse")
            if not tool_use:
                continue
            function_name = tool_use.get("name")
            function_input = tool_use.get("input", {})
            if function_name:
                function_calls[function_name] = function_input

        return function_calls
    
    def _call_with_retry(self, operation_func, *args, **kwargs):
        """
        Call AWS operation with exponential backoff retry for rate limits
        
        Args:
            operation_func: Function to call
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result from operation_func
            
        Raises:
            BedrockRateLimitError: If rate limit exceeded after all retries
            BedrockUnavailableError: If service is unavailable
            ClientError: For other AWS errors
        """
        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                return operation_func(*args, **kwargs)
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                request_id = e.response.get('ResponseMetadata', {}).get('RequestId', 'unknown')
                
                # Check if it's a rate limit error
                if error_code in ['ThrottlingException', 'TooManyRequestsException']:
                    last_error = e
                    
                    if attempt < self.MAX_RETRIES - 1:
                        delay = self.RETRY_DELAYS[attempt]
                        logger.warning(
                            f"Rate limit exceeded (attempt {attempt + 1}/{self.MAX_RETRIES}), "
                            f"retrying in {delay}s. Request ID: {request_id}"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"Rate limit exceeded after {self.MAX_RETRIES} attempts. Request ID: {request_id}")
                        raise BedrockRateLimitError(
                            f"Rate limit exceeded after {self.MAX_RETRIES} retries"
                        ) from e
                
                # Check if service is unavailable
                elif error_code in ['ServiceUnavailable', 'InternalServerError']:
                    logger.error(f"Bedrock service unavailable. Request ID: {request_id}")
                    raise BedrockUnavailableError(
                        "Bedrock service is temporarily unavailable"
                    ) from e
                
                # For other errors, raise immediately
                else:
                    logger.error(f"Bedrock error: {error_code}. Request ID: {request_id}")
                    raise
        
        # Should not reach here, but just in case
        if last_error:
            raise BedrockRateLimitError(
                f"Rate limit exceeded after {self.MAX_RETRIES} retries"
            ) from last_error
    
    def _construct_prompt(
        self,
        transcript: str,
        entities: List[Any]
    ) -> str:
        """
        Build prompt with transcript and entity context for Bedrock
        
        Args:
            transcript: Original medical transcript
            entities: Extracted medical entities from Comprehend Medical
            
        Returns:
            Formatted prompt string
        """
        # Group entities by type for better context.
        # Accept entities in multiple shapes (Pydantic model, dict, or plain object)
        # so extraction does not fail on type coercion differences.
        entities_by_type = {}
        for entity in entities:
            entity_type = "UNKNOWN"
            text = ""

            if isinstance(entity, dict):
                raw_type = entity.get("entity_type") or entity.get("type")
                text = entity.get("text", "")
            else:
                raw_type = getattr(entity, "entity_type", None) or getattr(entity, "type", None)
                text = getattr(entity, "text", "")

            if isinstance(raw_type, Enum):
                entity_type = raw_type.value
            elif isinstance(raw_type, str) and raw_type.strip():
                entity_type = raw_type.strip().upper()

            text = str(text or "").strip()
            if not text:
                continue

            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(text)
        
        # Build entity context section
        entity_context = []
        if entities_by_type:
            entity_context.append("Extracted Medical Entities:")
            for entity_type, texts in entities_by_type.items():
                entity_context.append(f"- {entity_type}: {', '.join(texts)}")
        
        # Construct full prompt
        prompt = f"""You are a medical AI assistant helping to extract structured prescription information from a medical consultation transcript.

{chr(10).join(entity_context) if entity_context else ""}

Medical Consultation Transcript:
{transcript}

Please extract the prescription information from this transcript and fill in the provided function parameters. Use the field descriptions to guide your extraction. If information is not mentioned in the transcript, leave that field empty or use null."""
        
        return prompt
    
    def _build_function_schema(
        self,
        field_definitions: List[FieldDefinition]
    ) -> Dict[str, Any]:
        """
        Convert FieldDefinition objects to Bedrock function schema (JSON Schema format)
        
        Args:
            field_definitions: List of field definitions from hospital config
            
        Returns:
            JSON Schema dictionary for function parameters
        """
        properties = {}
        required_fields = []
        
        for field_def in field_definitions:
            # Build property schema based on field type
            prop_schema = {
                "description": field_def.description
            }
            
            # Map field type to JSON Schema type
            if field_def.field_type == "text" or field_def.field_type == "multiline":
                prop_schema["type"] = "string"
                if field_def.max_length:
                    prop_schema["maxLength"] = field_def.max_length
                if field_def.placeholder:
                    prop_schema["description"] += f" Example: {field_def.placeholder}"
            
            elif field_def.field_type == "number":
                prop_schema["type"] = "number"
                if field_def.min_value is not None:
                    prop_schema["minimum"] = field_def.min_value
                if field_def.max_value is not None:
                    prop_schema["maximum"] = field_def.max_value
            
            elif field_def.field_type == "dropdown":
                prop_schema["type"] = "string"
                if field_def.options:
                    prop_schema["enum"] = field_def.options
                    prop_schema["description"] += f" Valid options: {', '.join(field_def.options)}"
            
            properties[field_def.field_name] = prop_schema
            
            # Track required fields
            if field_def.required:
                required_fields.append(field_def.field_name)
        
        # Build complete schema
        schema = {
            "type": "object",
            "properties": properties
        }
        
        if required_fields:
            schema["required"] = required_fields
        
        return schema
    
    def generate_prescription_data(
        self,
        transcript: str,
        entities: List[Any],
        hospital_config: HospitalConfiguration
    ) -> Optional[FunctionCallResponse]:
        """
        Generate structured prescription data using Bedrock function calling
        
        Args:
            transcript: Original transcript for context
            entities: Extracted medical entities
            hospital_config: Hospital configuration with field definitions
            
        Returns:
            FunctionCallResponse with structured field data or None on error
            
        Raises:
            BedrockUnavailableError: Service unavailable
            BedrockRateLimitError: Rate limit exceeded
        """
        start_time = time.time()
        
        try:
            self._log_operation('generate_prescription_data', 
                              transcript_length=len(transcript),
                              entity_count=len(entities))
            
            # Build prompt
            prompt = self._construct_prompt(transcript, entities)
            
            # Build function definitions from hospital config
            # For simplicity, we'll create one function per section
            tools = []
            for section in hospital_config.sections:
                if section.repeatable:
                    # For repeatable sections (like medications), create array schema
                    item_schema = self._build_function_schema(section.fields)
                    function_schema = {
                        "type": "object",
                        "properties": {
                            "items": {
                                "type": "array",
                                "items": item_schema,
                                "description": f"List of {section.section_label}"
                            }
                        }
                    }
                else:
                    function_schema = self._build_function_schema(section.fields)
                
                tool = {
                    "name": f"fill_{section.section_id}",
                    "description": f"Fill in the {section.section_label} section of the prescription form",
                    "input_schema": function_schema
                }
                tools.append(tool)
            
            response_body = self._invoke_with_tools(prompt, tools)
            function_calls = self._extract_function_calls(response_body)
            
            duration_ms = (time.time() - start_time) * 1000
            self._log_success('generate_prescription_data', 
                            duration_ms=duration_ms,
                            function_call_count=len(function_calls))
            
            logger.info(f"Generated prescription data with {len(function_calls)} function calls")
            
            # Return combined function calls
            if function_calls:
                return FunctionCallResponse(
                    function_name="extract_prescription",
                    arguments=function_calls
                )
            else:
                logger.warning("No function calls in Bedrock response")
                return None
            
        except (BedrockUnavailableError, BedrockRateLimitError) as e:
            self._log_error('generate_prescription_data', e)
            logger.error(f"Bedrock error: {str(e)}")
            raise
            
        except ClientError as e:
            self._log_error('generate_prescription_data', e)
            error_code = e.response['Error']['Code']
            request_id = e.response.get('ResponseMetadata', {}).get('RequestId', 'unknown')
            logger.error(f"Failed to generate prescription data: {error_code}. Request ID: {request_id}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error generating prescription data: {str(e)}")
            raise
    
    def extract_prescription_sections(self, transcript: str) -> Optional[Dict[str, Any]]:
        """
        Extract prescription sections from transcript for prescription workflow
        
        Args:
            transcript: Medical consultation transcript
            
        Returns:
            Dictionary with section keys and content, or None on error
        """
        start_time = time.time()
        
        try:
            self._log_operation('extract_prescription_sections', 
                              transcript_length=len(transcript))
            
            # Build simplified prompt for section extraction
            prompt = f"""You are a medical AI assistant. Extract structured prescription information from the following consultation transcript.

Medical Consultation Transcript:
{transcript}

Extract the following sections:
1. Diagnosis: Primary and secondary diagnoses
2. Medications: List of medications with dosage, frequency, and duration
3. Instructions: Patient care instructions and precautions
4. Follow-up: Follow-up appointment recommendations
5. Lab Tests: Recommended laboratory tests (if any)
6. Referrals: Specialist referrals (if any)

Return the data in JSON format with keys matching the section names. If a section is not mentioned, use an empty string or null."""
            
            # Define function for extraction
            tools = [{
                "name": "extract_prescription_sections",
                "description": "Extract prescription sections from medical transcript",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "diagnosis": {
                            "type": "string",
                            "description": "Primary and secondary diagnoses"
                        },
                        "medications": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Medication name"},
                                    "dosage": {"type": "string", "description": "Dosage amount"},
                                    "frequency": {"type": "string", "description": "How often to take"},
                                    "duration": {"type": "string", "description": "How long to take"}
                                },
                                "required": ["name", "dosage", "frequency"]
                            },
                            "description": "List of prescribed medications"
                        },
                        "instructions": {
                            "type": "string",
                            "description": "Patient care instructions and precautions"
                        },
                        "follow_up": {
                            "type": "string",
                            "description": "Follow-up appointment recommendations"
                        },
                        "lab_tests": {
                            "type": "string",
                            "description": "Recommended laboratory tests"
                        },
                        "referrals": {
                            "type": "string",
                            "description": "Specialist referrals"
                        }
                    },
                    "required": ["diagnosis", "medications", "instructions"]
                }
            }]
            
            response_body = self._invoke_with_tools(prompt, tools)
            function_calls = self._extract_function_calls(response_body)
            
            duration_ms = (time.time() - start_time) * 1000
            self._log_success('extract_prescription_sections', 
                            duration_ms=duration_ms)
            
            # Extract the function call result
            if 'extract_prescription_sections' in function_calls:
                sections = function_calls['extract_prescription_sections']
                logger.info(f"Extracted prescription sections: {list(sections.keys())}")
                return sections
            else:
                logger.warning("No prescription sections extracted from Bedrock response")
                return None
            
        except (BedrockUnavailableError, BedrockRateLimitError) as e:
            self._log_error('extract_prescription_sections', e)
            logger.error(f"Bedrock error: {str(e)}")
            raise
            
        except ClientError as e:
            self._log_error('extract_prescription_sections', e)
            error_code = e.response['Error']['Code']
            request_id = e.response.get('ResponseMetadata', {}).get('RequestId', 'unknown')
            logger.error(f"Failed to extract prescription sections: {error_code}. Request ID: {request_id}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error extracting prescription sections: {str(e)}")
            raise
