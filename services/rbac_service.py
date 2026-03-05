"""RBAC Service for role-based access control and permission management"""
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class RBACService:
    """Service for managing role-based access control"""
    
    # Role hierarchy
    ROLES = ['Doctor', 'HospitalAdmin', 'DeveloperAdmin']
    
    # Sidebar menu items by role
    SIDEBAR_MENUS = {
        'Doctor': [
            {'label': 'Home', 'icon': 'home', 'route': '/home'},
            {'label': 'My Prescriptions', 'icon': 'description', 'route': '/prescriptions'},
            {'label': 'Profile', 'icon': 'person', 'route': '/profile'}
        ],
        'HospitalAdmin': [
            {'label': 'Home', 'icon': 'home', 'route': '/home'},
            {'label': 'Prescriptions', 'icon': 'description', 'route': '/prescriptions'},
            {'label': 'Hospital Settings', 'icon': 'local_hospital', 'route': '/hospital-settings'},
            {'label': 'Profile', 'icon': 'person', 'route': '/profile'}
        ],
        'DeveloperAdmin': [
            {'label': 'Home', 'icon': 'home', 'route': '/home'},
            {'label': 'All Prescriptions', 'icon': 'description', 'route': '/prescriptions'},
            {'label': 'Hospital Settings', 'icon': 'local_hospital', 'route': '/hospital-settings'},
            {'label': 'CloudWatch Logs', 'icon': 'article', 'route': '/logs'},
            {'label': 'Profile', 'icon': 'person', 'route': '/profile'}
        ]
    }
    
    def __init__(self, database_manager):
        """
        Initialize RBACService
        
        Args:
            database_manager: DatabaseManager instance
        """
        self.db = database_manager
    
    def get_user_role(self, user_id: str) -> Optional[str]:
        """
        Get user role from user_roles table
        
        Args:
            user_id: User ID
            
        Returns:
            Role string (Doctor, HospitalAdmin, DeveloperAdmin) or None
        """
        query = """
        SELECT role
        FROM user_roles
        WHERE user_id = %s
        """
        
        try:
            result = self.db.execute_with_retry(query, (user_id,))
            if result and len(result) > 0:
                return result[0][0]
            # Safe fallback for stale users without a row; login flow now blocks this case.
            return 'Doctor'
        except Exception as e:
            logger.error(f"Failed to get user role: {str(e)}")
            return 'Doctor'
    
    def get_user_hospital(self, user_id: str) -> Optional[str]:
        """
        Get user's hospital ID
        
        Args:
            user_id: User ID
            
        Returns:
            Hospital ID or None
        """
        query = """
        SELECT hospital_id
        FROM user_roles
        WHERE user_id = %s
        """
        
        try:
            result = self.db.execute_with_retry(query, (user_id,))
            if result and len(result) > 0:
                return result[0][0]
            return None
        except Exception as e:
            logger.error(f"Failed to get user hospital: {str(e)}")
            return None
    
    def sync_user_role_from_cognito(self, user_id: str, cognito_attributes: Dict[str, Any]) -> bool:
        """
        Synchronize user role from Cognito custom attributes
        
        Args:
            user_id: User ID
            cognito_attributes: Cognito user attributes
            
        Returns:
            True if successful, False otherwise
        """
        role = cognito_attributes.get('custom:role')
        hospital_id = cognito_attributes.get('custom:hospital_id')

        if role not in self.ROLES:
            logger.error(f"Cannot sync role for {user_id}: invalid or missing role '{role}'")
            return False

        if role in ['Doctor', 'HospitalAdmin'] and not hospital_id:
            logger.error(f"Cannot sync role for {user_id}: missing hospital_id for role '{role}'")
            return False
        
        query = """
        INSERT INTO user_roles (user_id, role, hospital_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE
        SET role = EXCLUDED.role, 
            hospital_id = EXCLUDED.hospital_id, 
            updated_at = CURRENT_TIMESTAMP
        """
        
        try:
            self.db.execute_with_retry(query, (user_id, role, hospital_id))
            logger.info(f"User role synchronized: {user_id} -> {role}")
            return True
        except Exception as e:
            logger.error(f"Failed to sync user role: {str(e)}")
            return False
    
    def can_view_prescription(self, user_id: str, prescription: Dict[str, Any]) -> bool:
        """
        Check if user can view prescription
        
        Args:
            user_id: User ID
            prescription: Prescription dictionary
            
        Returns:
            True if user can view, False otherwise
        """
        role = self.get_user_role(user_id)
        
        # DeveloperAdmin can view all
        if role == 'DeveloperAdmin':
            return True
        
        # HospitalAdmin can view all in their hospital
        if role == 'HospitalAdmin':
            user_hospital = self.get_user_hospital(user_id)
            return prescription.get('hospital_id') == user_hospital
        
        # Doctor can only view own prescriptions
        return prescription.get('created_by_doctor_id') == user_id
    
    def can_edit_prescription(self, user_id: str, prescription: Dict[str, Any]) -> bool:
        """
        Check if user can edit prescription
        
        Args:
            user_id: User ID
            prescription: Prescription dictionary
            
        Returns:
            True if user can edit, False otherwise
        """
        # Only creator can edit, and only if not Finalized or Deleted
        state = prescription.get('state')
        is_creator = prescription.get('created_by_doctor_id') == user_id
        
        return is_creator and state in ['Draft', 'InProgress']
    
    def can_delete_prescription(self, user_id: str, prescription: Dict[str, Any]) -> bool:
        """
        Check if user can delete prescription
        
        Args:
            user_id: User ID
            prescription: Prescription dictionary
            
        Returns:
            True if user can delete, False otherwise
        """
        # Only creator can delete, and only if not already deleted
        state = prescription.get('state')
        is_creator = prescription.get('created_by_doctor_id') == user_id
        
        return is_creator and state != 'Deleted'
    
    def can_restore_prescription(self, user_id: str, prescription: Dict[str, Any]) -> bool:
        """
        Check if user can restore prescription
        
        Args:
            user_id: User ID
            prescription: Prescription dictionary
            
        Returns:
            True if user can restore, False otherwise
        """
        role = self.get_user_role(user_id)
        state = prescription.get('state')
        is_creator = prescription.get('created_by_doctor_id') == user_id
        
        # Must be deleted and within 30 days
        if state != 'Deleted':
            return False
        
        # Check 30-day window
        from datetime import datetime
        deleted_at = prescription.get('deleted_at')
        if deleted_at:
            if isinstance(deleted_at, str):
                deleted_at = datetime.fromisoformat(deleted_at)
            days_since_deletion = (datetime.now() - deleted_at).days
            if days_since_deletion > 30:
                return False
        
        # Creator or DeveloperAdmin can restore
        return is_creator or role == 'DeveloperAdmin'
    
    def filter_prescriptions_by_role(self, prescriptions: List[Dict[str, Any]], 
                                    user_id: str, role: str, 
                                    hospital_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Filter prescriptions based on user role
        
        Args:
            prescriptions: List of prescription dictionaries
            user_id: User ID
            role: User role
            hospital_id: User's hospital ID (optional)
            
        Returns:
            Filtered list of prescriptions
        """
        if role == 'DeveloperAdmin':
            return prescriptions
        
        if role == 'HospitalAdmin' and hospital_id:
            return [p for p in prescriptions if p.get('hospital_id') == hospital_id]
        
        # Doctor - only own prescriptions
        return [p for p in prescriptions if p.get('created_by_doctor_id') == user_id]
    
    def get_prescription_filter_sql(self, user_id: str, role: str, 
                                   hospital_id: Optional[str] = None) -> str:
        """
        Get SQL WHERE clause for prescription filtering based on role
        
        Args:
            user_id: User ID
            role: User role
            hospital_id: User's hospital ID (optional)
            
        Returns:
            SQL WHERE clause string
        """
        if role == 'DeveloperAdmin':
            return "1=1"  # No filtering
        
        if role == 'HospitalAdmin' and hospital_id:
            return f"hospital_id = '{hospital_id}'"
        
        # Doctor - only own prescriptions
        return f"created_by_doctor_id = '{user_id}'"
    
    def get_sidebar_menu_items(self, role: str) -> List[Dict[str, str]]:
        """
        Get sidebar menu items for user role
        
        Args:
            role: User role
            
        Returns:
            List of menu item dictionaries
        """
        return self.SIDEBAR_MENUS.get(role, self.SIDEBAR_MENUS['Doctor'])
    
    def check_permission(self, user_id: str, prescription: Dict[str, Any], 
                        operation: str) -> tuple[bool, str]:
        """
        Check if user has permission for operation on prescription
        
        Args:
            user_id: User ID
            prescription: Prescription dictionary
            operation: Operation name (view, edit, delete, restore, finalize)
            
        Returns:
            Tuple of (has_permission, error_message)
        """
        if operation == 'view':
            if not self.can_view_prescription(user_id, prescription):
                return False, "You do not have permission to view this prescription"
        
        elif operation == 'edit':
            if not self.can_edit_prescription(user_id, prescription):
                return False, "You can only edit your own prescriptions that are in Draft or InProgress state"
        
        elif operation == 'delete':
            if not self.can_delete_prescription(user_id, prescription):
                return False, "You can only delete your own prescriptions"
        
        elif operation == 'restore':
            if not self.can_restore_prescription(user_id, prescription):
                return False, "You can only restore your own prescriptions within 30 days of deletion"
        
        elif operation == 'finalize':
            is_creator = prescription.get('created_by_doctor_id') == user_id
            if not is_creator:
                return False, "Only the creator can finalize this prescription"
            
            state = prescription.get('state')
            if state != 'InProgress':
                return False, "Prescription must be in InProgress state to finalize"
        
        return True, ""
