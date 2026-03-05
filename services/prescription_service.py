"""Prescription Service for managing prescription workflow and state transitions"""
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class PrescriptionService:
    """Service for managing prescription lifecycle and state transitions"""
    
    # Valid state transitions
    VALID_TRANSITIONS = {
        'Draft': ['InProgress', 'Deleted'],
        'InProgress': ['Finalized', 'Deleted'],
        'Finalized': ['Deleted'],
        'Deleted': ['Draft', 'InProgress']  # Restore to pre_deleted_state
    }
    
    # Section definitions with required flag and order
    SECTION_DEFINITIONS = [
        {"key": "diagnosis", "title": "Diagnosis", "required": True, "order": 1},
        {"key": "medications", "title": "Medications", "required": True, "order": 2},
        {"key": "instructions", "title": "Patient Instructions", "required": True, "order": 3},
        {"key": "follow_up", "title": "Follow-up", "required": False, "order": 4},
        {"key": "lab_tests", "title": "Laboratory Tests", "required": False, "order": 5},
        {"key": "referrals", "title": "Referrals", "required": False, "order": 6}
    ]
    
    def __init__(self, database_manager):
        """
        Initialize PrescriptionService
        
        Args:
            database_manager: DatabaseManager instance
        """
        self.db = database_manager
    
    def create_prescription(self, user_id: str, consultation_id: str, 
                          hospital_id: str, patient_name: str) -> Optional[str]:
        """
        Create new prescription in Draft state
        
        Args:
            user_id: Doctor user ID
            consultation_id: Consultation session ID
            hospital_id: Hospital ID
            patient_name: Patient name
            
        Returns:
            Prescription ID if successful, None otherwise
        """
        query = """
        INSERT INTO prescriptions 
        (user_id, created_by_doctor_id, consultation_id, hospital_id, patient_name, 
         state, medications, s3_key, sections, created_at)
        VALUES (%s, %s, %s, %s, %s, 'Draft', '[]'::jsonb, '', '[]'::jsonb, CURRENT_TIMESTAMP)
        RETURNING prescription_id
        """
        
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (user_id, user_id, consultation_id, hospital_id, patient_name))
                    conn.commit()
                    result = cursor.fetchone()
                    if result:
                        prescription_id = str(result[0])
                        logger.info(f"Prescription created: {prescription_id} by user {user_id}")
                        return prescription_id
        except Exception as e:
            logger.error(f"Failed to create prescription: {str(e)}")
            return None
    
    def transition_to_in_progress(self, prescription_id: str, bedrock_payload: Dict[str, Any]) -> bool:
        """
        Transition prescription from Draft to InProgress and load Bedrock content
        
        Args:
            prescription_id: Prescription ID
            bedrock_payload: Bedrock AI response payload
            
        Returns:
            True if successful, False otherwise
        """
        # Map Bedrock response to sections
        sections = self._map_bedrock_to_sections(bedrock_payload)
        
        query = """
        UPDATE prescriptions
        SET state = 'InProgress',
            sections = %s::jsonb,
            bedrock_payload = %s::jsonb,
            updated_at = CURRENT_TIMESTAMP
        WHERE prescription_id = %s AND state = 'Draft'
        """
        
        try:
            self.db.execute_with_retry(query, (
                json.dumps(sections),
                json.dumps(bedrock_payload),
                prescription_id
            ))
            logger.info(f"Prescription {prescription_id} transitioned to InProgress")
            return True
        except Exception as e:
            logger.error(f"Failed to transition prescription to InProgress: {str(e)}")
            return False
    
    def _map_bedrock_to_sections(self, bedrock_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Map Bedrock response to prescription sections
        
        Args:
            bedrock_response: Bedrock AI response
            
        Returns:
            List of section dictionaries
        """
        sections = []
        bedrock_sections = bedrock_response.get('sections', {})
        
        for section_def in self.SECTION_DEFINITIONS:
            key = section_def["key"]
            content = bedrock_sections.get(key, "")
            
            # Convert list to formatted string for medications
            if key == "medications" and isinstance(content, list):
                content = self._format_medications(content)
            
            sections.append({
                "key": key,
                "title": section_def["title"],
                "content": content if content else "",
                "status": "Pending",
                "order": section_def["order"],
                "required": section_def["required"]
            })
        
        return sections
    
    def _format_medications(self, medications: List[Dict[str, Any]]) -> str:
        """
        Format medications list as readable string
        
        Args:
            medications: List of medication dictionaries
            
        Returns:
            Formatted string
        """
        formatted = []
        for med in medications:
            name = med.get('name', '')
            dosage = med.get('dosage', '')
            frequency = med.get('frequency', '')
            duration = med.get('duration', '')
            formatted.append(f"{name} - {dosage}, {frequency}, {duration}")
        return "\n".join(formatted)
    
    def approve_section(self, prescription_id: str, section_key: str, user_id: str) -> bool:
        """
        Approve a prescription section
        
        Args:
            prescription_id: Prescription ID
            section_key: Section key to approve
            user_id: User ID performing the action
            
        Returns:
            True if successful, False otherwise
        """
        return self._update_section_status(prescription_id, section_key, "Approved")
    
    def reject_section(self, prescription_id: str, section_key: str, user_id: str) -> bool:
        """
        Reject a prescription section (enables editing)
        
        Args:
            prescription_id: Prescription ID
            section_key: Section key to reject
            user_id: User ID performing the action
            
        Returns:
            True if successful, False otherwise
        """
        return self._update_section_status(prescription_id, section_key, "Rejected")
    
    def update_section_content(self, prescription_id: str, section_key: str, content: str) -> bool:
        """
        Update section content and reset status to Pending
        
        Args:
            prescription_id: Prescription ID
            section_key: Section key to update
            content: New content
            
        Returns:
            True if successful, False otherwise
        """
        query = """
        UPDATE prescriptions
        SET sections = (
            SELECT jsonb_agg(
                CASE 
                    WHEN elem->>'key' = %s 
                    THEN jsonb_set(jsonb_set(elem, '{content}', to_jsonb(%s::text)), '{status}', '"Pending"')
                    ELSE elem
                END
            )
            FROM jsonb_array_elements(sections) elem
        ),
        updated_at = CURRENT_TIMESTAMP
        WHERE prescription_id = %s AND state = 'InProgress'
        """
        
        try:
            self.db.execute_with_retry(query, (section_key, content, prescription_id))
            logger.info(f"Section {section_key} updated in prescription {prescription_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update section content: {str(e)}")
            return False
    
    def _update_section_status(self, prescription_id: str, section_key: str, status: str) -> bool:
        """
        Update section status
        
        Args:
            prescription_id: Prescription ID
            section_key: Section key
            status: New status (Pending, Approved, Rejected)
            
        Returns:
            True if successful, False otherwise
        """
        query = """
        UPDATE prescriptions
        SET sections = (
            SELECT jsonb_agg(
                CASE 
                    WHEN elem->>'key' = %s 
                    THEN jsonb_set(elem, '{status}', to_jsonb(%s::text))
                    ELSE elem
                END
            )
            FROM jsonb_array_elements(sections) elem
        ),
        updated_at = CURRENT_TIMESTAMP
        WHERE prescription_id = %s AND state = 'InProgress'
        """
        
        try:
            self.db.execute_with_retry(query, (section_key, status, prescription_id))
            logger.info(f"Section {section_key} status set to {status} in prescription {prescription_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update section status: {str(e)}")
            return False
    
    def can_finalize(self, prescription_id: str) -> bool:
        """
        Check if prescription can be finalized (all required sections approved)
        
        Args:
            prescription_id: Prescription ID
            
        Returns:
            True if can finalize, False otherwise
        """
        query = """
        SELECT sections
        FROM prescriptions
        WHERE prescription_id = %s
        """
        
        try:
            result = self.db.execute_with_retry(query, (prescription_id,))
            if result and len(result) > 0:
                sections = result[0][0]
                if isinstance(sections, str):
                    sections = json.loads(sections)
                
                # Check all required sections are approved
                for section in sections:
                    if section.get('required', True) and section.get('status') != 'Approved':
                        return False
                return True
        except Exception as e:
            logger.error(f"Failed to check if prescription can be finalized: {str(e)}")
            return False
    
    def finalize_prescription(self, prescription_id: str, user_id: str) -> bool:
        """
        Finalize prescription (set state to Finalized)
        
        Args:
            prescription_id: Prescription ID
            user_id: User ID performing finalization
            
        Returns:
            True if successful, False otherwise
        """
        # Check if can finalize
        if not self.can_finalize(prescription_id):
            logger.warning(f"Cannot finalize prescription {prescription_id}: not all required sections approved")
            return False
        
        query = """
        UPDATE prescriptions
        SET state = 'Finalized',
            finalized_at = CURRENT_TIMESTAMP,
            finalized_by = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE prescription_id = %s AND state = 'InProgress'
        """
        
        try:
            self.db.execute_with_retry(query, (user_id, prescription_id))
            logger.info(f"Prescription {prescription_id} finalized by user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to finalize prescription: {str(e)}")
            return False
    
    def soft_delete(self, prescription_id: str, user_id: str) -> bool:
        """
        Soft delete prescription (set state to Deleted, preserve record)
        
        Args:
            prescription_id: Prescription ID
            user_id: User ID performing deletion
            
        Returns:
            True if successful, False otherwise
        """
        query = """
        UPDATE prescriptions
        SET state = 'Deleted',
            deleted_at = CURRENT_TIMESTAMP,
            deleted_by = %s,
            pre_deleted_state = state,
            updated_at = CURRENT_TIMESTAMP
        WHERE prescription_id = %s AND state != 'Deleted'
        """
        
        try:
            self.db.execute_with_retry(query, (user_id, prescription_id))
            logger.info(f"Prescription {prescription_id} soft deleted by user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to soft delete prescription: {str(e)}")
            return False
    
    def restore_prescription(self, prescription_id: str, user_id: str) -> bool:
        """
        Restore soft-deleted prescription
        
        Args:
            prescription_id: Prescription ID
            user_id: User ID performing restoration
            
        Returns:
            True if successful, False otherwise
        """
        query = """
        UPDATE prescriptions
        SET state = pre_deleted_state,
            deleted_at = NULL,
            deleted_by = NULL,
            pre_deleted_state = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE prescription_id = %s 
          AND state = 'Deleted'
          AND deleted_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
        """
        
        try:
            self.db.execute_with_retry(query, (prescription_id,))
            logger.info(f"Prescription {prescription_id} restored by user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore prescription: {str(e)}")
            return False
    
    def get_prescription_with_permissions(self, prescription_id: str, user_id: str, 
                                         user_role: str) -> Optional[Dict[str, Any]]:
        """
        Get prescription with permission flags
        
        Args:
            prescription_id: Prescription ID
            user_id: User ID requesting prescription
            user_role: User role
            
        Returns:
            Prescription dictionary with permissions or None
        """
        query = """
        SELECT p.prescription_id, p.user_id, p.patient_name, p.state, 
               p.created_by_doctor_id, p.hospital_id, p.sections, p.medications,
               p.s3_key, p.created_at, p.finalized_at, p.finalized_by,
               p.deleted_at, p.deleted_by, p.pre_deleted_state, p.consultation_id,
               p.bedrock_payload
        FROM prescriptions p
        WHERE p.prescription_id = %s
        """
        
        try:
            result = self.db.execute_with_retry(query, (prescription_id,))
            if result and len(result) > 0:
                row = result[0]
                
                prescription = {
                    'prescription_id': str(row[0]),
                    'user_id': row[1],
                    'patient_name': row[2],
                    'state': row[3],
                    'created_by_doctor_id': row[4],
                    'hospital_id': row[5],
                    'sections': json.loads(row[6]) if isinstance(row[6], str) else row[6],
                    'medications': json.loads(row[7]) if isinstance(row[7], str) else row[7],
                    's3_key': row[8],
                    'created_at': row[9].isoformat() if row[9] else None,
                    'finalized_at': row[10].isoformat() if row[10] else None,
                    'finalized_by': row[11],
                    'deleted_at': row[12].isoformat() if row[12] else None,
                    'deleted_by': row[13],
                    'pre_deleted_state': row[14],
                    'consultation_id': row[15],
                    'bedrock_payload': json.loads(row[16]) if row[16] and isinstance(row[16], str) else row[16]
                }
                
                # Add permissions
                prescription['permissions'] = self._calculate_permissions(
                    prescription, user_id, user_role
                )
                
                return prescription
        except Exception as e:
            logger.error(f"Failed to get prescription: {str(e)}")
            return None
    
    def _calculate_permissions(self, prescription: Dict[str, Any], 
                              user_id: str, user_role: str) -> Dict[str, bool]:
        """
        Calculate user permissions for prescription
        
        Args:
            prescription: Prescription dictionary
            user_id: User ID
            user_role: User role
            
        Returns:
            Permissions dictionary
        """
        state = prescription['state']
        is_creator = prescription['created_by_doctor_id'] == user_id
        is_dev_admin = user_role == 'DeveloperAdmin'
        
        # Check if within 30-day restore window
        within_restore_window = False
        if prescription.get('deleted_at'):
            deleted_at = datetime.fromisoformat(prescription['deleted_at'])
            days_since_deletion = (datetime.now() - deleted_at).days
            within_restore_window = days_since_deletion <= 30
        
        return {
            'can_edit': state in ['Draft', 'InProgress'] and is_creator,
            'can_delete': state != 'Deleted' and is_creator,
            'can_restore': state == 'Deleted' and within_restore_window and (is_creator or is_dev_admin),
            'can_download_pdf': state == 'Finalized'
        }
