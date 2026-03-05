"""Consultation Service for retrieving and formatting consultation data"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from aws_services.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class ConsultationService:
    """Service for managing consultation data retrieval and formatting"""
    
    @staticmethod
    def get_recent_consultations(
        user_id: str,
        db_manager: DatabaseManager,
        limit: int = 10,
        search: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve recent consultations for a user
        
        A consultation is defined as a consultation record that can have multiple
        transcription clips. Prescriptions are joined by consultation_id first,
        with a legacy fallback to temporal proximity for older rows.
        
        Args:
            user_id: ID of the authenticated user
            db_manager: DatabaseManager instance for database access
            limit: Maximum number of consultations to retrieve (default: 10, max: 50)
            
        Returns:
            List of consultation dictionaries with fields:
                - consultation_id: consultation_id
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
        
        # SQL query to join consultations with aggregated clip transcript + prescriptions
        query = """
        SELECT 
            c.consultation_id,
            c.user_id,
            COALESCE(NULLIF(c.merged_transcript_text, ''), clips.merged_transcript, '') AS transcript_text,
            c.status,
            clips.medical_entities,
            c.created_at,
            p.prescription_id,
            p.patient_name,
            p.medications,
            p.sections,
            p.state
        FROM consultations c
        LEFT JOIN LATERAL (
            SELECT
                COALESCE(
                    STRING_AGG(NULLIF(TRIM(t.transcript_text), ''), ' ' ORDER BY t.clip_order, t.created_at),
                    ''
                ) AS merged_transcript,
                (
                    SELECT t2.medical_entities
                    FROM transcriptions t2
                    WHERE t2.consultation_id = c.consultation_id
                      AND t2.user_id = c.user_id
                      AND t2.medical_entities IS NOT NULL
                    ORDER BY t2.updated_at DESC, t2.created_at DESC
                    LIMIT 1
                ) AS medical_entities
            FROM transcriptions t
            WHERE t.consultation_id = c.consultation_id
              AND t.user_id = c.user_id
        ) clips ON TRUE
        LEFT JOIN LATERAL (
            SELECT p1.prescription_id, p1.patient_name, p1.medications, p1.sections, p1.state
            FROM prescriptions p1
            WHERE p1.user_id = c.user_id
              AND (
                p1.consultation_id = c.consultation_id
                OR (
                  p1.consultation_id IS NULL
                  AND p1.created_at >= c.created_at
                  AND p1.created_at <= c.created_at + INTERVAL '1 hour'
                )
              )
            ORDER BY
              CASE WHEN p1.consultation_id = c.consultation_id THEN 0 ELSE 1 END,
              p1.created_at DESC
            LIMIT 1
        ) p ON TRUE
        WHERE {where_clause}
        ORDER BY c.created_at DESC
        LIMIT %s
        """
        
        try:
            where_clauses = ["c.user_id = %s"]
            params: List[Any] = [user_id]

            if status:
                where_clauses.append("UPPER(c.status) = %s")
                params.append(status.upper())

            if start_date:
                try:
                    start_dt = datetime.fromisoformat(start_date).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    where_clauses.append("c.created_at >= %s")
                    params.append(start_dt)
                except ValueError:
                    logger.warning(f"Ignoring invalid start_date filter: {start_date}")

            if end_date:
                try:
                    end_dt = datetime.fromisoformat(end_date).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ) + timedelta(days=1)
                    where_clauses.append("c.created_at < %s")
                    params.append(end_dt)
                except ValueError:
                    logger.warning(f"Ignoring invalid end_date filter: {end_date}")

            if search and search.strip():
                where_clauses.append("""
                (
                    COALESCE(p.patient_name, '') ILIKE %s
                    OR COALESCE(c.merged_transcript_text, '') ILIKE %s
                    OR COALESCE(clips.merged_transcript, '') ILIKE %s
                    OR COALESCE(c.status, '') ILIKE %s
                    OR COALESCE(clips.medical_entities::text, '') ILIKE %s
                    OR COALESCE(p.prescription_id::text, '') ILIKE %s
                    OR COALESCE(p.state, '') ILIKE %s
                    OR COALESCE(p.medications::text, '') ILIKE %s
                    OR COALESCE(p.sections::text, '') ILIKE %s
                    OR TO_CHAR(c.created_at, 'Mon DD, YYYY') ILIKE %s
                )
                """)
                pattern = f"%{search.strip()}%"
                params.extend([pattern] * 10)

            where_clause = " AND ".join(where_clauses)
            final_query = query.format(where_clause=where_clause)
            params.append(limit)

            results = db_manager.execute_with_retry(final_query, tuple(params))
            
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
         created_at, prescription_id, prescription_patient_name, _medications, _sections, prescription_state) = row
        
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
            "prescription_state": prescription_state,
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
                category = entity.get("Category") or entity.get("category")
                entity_type = entity.get("Type") or entity.get("type")
                entity_text = entity.get("Text") or entity.get("text")
                if (category == "PROTECTED_HEALTH_INFORMATION" and
                    entity_type == "NAME" and
                    entity_text):
                    return entity_text.strip()
        
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
