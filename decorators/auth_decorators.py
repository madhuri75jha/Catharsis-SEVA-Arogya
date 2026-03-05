"""
Authentication and Authorization Decorators

This module provides decorators for role-based access control (RBAC) in the SEVA Arogya application.
"""

from functools import wraps
from flask import session, jsonify
import logging

logger = logging.getLogger(__name__)


def require_role(*allowed_roles):
    """
    Decorator to enforce role-based access control on routes.
    
    Usage:
        @require_role('DeveloperAdmin')
        def admin_only_route():
            ...
        
        @require_role('Doctor', 'HospitalAdmin')
        def doctor_or_admin_route():
            ...
    
    Args:
        *allowed_roles: Variable number of role strings that are allowed to access the route.
                       Valid roles: 'Doctor', 'HospitalAdmin', 'DeveloperAdmin'
    
    Returns:
        Decorated function that checks user role before executing.
        Returns 403 Forbidden if user role is not in allowed_roles.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get user role from session
            user_role = session.get('user_role')
            
            if not user_role:
                logger.warning(f"Access denied to {f.__name__}: No role in session")
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'Access denied. User role not found.',
                        'details': 'Please log in again to refresh your session.'
                    }
                }), 403
            
            # Check if user role is in allowed roles
            if user_role not in allowed_roles:
                logger.warning(
                    f"Access denied to {f.__name__}: User role '{user_role}' not in allowed roles {allowed_roles}"
                )
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': f'Access denied. This action requires one of the following roles: {", ".join(allowed_roles)}',
                        'details': f'Your current role is: {user_role}'
                    }
                }), 403
            
            # Role is allowed, proceed with the route
            logger.debug(f"Access granted to {f.__name__} for role '{user_role}'")
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
