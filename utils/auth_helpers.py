"""
Authentication Helper Functions

This module provides helper functions for authentication and authorization,
including Cognito role synchronization.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def sync_user_role_from_cognito(database_manager, user_info: Dict[str, Any], user_id: str) -> Optional[str]:
    """
    Synchronize user role from Cognito custom attributes to the user_roles table.
    
    This function extracts the custom:role and custom:hospital_id attributes from
    Cognito user info and upserts them into the user_roles table. This ensures
    that the application's RBAC system stays in sync with Cognito.
    
    Args:
        database_manager: DatabaseManager instance for database operations
        user_info: User info dictionary from Cognito (from validate_token)
        user_id: User ID (typically email)
    
    Returns:
        str: The user's role ('Doctor', 'HospitalAdmin', or 'DeveloperAdmin')
        None: If role sync fails
    """
    try:
        # Extract custom attributes from Cognito
        attributes = user_info.get('attributes', {})
        role = attributes.get('custom:role')
        hospital_id = attributes.get('custom:hospital_id')
        
        # Default to Doctor role if not specified
        if not role:
            logger.warning(f"No custom:role attribute found for user {user_id}, defaulting to Doctor")
            role = 'Doctor'
        
        # Validate role
        valid_roles = ['Doctor', 'HospitalAdmin', 'DeveloperAdmin']
        if role not in valid_roles:
            logger.error(f"Invalid role '{role}' for user {user_id}, defaulting to Doctor")
            role = 'Doctor'
        
        # Upsert to user_roles table
        conn = database_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if user role already exists
            cursor.execute(
                "SELECT role, hospital_id FROM user_roles WHERE user_id = %s",
                (user_id,)
            )
            existing_role = cursor.fetchone()
            
            if existing_role:
                # Update existing role
                cursor.execute(
                    """
                    UPDATE user_roles 
                    SET role = %s, hospital_id = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                    """,
                    (role, hospital_id, user_id)
                )
                logger.info(f"Updated role for user {user_id}: {role} (hospital: {hospital_id})")
            else:
                # Insert new role
                cursor.execute(
                    """
                    INSERT INTO user_roles (user_id, role, hospital_id, created_at, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (user_id, role, hospital_id)
                )
                logger.info(f"Created role for user {user_id}: {role} (hospital: {hospital_id})")
            
            conn.commit()
            return role
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error syncing role for user {user_id}: {str(e)}")
            return None
        finally:
            cursor.close()
            
    except Exception as e:
        logger.error(f"Error syncing user role from Cognito for {user_id}: {str(e)}")
        return None


def get_user_role_from_session(session) -> Optional[str]:
    """
    Get user role from Flask session.
    
    Args:
        session: Flask session object
    
    Returns:
        str: User role if found in session
        None: If role not found
    """
    return session.get('user_role')


def get_user_hospital_from_session(session) -> Optional[str]:
    """
    Get user hospital ID from Flask session.
    
    Args:
        session: Flask session object
    
    Returns:
        str: Hospital ID if found in session
        None: If hospital ID not found
    """
    return session.get('hospital_id')
