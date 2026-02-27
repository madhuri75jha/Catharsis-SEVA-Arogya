"""Comprehend Manager for AWS Comprehend Medical"""
import logging
import time
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError
from .base_client import BaseAWSClient

logger = logging.getLogger(__name__)


class ComprehendManager(BaseAWSClient):
    """Manages AWS Comprehend Medical operations for medical entity extraction"""
    
    # Minimum confidence score for entity filtering
    MIN_CONFIDENCE_SCORE = 0.5
    
    def __init__(self, region: str):
        """
        Initialize Comprehend Manager
        
        Args:
            region: AWS region
        """
        super().__init__('comprehendmedical', region)
        logger.info("Comprehend manager initialized")
    
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
            
            # Call Comprehend Medical to detect entities
            response = self.client.detect_entities_v2(
                Text=text
            )
            
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
            
        except ClientError as e:
            self._log_error('extract_entities', e)
            error_code = e.response['Error']['Code']
            logger.error(f"Failed to extract medical entities: {error_code}")
            
            # Return empty list on error so transcript can still be returned
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error extracting medical entities: {str(e)}")
            return None
    
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
