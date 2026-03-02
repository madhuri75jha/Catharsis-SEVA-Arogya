"""Comprehend Manager for AWS Comprehend Medical"""
import logging
import time
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError
from .base_client import BaseAWSClient
from models.bedrock_extraction import MedicalEntity, EntityType

logger = logging.getLogger(__name__)


class ComprehendUnavailableError(Exception):
    """Raised when Comprehend Medical service is unavailable"""
    pass


class ComprehendRateLimitError(Exception):
    """Raised when Comprehend Medical rate limit is exceeded"""
    pass


class ComprehendManager(BaseAWSClient):
    """Manages AWS Comprehend Medical operations for medical entity extraction"""
    
    # Minimum confidence score for entity filtering
    MIN_CONFIDENCE_SCORE = 0.5
    
    # Retry configuration for rate limits
    MAX_RETRIES = 3
    RETRY_DELAYS = [1.0, 2.0, 4.0]  # Exponential backoff: 1s, 2s, 4s
    
    # Mapping from Comprehend Medical types to our EntityType enum
    TYPE_MAPPING = {
        'BRAND_NAME': EntityType.MEDICATION,
        'GENERIC_NAME': EntityType.MEDICATION,
        'DX_NAME': EntityType.CONDITION,
        'PROCEDURE_NAME': EntityType.PROCEDURE,
        'TEST_NAME': EntityType.TEST_NAME,
        'TREATMENT_NAME': EntityType.TREATMENT_NAME,
        'SYSTEM_ORGAN_SITE': EntityType.ANATOMY,
        'DIRECTION': EntityType.ANATOMY,
        'DOSAGE': EntityType.DOSAGE,
        'FREQUENCY': EntityType.FREQUENCY,
        'DURATION': EntityType.DURATION,
    }
    
    def __init__(self, region: str):
        """
        Initialize Comprehend Manager
        
        Args:
            region: AWS region
        """
        super().__init__('comprehendmedical', region)
        logger.info("Comprehend manager initialized")
    
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
            ComprehendRateLimitError: If rate limit exceeded after all retries
            ComprehendUnavailableError: If service is unavailable
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
                        raise ComprehendRateLimitError(
                            f"Rate limit exceeded after {self.MAX_RETRIES} retries"
                        ) from e
                
                # Check if service is unavailable
                elif error_code in ['ServiceUnavailable', 'InternalServerError']:
                    logger.error(f"Comprehend Medical service unavailable. Request ID: {request_id}")
                    raise ComprehendUnavailableError(
                        "Comprehend Medical service is temporarily unavailable"
                    ) from e
                
                # For other errors, raise immediately
                else:
                    logger.error(f"Comprehend Medical error: {error_code}. Request ID: {request_id}")
                    raise
        
        # Should not reach here, but just in case
        if last_error:
            raise ComprehendRateLimitError(
                f"Rate limit exceeded after {self.MAX_RETRIES} retries"
            ) from last_error
    
    def extract_entities(self, text: str) -> Optional[List[Dict[str, Any]]]:
        """
        Extract medical entities from text using Comprehend Medical
        
        Args:
            text: Medical text to analyze
            
        Returns:
            List of extracted entities with confidence scores or None on error
        """
        start_time = time.time()
        
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for entity extraction")
                return []
            
            self._log_operation('extract_entities', text_length=len(text))
            
            # Call Comprehend Medical with retry logic
            def _detect_entities():
                return self.client.detect_entities_v2(Text=text)
            
            response = self._call_with_retry(_detect_entities)
            
            # Extract and structure entities
            entities = []
            raw_entities = response.get('Entities', [])
            
            for entity in raw_entities:
                # Filter by confidence score
                confidence = entity.get('Score', 0.0)
                if confidence < self.MIN_CONFIDENCE_SCORE:
                    continue
                
                # Structure entity data
                entity_data = {
                    'text': entity.get('Text'),
                    'category': entity.get('Category'),
                    'type': entity.get('Type'),
                    'confidence': confidence,
                    'begin_offset': entity.get('BeginOffset'),
                    'end_offset': entity.get('EndOffset')
                }
                
                # Add attributes if available (dosage, frequency, etc.)
                attributes = []
                for attr in entity.get('Attributes', []):
                    attr_confidence = attr.get('Score', 0.0)
                    if attr_confidence >= self.MIN_CONFIDENCE_SCORE:
                        attributes.append({
                            'type': attr.get('Type'),
                            'text': attr.get('Text'),
                            'confidence': attr_confidence
                        })
                
                if attributes:
                    entity_data['attributes'] = attributes
                
                entities.append(entity_data)
            
            duration_ms = (time.time() - start_time) * 1000
            self._log_success('extract_entities', duration_ms=duration_ms, entity_count=len(entities))
            logger.info(f"Extracted {len(entities)} medical entities from text")
            
            return entities
            
        except (ComprehendUnavailableError, ComprehendRateLimitError) as e:
            # Log and re-raise our custom exceptions
            self._log_error('extract_entities', e)
            logger.error(f"Comprehend Medical error: {str(e)}")
            return None
            
        except ClientError as e:
            self._log_error('extract_entities', e)
            error_code = e.response['Error']['Code']
            request_id = e.response.get('ResponseMetadata', {}).get('RequestId', 'unknown')
            logger.error(f"Failed to extract medical entities: {error_code}. Request ID: {request_id}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error extracting medical entities: {str(e)}")
            return None
    
    def extract_entities_structured(self, text: str) -> Optional[List[MedicalEntity]]:
        """
        Extract medical entities and return as structured MedicalEntity objects
        
        Args:
            text: Medical text to analyze
            
        Returns:
            List of MedicalEntity objects or None on error
        """
        raw_entities = self.extract_entities(text)
        
        if raw_entities is None:
            return None
        
        structured_entities = []
        
        for entity in raw_entities:
            # Map Comprehend type to our EntityType enum
            entity_type_str = entity.get('type', '')
            entity_type = self.TYPE_MAPPING.get(entity_type_str, EntityType.CONDITION)
            
            # Convert attributes to dict format
            attributes = entity.get('attributes', [])
            
            try:
                medical_entity = MedicalEntity(
                    entity_type=entity_type,
                    text=entity.get('text', ''),
                    confidence=entity.get('confidence', 0.0),
                    begin_offset=entity.get('begin_offset', 0),
                    end_offset=entity.get('end_offset', 0),
                    attributes=attributes if attributes else None
                )
                structured_entities.append(medical_entity)
            except Exception as e:
                logger.warning(f"Failed to create MedicalEntity from {entity}: {e}")
                continue
        
        logger.info(f"Created {len(structured_entities)} structured MedicalEntity objects")
        return structured_entities
    
    def categorize_entities_by_type(self, entities: List[MedicalEntity]) -> Dict[EntityType, List[MedicalEntity]]:
        """
        Categorize MedicalEntity objects by their detailed type
        
        Args:
            entities: List of MedicalEntity objects
            
        Returns:
            Dictionary with entities grouped by EntityType
        """
        categorized = {entity_type: [] for entity_type in EntityType}
        
        for entity in entities:
            categorized[entity.entity_type].append(entity)
        
        logger.info(f"Categorized {len(entities)} entities by type")
        
        return categorized
    
    def categorize_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorize extracted entities by type
        
        Args:
            entities: List of extracted entities
            
        Returns:
            Dictionary with entities grouped by category
        """
        categorized = {
            'medications': [],
            'conditions': [],
            'procedures': [],
            'anatomy': [],
            'test_treatment_procedure': [],
            'other': []
        }
        
        for entity in entities:
            category = entity.get('category', '').lower()
            
            if category == 'medication':
                categorized['medications'].append(entity)
            elif category == 'medical_condition':
                categorized['conditions'].append(entity)
            elif category == 'procedure':
                categorized['procedures'].append(entity)
            elif category == 'anatomy':
                categorized['anatomy'].append(entity)
            elif category == 'test_treatment_procedure':
                categorized['test_treatment_procedure'].append(entity)
            else:
                categorized['other'].append(entity)
        
        logger.info(f"Categorized entities: {sum(len(v) for v in categorized.values())} total")
        
        return categorized
    
    def extract_medications(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract only medication entities from text
        
        Args:
            text: Medical text to analyze
            
        Returns:
            List of medication entities
        """
        entities = self.extract_entities(text)
        
        if entities is None:
            return []
        
        medications = [e for e in entities if e.get('category') == 'MEDICATION']
        
        logger.info(f"Extracted {len(medications)} medication entities")
        
        return medications
