"""Consultation Service for retrieving and formatting consultation data"""
import json
import logging
from typing import List, Dict, Any, Optional
from aws_services.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class ConsultationService:
    """Service for managing consultation data retrieval and formatting"""
    
    @staticmethod
    def get_recent_consultations(user_id: str, db_manager: DatabaseManager, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve recent consultations for a user
        
        A consultation is defined as a transcription record with an optionally associated prescription.
        Prescriptions are joined by matching user_id and temporal proximity (within 1 hour).
        
        Args:
            user_id: ID of the authenticated user
            db_manager: DatabaseManager instance for database access
            limit: Maximum number of consultations to retrieve (default: 10, max: 50)
            
        Returns:
            List of consultation dictionaries with fields:
                - consultation_id: transcription_id
                - patient_name: extracted from medical_entities or prescription
                - patient_initials: generated from patient_name
                - status: transcription status (COMPLETED, IN_PROGRESS, FAILED)
                - created_at: ISO 8601 timestamp
                - has_prescription: boolean indicating if prescription exists
                - prescription_id: prescription_id if exists, else None
                - transcript_preview: first 100 characters of transcript
        """
        # Validate and cap limit
        limit = max(1, min(limit, 50))
        
        # SQL query to join transcriptions with prescriptions
        query = """
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
        """
        
        try:
            results = db_manager.execute_with_retry(query, (user_id, limit))
            
            if not results:
                return []
            
            consultations = []
            for row in results:
                consultation = ConsultationService._format_consultation(row)
                consultations.append(consultation)
            
            return consultations
            
        except Exception as e:
            logger.error(f"Failed to retrieve consultations for user {user_id}: {str(e)}")
            raise
    
    @staticmethod
    def _format_consultation(row: tuple) -> Dict[str, Any]:
        """
        Format a database row into a consultation dictionary
        
        Args:
            row: Database result row tuple
            
        Returns:
            Formatted consultation dictionary
        """
        (transcription_id, user_id, transcript_text, status, medical_entities_json,
         created_at, prescription_id, prescription_patient_name, medications) = row
        
        # Parse medical_entities JSONB
        medical_entities = []
        if medical_entities_json:
            try:
                if isinstance(medical_entities_json, str):
                    medical_entities = json.loads(medical_entities_json)
                else:
                    medical_entities = medical_entities_json
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse medical_entities for transcription {transcription_id}: {str(e)}")
                medical_entities = []
        
        # Extract patient name
        patient_name = ConsultationService._extract_patient_name(
            prescription_patient_name, medical_entities
        )
        
        # Generate patient initials
        patient_initials = ConsultationService._generate_initials(patient_name)
        
        # Create transcript preview (first 100 characters)
        transcript_preview = ""
        if transcript_text:
            transcript_preview = transcript_text[:100]
            if len(transcript_text) > 100:
                transcript_preview += "..."
        
        # Format consultation object
        consultation = {
            "consultation_id": str(transcription_id),
            "patient_name": patient_name,
            "patient_initials": patient_initials,
            "status": status,
            "created_at": created_at.isoformat() if created_at else None,
            "has_prescription": prescription_id is not None,
            "prescription_id": str(prescription_id) if prescription_id else None,
            "transcript_preview": transcript_preview
        }
        
        return consultation
    
    @staticmethod
    def _extract_patient_name(prescription_patient_name: Optional[str], 
                             medical_entities: List[Dict[str, Any]]) -> str:
        """
        Extract patient name from prescription or medical entities
        
        Priority:
        1. Prescription patient_name field
        2. PERSON entity with Category="PROTECTED_HEALTH_INFORMATION" from medical_entities
        3. "Unknown Patient" as fallback
        
        Args:
            prescription_patient_name: Patient name from prescription (if exists)
            medical_entities: List of medical entity dictionaries from Comprehend Medical
            
        Returns:
            Patient name string or "Unknown Patient"
        """
        # Check prescription patient_name first
        if prescription_patient_name and prescription_patient_name.strip():
            return prescription_patient_name.strip()
        
        # Check medical_entities for PERSON entities
        if medical_entities:
            for entity in medical_entities:
                if (entity.get("Category") == "PROTECTED_HEALTH_INFORMATION" and
                    entity.get("Type") == "NAME" and
                    entity.get("Text")):
                    return entity["Text"].strip()
        
        # Fallback to "Unknown Patient"
        return "Unknown Patient"
    
    @staticmethod
    def _generate_initials(patient_name: str) -> str:
        """
        Generate patient initials from name
        
        Logic:
        - Split name by whitespace
        - Take first character of first word and first character of last word
        - Convert to uppercase
        - If name is "Unknown Patient", return "?"
        
        Args:
            patient_name: Patient name string
            
        Returns:
            Patient initials (2 characters uppercase) or "?"
        """
        if not patient_name or patient_name == "Unknown Patient":
            return "?"
        
        # Split name by whitespace and filter empty strings
        name_parts = [part for part in patient_name.split() if part]
        
        if not name_parts:
            return "?"
        
        if len(name_parts) == 1:
            # Single name: use first character twice or just first character
            return name_parts[0][0].upper()
        
        # Multiple parts: first char of first word + first char of last word
        first_initial = name_parts[0][0].upper()
        last_initial = name_parts[-1][0].upper()
        
        return first_initial + last_initial
