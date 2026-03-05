"""
Validation Utilities

This module provides validation functions for the SEVA Arogya application,
including state transition validation and error handling helpers.
"""

import logging
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Valid state transitions for prescriptions
VALID_TRANSITIONS = {
    'Draft': ['InProgress', 'Deleted'],
    'InProgress': ['Finalized', 'Deleted'],
    'Finalized': ['Deleted'],
    'Deleted': ['Draft', 'InProgress', 'Finalized']  # Restore to previous state
}

# Valid prescription states
VALID_STATES = ['Draft', 'InProgress', 'Finalized', 'Deleted']

# Valid section statuses
VALID_SECTION_STATUSES = ['Pending', 'Approved', 'Rejected']

# Valid user roles
VALID_ROLES = ['Doctor', 'HospitalAdmin', 'DeveloperAdmin']


def validate_state_transition(current_state: str, new_state: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if a state transition is allowed.
    
    Args:
        current_state: Current prescription state
        new_state: Desired new state
    
    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if transition is valid
        - (False, error_message) if transition is invalid
    """
    # Validate current state
    if current_state not in VALID_STATES:
        return False, f"Invalid current state: {current_state}"
    
    # Validate new state
    if new_state not in VALID_STATES:
        return False, f"Invalid new state: {new_state}"
    
    # Check if transition is allowed
    allowed_transitions = VALID_TRANSITIONS.get(current_state, [])
    
    if new_state not in allowed_transitions:
        return False, f"Invalid state transition from {current_state} to {new_state}. Allowed transitions: {', '.join(allowed_transitions)}"
    
    return True, None


def validate_prescription_state(state: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if a prescription state is valid.
    
    Args:
        state: Prescription state to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if state not in VALID_STATES:
        return False, f"Invalid state: {state}. Valid states: {', '.join(VALID_STATES)}"
    
    return True, None


def validate_section_status(status: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if a section status is valid.
    
    Args:
        status: Section status to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if status not in VALID_SECTION_STATUSES:
        return False, f"Invalid section status: {status}. Valid statuses: {', '.join(VALID_SECTION_STATUSES)}"
    
    return True, None


def validate_user_role(role: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if a user role is valid.
    
    Args:
        role: User role to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if role not in VALID_ROLES:
        return False, f"Invalid role: {role}. Valid roles: {', '.join(VALID_ROLES)}"
    
    return True, None


def create_error_response(code: str, message: str, details: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        code: Error code (e.g., 'INVALID_STATE_TRANSITION', 'FORBIDDEN', 'NOT_FOUND')
        message: Human-readable error message
        details: Optional additional details
    
    Returns:
        Dictionary with standardized error format
    """
    error_response = {
        'success': False,
        'error': {
            'code': code,
            'message': message
        }
    }
    
    if details:
        error_response['error']['details'] = details
    
    return error_response


def create_success_response(data: Optional[Dict[str, Any]] = None, message: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a standardized success response.
    
    Args:
        data: Optional data to include in response
        message: Optional success message
    
    Returns:
        Dictionary with standardized success format
    """
    response = {'success': True}
    
    if message:
        response['message'] = message
    
    if data:
        response.update(data)
    
    return response
