"""Extraction Pipeline for Medical Prescription Data"""
import logging
import time
import uuid
from typing import Optional
from datetime import datetime
from aws_services.comprehend_manager import ComprehendManager
from aws_services.bedrock_client import BedrockClient
from aws_services.config_manager import ConfigManager, ConfigurationNotFoundError
from aws_services.validation_layer import ValidationLayer
from models.bedrock_extraction import PrescriptionData, ExtractionRequest

logger = logging.getLogger(__name__)


class ExtractionPipeline:
    """Orchestrates the complete medical prescription extraction workflow"""
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize extraction pipeline
        
        Args:
            config_manager: ConfigManager instance for loading configurations
        """
        self.config_manager = config_manager
        
        # Initialize AWS service clients
        comprehend_region = config_manager.get('aws_comprehend_region')
        self.comprehend_manager = ComprehendManager(comprehend_region)
        
        bedrock_region = config_manager.get('bedrock_region')
        bedrock_model_id = config_manager.get('bedrock_model_id')
        self.bedrock_client = BedrockClient(bedrock_region, bedrock_model_id)
        
        # Initialize validation layer
        self.validation_layer = ValidationLayer()
        
        logger.info("Extraction pipeline initialized")
    
    def extract_prescription_data(
        self,
        transcript: str,
        hospital_id: str,
        request_id: Optional[str] = None
    ) -> Optional[PrescriptionData]:
        """
        Main extraction method that coordinates all steps
        
        Args:
            transcript: Raw transcript text
            hospital_id: Hospital identifier for configuration lookup
            request_id: Optional request ID for tracking
            
        Returns:
            PrescriptionData with extracted fields and confidence scores or None on error
            
        Raises:
            ConfigurationNotFoundError: When hospital config is invalid
        """
        start_time = time.time()
        
        # Generate request ID if not provided
        if not request_id:
            request_id = f"req_{uuid.uuid4().hex[:12]}"
        
        logger.info(f"Starting extraction pipeline for request {request_id}, hospital {hospital_id}")
        
        try:
            # Step 1: Extract medical entities using Comprehend Medical
            logger.info(f"[{request_id}] Step 1: Extracting medical entities")
            entities = self.comprehend_manager.extract_entities_structured(transcript)
            
            if entities is None:
                logger.error(f"[{request_id}] Failed to extract medical entities")
                return None
            
            logger.info(f"[{request_id}] Extracted {len(entities)} medical entities")
            
            # Step 2: Load hospital configuration
            logger.info(f"[{request_id}] Step 2: Loading hospital configuration")
            try:
                hospital_config = self.config_manager.load_hospital_configuration(hospital_id)
            except ConfigurationNotFoundError:
                logger.warning(f"[{request_id}] Hospital config not found, using default")
                hospital_config = self.config_manager.get_default_hospital_configuration()
            
            logger.info(f"[{request_id}] Loaded config for '{hospital_config.hospital_name}'")
            
            # Step 3: Generate prescription data using Bedrock
            logger.info(f"[{request_id}] Step 3: Generating prescription data with Bedrock")
            function_response = self.bedrock_client.generate_prescription_data(
                transcript=transcript,
                entities=entities,
                hospital_config=hospital_config
            )
            
            if not function_response:
                logger.warning(f"[{request_id}] No function calls returned from Bedrock")
                return self._create_empty_prescription_data(start_time, request_id)
            
            logger.info(f"[{request_id}] Received function calls from Bedrock")
            
            # Step 4: Validate function call structure
            logger.info(f"[{request_id}] Step 4: Validating function call structure")
            validation_result = self.validation_layer.validate_function_call(
                function_response.arguments,
                hospital_config
            )
            
            if not validation_result.is_valid:
                logger.warning(
                    f"[{request_id}] Validation errors: {validation_result.errors}. "
                    f"Proceeding with partial data."
                )
            
            # Step 5: Format prescription data
            logger.info(f"[{request_id}] Step 5: Formatting prescription data")
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            prescription_data = self.validation_layer.format_prescription_data(
                function_calls=function_response.arguments,
                hospital_config=hospital_config,
                processing_time_ms=processing_time_ms,
                request_id=request_id
            )
            
            # Add timestamp
            prescription_data.timestamp = datetime.utcnow()
            
            logger.info(
                f"[{request_id}] Extraction complete: {len(prescription_data.sections)} sections, "
                f"{processing_time_ms}ms"
            )
            
            return prescription_data
            
        except Exception as e:
            logger.error(f"[{request_id}] Extraction pipeline failed: {str(e)}", exc_info=True)
            return None
    
    def _create_empty_prescription_data(
        self,
        start_time: float,
        request_id: str
    ) -> PrescriptionData:
        """
        Create empty prescription data when extraction fails
        
        Args:
            start_time: Pipeline start time
            request_id: Request ID
            
        Returns:
            Empty PrescriptionData object
        """
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return PrescriptionData(
            sections=[],
            processing_time_ms=processing_time_ms,
            request_id=request_id,
            timestamp=datetime.utcnow()
        )
    
    def validate_request(self, request: ExtractionRequest) -> tuple[bool, Optional[str]]:
        """
        Validate extraction request
        
        Args:
            request: ExtractionRequest to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Transcript validation (already done by Pydantic, but double-check)
        if not request.transcript or len(request.transcript.strip()) == 0:
            return False, "Transcript cannot be empty"
        
        if len(request.transcript) > 10000:
            return False, "Transcript exceeds maximum length of 10000 characters"
        
        # Hospital ID validation
        if not request.hospital_id or len(request.hospital_id.strip()) == 0:
            return False, "Hospital ID cannot be empty"
        
        return True, None
