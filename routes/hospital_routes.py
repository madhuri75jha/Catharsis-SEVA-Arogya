"""Hospital and User Management API Routes"""
import logging
import os
import base64
from flask import Blueprint, request, jsonify, session
from functools import wraps
import json
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Create blueprint
hospital_bp = Blueprint('hospitals', __name__, url_prefix='/api/v1')

# Global service instances
rbac_service = None
database_manager = None
cloudwatch_service = None


def init_hospital_routes(rbac_svc, db_manager, cw_service=None):
    """Initialize hospital routes with service instances"""
    global rbac_service, database_manager, cloudwatch_service
    rbac_service = rbac_svc
    database_manager = db_manager
    cloudwatch_service = cw_service
    logger.info("Hospital routes initialized")


def _decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without signature verification for non-sensitive display metadata."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return {}
        payload = parts[1]
        payload += '=' * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode('utf-8')).decode('utf-8')
        return json.loads(decoded)
    except Exception:
        return {}


def login_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


def require_role(*allowed_roles):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({'success': False, 'message': 'Unauthorized'}), 401
            
            user_role = rbac_service.get_user_role(user_id)
            if user_role not in allowed_roles:
                return jsonify({'success': False, 'message': 'Forbidden'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Hospital Management Endpoints

@hospital_bp.route('/hospitals', methods=['GET'])
@login_required
@require_role('DeveloperAdmin')
def get_hospitals():
    """Get list of all hospitals (DeveloperAdmin only)"""
    try:
        query = """
        SELECT hospital_id, name, address, phone, email, 
               registration_number, website, logo_url, created_at
        FROM hospitals
        ORDER BY name ASC
        """
        
        results = database_manager.execute_with_retry(query)
        
        hospitals = []
        if results:
            for row in results:
                hospitals.append({
                    'hospital_id': row[0],
                    'name': row[1],
                    'address': row[2],
                    'phone': row[3],
                    'email': row[4],
                    'registration_number': row[5],
                    'website': row[6],
                    'logo_url': row[7],
                    'created_at': row[8].isoformat() if row[8] else None
                })
        
        return jsonify({
            'success': True,
            'hospitals': hospitals
        })
        
    except Exception as e:
        logger.error(f"Failed to get hospitals: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to retrieve hospitals'}), 500


@hospital_bp.route('/hospitals/<hospital_id>', methods=['GET'])
@login_required
def get_hospital(hospital_id):
    """Get hospital details (HospitalAdmin for own hospital or DeveloperAdmin)"""
    try:
        user_id = session.get('user_id')
        user_role = rbac_service.get_user_role(user_id)
        user_hospital = rbac_service.get_user_hospital(user_id)
        
        # Check authorization
        if user_role == 'HospitalAdmin' and user_hospital != hospital_id:
            return jsonify({'success': False, 'message': 'Forbidden'}), 403
        elif user_role == 'Doctor':
            return jsonify({'success': False, 'message': 'Forbidden'}), 403
        
        query = """
        SELECT hospital_id, name, address, phone, email, 
               registration_number, website, logo_url, created_at, updated_at
        FROM hospitals
        WHERE hospital_id = %s
        """
        
        result = database_manager.execute_with_retry(query, (hospital_id,))
        
        if not result:
            return jsonify({'success': False, 'message': 'Hospital not found'}), 404
        
        row = result[0]
        hospital = {
            'hospital_id': row[0],
            'name': row[1],
            'address': row[2],
            'phone': row[3],
            'email': row[4],
            'registration_number': row[5],
            'website': row[6],
            'logo_url': row[7],
            'created_at': row[8].isoformat() if row[8] else None,
            'updated_at': row[9].isoformat() if row[9] else None
        }
        
        return jsonify({
            'success': True,
            'hospital': hospital
        })
        
    except Exception as e:
        logger.error(f"Failed to get hospital {hospital_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to retrieve hospital'}), 500


@hospital_bp.route('/hospitals/<hospital_id>', methods=['PUT'])
@login_required
def update_hospital(hospital_id):
    """Update hospital information (HospitalAdmin for own hospital or DeveloperAdmin)"""
    try:
        user_id = session.get('user_id')
        user_role = rbac_service.get_user_role(user_id)
        user_hospital = rbac_service.get_user_hospital(user_id)
        
        # Check authorization
        if user_role == 'HospitalAdmin' and user_hospital != hospital_id:
            return jsonify({'success': False, 'message': 'Forbidden'}), 403
        elif user_role == 'Doctor':
            return jsonify({'success': False, 'message': 'Forbidden'}), 403
        
        data = request.get_json()
        
        # Build update query dynamically
        update_fields = []
        params = []
        
        allowed_fields = ['name', 'address', 'phone', 'email', 'registration_number', 'website', 'logo_url']
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"{field} = %s")
                params.append(data[field])
        
        if not update_fields:
            return jsonify({'success': False, 'message': 'No fields to update'}), 400
        
        params.append(hospital_id)
        
        query = f"""
        UPDATE hospitals
        SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
        WHERE hospital_id = %s
        """
        
        database_manager.execute_with_retry(query, tuple(params))
        
        logger.info(f"Hospital {hospital_id} updated by user {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Hospital updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to update hospital {hospital_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to update hospital'}), 500


# Doctor Management Endpoints

@hospital_bp.route('/hospitals/<hospital_id>/doctors', methods=['GET'])
@login_required
def get_hospital_doctors(hospital_id):
    """Get list of doctors in a hospital"""
    try:
        user_id = session.get('user_id')
        user_role = rbac_service.get_user_role(user_id)
        user_hospital = rbac_service.get_user_hospital(user_id)
        
        # Check authorization
        if user_role == 'HospitalAdmin' and user_hospital != hospital_id:
            return jsonify({'success': False, 'message': 'Forbidden'}), 403
        elif user_role == 'Doctor':
            return jsonify({'success': False, 'message': 'Forbidden'}), 403
        
        query = """
        SELECT doctor_id, name, specialty, signature_url, availability, created_at
        FROM doctors
        WHERE hospital_id = %s
        ORDER BY name ASC
        """
        
        results = database_manager.execute_with_retry(query, (hospital_id,))
        
        doctors = []
        if results:
            for row in results:
                doctors.append({
                    'doctor_id': row[0],
                    'name': row[1],
                    'specialty': row[2],
                    'signature_url': row[3],
                    'availability': row[4],
                    'created_at': row[5].isoformat() if row[5] else None
                })
        
        return jsonify({
            'success': True,
            'doctors': doctors
        })
        
    except Exception as e:
        logger.error(f"Failed to get doctors for hospital {hospital_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to retrieve doctors'}), 500


@hospital_bp.route('/hospitals/<hospital_id>/doctors', methods=['POST'])
@login_required
def add_hospital_doctor(hospital_id):
    """Add doctor to hospital"""
    try:
        user_id = session.get('user_id')
        user_role = rbac_service.get_user_role(user_id)
        user_hospital = rbac_service.get_user_hospital(user_id)
        
        # Check authorization
        if user_role == 'HospitalAdmin' and user_hospital != hospital_id:
            return jsonify({'success': False, 'message': 'Forbidden'}), 403
        elif user_role == 'Doctor':
            return jsonify({'success': False, 'message': 'Forbidden'}), 403
        
        data = request.get_json()
        doctor_id = data.get('doctor_id', '')
        name = data.get('name', '')
        specialty = data.get('specialty', '')
        
        if not doctor_id or not name:
            return jsonify({'success': False, 'message': 'doctor_id and name required'}), 400
        
        query = """
        INSERT INTO doctors (doctor_id, hospital_id, name, specialty)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (doctor_id) DO UPDATE
        SET hospital_id = EXCLUDED.hospital_id,
            name = EXCLUDED.name,
            specialty = EXCLUDED.specialty,
            updated_at = CURRENT_TIMESTAMP
        """
        
        database_manager.execute_with_retry(query, (doctor_id, hospital_id, name, specialty))
        
        logger.info(f"Doctor {doctor_id} added to hospital {hospital_id}")
        
        return jsonify({
            'success': True,
            'message': 'Doctor added successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to add doctor to hospital {hospital_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to add doctor'}), 500


@hospital_bp.route('/hospitals/<hospital_id>/doctors/<doctor_id>', methods=['DELETE'])
@login_required
def remove_hospital_doctor(hospital_id, doctor_id):
    """Remove doctor from hospital"""
    try:
        user_id = session.get('user_id')
        user_role = rbac_service.get_user_role(user_id)
        user_hospital = rbac_service.get_user_hospital(user_id)
        
        # Check authorization
        if user_role == 'HospitalAdmin' and user_hospital != hospital_id:
            return jsonify({'success': False, 'message': 'Forbidden'}), 403
        elif user_role == 'Doctor':
            return jsonify({'success': False, 'message': 'Forbidden'}), 403
        
        query = "DELETE FROM doctors WHERE doctor_id = %s AND hospital_id = %s"
        database_manager.execute_with_retry(query, (doctor_id, hospital_id))
        
        logger.info(f"Doctor {doctor_id} removed from hospital {hospital_id}")
        
        return jsonify({
            'success': True,
            'message': 'Doctor removed successfully'
        })
        
    except Exception as e:
        logger.error(f"Failed to remove doctor from hospital: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to remove doctor'}), 500


# Profile Endpoint

@hospital_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """Get current user profile"""
    try:
        user_id = session.get('user_id')
        user_role = rbac_service.get_user_role(user_id)
        user_hospital = rbac_service.get_user_hospital(user_id)
        from utils.auth_helpers import format_role_display
        
        # Get doctor info
        doctor_query = """
        SELECT d.name, d.specialty, d.signature_url, d.availability, h.name as hospital_name
        FROM doctors d
        LEFT JOIN hospitals h ON d.hospital_id = h.hospital_id
        WHERE d.doctor_id = %s
        """
        
        doctor_result = database_manager.execute_with_retry(doctor_query, (user_id,))

        # Derive last login from Cognito token claims when available.
        last_login_at = session.get('login_at')
        token_claims = _decode_jwt_payload(session.get('id_token', ''))
        auth_time = token_claims.get('auth_time')
        if auth_time:
            try:
                last_login_at = datetime.fromtimestamp(int(auth_time), tz=timezone.utc).isoformat()
            except (TypeError, ValueError):
                pass

        user_attributes = session.get('user_attributes', {}) or {}
        email_verified = None
        if 'email_verified' in user_attributes:
            email_verified = str(user_attributes.get('email_verified')).lower() == 'true'

        # Consultation metrics and trend for quick profile insights.
        if user_role == 'DeveloperAdmin':
            metrics_query = """
            SELECT
                COUNT(*) AS total_consultations,
                COUNT(*) FILTER (WHERE status = 'COMPLETED') AS completed_consultations,
                COUNT(*) FILTER (WHERE status = 'IN_PROGRESS') AS in_progress_consultations
            FROM consultations
            """
            trend_query = """
            SELECT DATE(created_at) AS day, COUNT(*) AS count
            FROM consultations
            WHERE created_at >= (CURRENT_DATE - INTERVAL '6 days')
            GROUP BY DATE(created_at)
            ORDER BY day ASC
            """
            metrics_result = database_manager.execute_with_retry(metrics_query)
            trend_result = database_manager.execute_with_retry(trend_query)
        else:
            metrics_query = """
            SELECT
                COUNT(*) AS total_consultations,
                COUNT(*) FILTER (WHERE status = 'COMPLETED') AS completed_consultations,
                COUNT(*) FILTER (WHERE status = 'IN_PROGRESS') AS in_progress_consultations
            FROM consultations
            WHERE user_id = %s
            """
            trend_query = """
            SELECT DATE(created_at) AS day, COUNT(*) AS count
            FROM consultations
            WHERE user_id = %s
              AND created_at >= (CURRENT_DATE - INTERVAL '6 days')
            GROUP BY DATE(created_at)
            ORDER BY day ASC
            """
            metrics_result = database_manager.execute_with_retry(metrics_query, (user_id,))
            trend_result = database_manager.execute_with_retry(trend_query, (user_id,))

        total_consultations = 0
        completed_consultations = 0
        in_progress_consultations = 0
        if metrics_result and len(metrics_result) > 0:
            total_consultations = metrics_result[0][0] or 0
            completed_consultations = metrics_result[0][1] or 0
            in_progress_consultations = metrics_result[0][2] or 0

        today = datetime.now(timezone.utc).date()
        day_labels = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
        trend_map = {}
        for row in trend_result or []:
            day = row[0]
            count = row[1] or 0
            if hasattr(day, 'isoformat'):
                trend_map[day.isoformat()] = int(count)

        consultation_trend = [
            {
                'date': day.isoformat(),
                'label': day.strftime('%a'),
                'count': trend_map.get(day.isoformat(), 0)
            }
            for day in day_labels
        ]
        
        profile = {
            'user_id': user_id,
            'email': session.get('user_id'),  # Assuming user_id is email
            'role': user_role,
            'role_display': format_role_display(user_role),
            'hospital_id': user_hospital,
            'menu_items': rbac_service.get_sidebar_menu_items(user_role),
            'last_login_at': last_login_at,
            'email_verified': email_verified,
            'metrics': {
                'total_consultations': int(total_consultations),
                'completed_consultations': int(completed_consultations),
                'in_progress_consultations': int(in_progress_consultations),
                'consultation_trend_last_7_days': consultation_trend
            }
        }
        
        if doctor_result:
            profile['name'] = doctor_result[0][0]
            profile['specialty'] = doctor_result[0][1]
            profile['signature_url'] = doctor_result[0][2]
            profile['availability'] = doctor_result[0][3]
            profile['hospital_name'] = doctor_result[0][4]
        else:
            profile['name'] = session.get('user_name', user_id)
        
        return jsonify({
            'success': True,
            'profile': profile
        })
        
    except Exception as e:
        logger.error(f"Failed to get profile: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to retrieve profile'}), 500


# CloudWatch Logs Endpoint

@hospital_bp.route('/logs', methods=['GET'])
@login_required
@require_role('DeveloperAdmin')
def get_logs():
    """Get CloudWatch logs (DeveloperAdmin only)"""
    try:
        if not cloudwatch_service:
            return jsonify({
                'success': False,
                'message': 'CloudWatch service not configured',
                'required_env': ['CLOUDWATCH_LOG_GROUP_NAME', 'AWS_CLOUDWATCH_REGION'],
                'configured': {
                    'CLOUDWATCH_LOG_GROUP_NAME': bool(os.getenv('CLOUDWATCH_LOG_GROUP_NAME')),
                    'AWS_CLOUDWATCH_REGION': bool(os.getenv('AWS_CLOUDWATCH_REGION'))
                }
            }), 503
        
        # Parse query parameters
        start_time_str = request.args.get('start_time', '')
        end_time_str = request.args.get('end_time', '')
        filter_pattern = request.args.get('filter_pattern', '')
        search = request.args.get('search', '')
        next_token = request.args.get('next_token', '')
        
        try:
            limit = min(int(request.args.get('limit', 100)), 1000)
        except ValueError:
            limit = 100
        
        # Parse dates
        from datetime import datetime, timedelta
        
        if start_time_str:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        else:
            start_time = datetime.now() - timedelta(hours=24)
        
        if end_time_str:
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        else:
            end_time = datetime.now()
        
        # Get logs
        if search:
            logs = cloudwatch_service.search_logs(search, start_time, end_time, limit)
            result = {
                'success': True,
                'logs': logs,
                'next_token': None,
                'has_more': False
            }
        else:
            result = cloudwatch_service.get_log_events(
                next_token=next_token if next_token else None,
                start_time=start_time,
                end_time=end_time,
                filter_pattern=filter_pattern if filter_pattern else None,
                limit=limit
            )
            result['success'] = True
            result['logs'] = result.pop('events', [])
        
        return jsonify(result)
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', 'CloudWatch client error')
        logger.error(f"CloudWatch API error while fetching logs: {error_code} - {error_message}")

        status = 500
        user_message = f"CloudWatch error: {error_code}"
        if error_code in {'AccessDeniedException', 'UnauthorizedOperation'}:
            status = 403
            user_message = "CloudWatch access denied for ECS task role"
        elif error_code in {'ResourceNotFoundException'}:
            status = 404
            user_message = "Configured CloudWatch log group was not found"
        elif error_code in {'InvalidParameterException', 'InvalidParameterValueException'}:
            status = 400
            user_message = "Invalid CloudWatch logs query parameters"

        return jsonify({
            'success': False,
            'message': user_message,
            'error_code': error_code,
            'error_detail': error_message
        }), status
    except Exception as e:
        logger.error(f"Failed to get logs: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve logs',
            'error_detail': str(e)
        }), 500


# Thank You Page Route

@hospital_bp.route('/thank-you', methods=['GET'])
@login_required
def thank_you():
    """Thank you page data"""
    import random
    
    messages = [
        "Prescription finalized successfully!",
        "Great work! Your prescription is ready.",
        "All set! Prescription has been finalized.",
        "Success! Your prescription is complete.",
        "Excellent! Prescription finalized and ready for download."
    ]
    
    return jsonify({
        'success': True,
        'message': random.choice(messages)
    })
