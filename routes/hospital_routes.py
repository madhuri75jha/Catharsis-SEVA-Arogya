"""Hospital and User Management API Routes"""
import logging
import os
import base64
from flask import Blueprint, request, jsonify, session
from functools import wraps
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from botocore.exceptions import ClientError
from models.bedrock_extraction import HospitalConfiguration

logger = logging.getLogger(__name__)

# Create blueprint
hospital_bp = Blueprint('hospitals', __name__, url_prefix='/api/v1')

# Global service instances
rbac_service = None
database_manager = None
cloudwatch_service = None
cognito_auth_manager = None
HOSPITAL_CONFIG_DIR = Path('config/hospitals')


def init_hospital_routes(rbac_svc, db_manager, cw_service=None, auth_svc=None):
    """Initialize hospital routes with service instances"""
    global rbac_service, database_manager, cloudwatch_service, cognito_auth_manager
    rbac_service = rbac_svc
    database_manager = db_manager
    cloudwatch_service = cw_service
    cognito_auth_manager = auth_svc
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


def _can_manage_hospital_config(hospital_id: str) -> tuple[bool, str, str, str]:
    """Authorization helper for hospital-bound config endpoints."""
    user_id = session.get('user_id')
    if not user_id:
        return False, '', '', ''

    user_role = rbac_service.get_user_role(user_id)
    user_hospital = rbac_service.get_user_hospital(user_id)

    if user_role == 'Doctor':
        return False, user_id, user_role, user_hospital

    if user_role == 'HospitalAdmin' and user_hospital != hospital_id:
        return False, user_id, user_role, user_hospital

    return True, user_id, user_role, user_hospital


def _load_hospital_name(hospital_id: str) -> str:
    query = "SELECT name FROM hospitals WHERE hospital_id = %s"
    result = database_manager.execute_with_retry(query, (hospital_id,))
    if result and result[0] and result[0][0]:
        return result[0][0]
    return hospital_id


def _default_config_payload(hospital_id: str) -> dict:
    default_file = HOSPITAL_CONFIG_DIR / 'default.json'
    with open(default_file, 'r', encoding='utf-8') as f:
        payload = json.load(f)
    payload['hospital_id'] = hospital_id
    payload['hospital_name'] = _load_hospital_name(hospital_id)
    return payload


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


# Hospital Prescription Config Endpoints

@hospital_bp.route('/hospitals/<hospital_id>/prescription-config', methods=['GET'])
@login_required
def get_prescription_config(hospital_id):
    """Get prescription form config JSON for a hospital."""
    try:
        authorized, _, _, _ = _can_manage_hospital_config(hospital_id)
        if not authorized:
            return jsonify({'success': False, 'message': 'Forbidden'}), 403

        HOSPITAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        config_file = HOSPITAL_CONFIG_DIR / f'{hospital_id}.json'

        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config_payload = json.load(f)
            source = 'hospital'
        else:
            config_payload = _default_config_payload(hospital_id)
            source = 'default_fallback'

        return jsonify({
            'success': True,
            'hospital_id': hospital_id,
            'source': source,
            'exists': config_file.exists(),
            'config': config_payload
        })
    except Exception as e:
        logger.error(f"Failed to get prescription config for {hospital_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Failed to retrieve prescription config'}), 500


@hospital_bp.route('/hospitals/<hospital_id>/prescription-config', methods=['PUT'])
@login_required
def save_prescription_config(hospital_id):
    """Save hospital-specific prescription form config JSON."""
    try:
        authorized, user_id, _, _ = _can_manage_hospital_config(hospital_id)
        if not authorized:
            return jsonify({'success': False, 'message': 'Forbidden'}), 403

        payload = request.get_json(silent=True) or {}
        config_payload = payload.get('config')
        if not isinstance(config_payload, dict):
            return jsonify({'success': False, 'message': 'config object is required'}), 400

        config_payload['hospital_id'] = hospital_id
        if not config_payload.get('hospital_name'):
            config_payload['hospital_name'] = _load_hospital_name(hospital_id)
        if not config_payload.get('version'):
            config_payload['version'] = '1.0'

        # Validate structure before writing.
        validated = HospitalConfiguration(**config_payload)
        clean_config = validated.model_dump(mode='json')

        HOSPITAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        config_file = HOSPITAL_CONFIG_DIR / f'{hospital_id}.json'
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(clean_config, f, indent=2, ensure_ascii=True)

        logger.info(f"Prescription config saved for hospital {hospital_id} by user {user_id}")
        return jsonify({'success': True, 'message': 'Prescription config saved', 'config': clean_config})
    except Exception as e:
        logger.error(f"Failed to save prescription config for {hospital_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'Failed to save prescription config: {str(e)}'}), 500


@hospital_bp.route('/hospitals/<hospital_id>/prescription-config/generate-default', methods=['POST'])
@login_required
def generate_default_prescription_config(hospital_id):
    """Generate/reset hospital config from default template."""
    try:
        authorized, user_id, _, _ = _can_manage_hospital_config(hospital_id)
        if not authorized:
            return jsonify({'success': False, 'message': 'Forbidden'}), 403

        config_payload = _default_config_payload(hospital_id)
        validated = HospitalConfiguration(**config_payload)
        clean_config = validated.model_dump(mode='json')

        HOSPITAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        config_file = HOSPITAL_CONFIG_DIR / f'{hospital_id}.json'
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(clean_config, f, indent=2, ensure_ascii=True)

        logger.info(f"Prescription config generated from default for hospital {hospital_id} by user {user_id}")
        return jsonify({
            'success': True,
            'message': 'Generated from default config',
            'config': clean_config
        })
    except Exception as e:
        logger.error(f"Failed to generate default prescription config for {hospital_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'Failed to generate default config: {str(e)}'}), 500


# Doctor Management Endpoints

@hospital_bp.route('/hospitals/<hospital_id>/doctors', methods=['GET'])
@login_required
def get_hospital_doctors(hospital_id):
    """Get list of doctors and approval statuses in a hospital."""
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
        SELECT
            COALESCE(ur.user_id, d.doctor_id) AS doctor_id,
            COALESCE(NULLIF(d.name, ''), SPLIT_PART(COALESCE(ur.user_id, d.doctor_id), '@', 1)) AS name,
            d.specialty,
            d.signature_url,
            d.availability,
            COALESCE(d.created_at, ur.created_at) AS created_at,
            COALESCE(ur.approval_status, 'Unregistered') AS approval_status
        FROM doctors d
        FULL OUTER JOIN user_roles ur
            ON ur.user_id = d.doctor_id
           AND ur.role = 'Doctor'
        WHERE COALESCE(ur.hospital_id, d.hospital_id) = %s
        ORDER BY 2 ASC
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
                    'created_at': row[5].isoformat() if row[5] else None,
                    'approval_status': row[6]
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
    """Add an existing system doctor to hospital and approve association."""
    try:
        user_id = session.get('user_id')
        user_role = rbac_service.get_user_role(user_id)
        user_hospital = rbac_service.get_user_hospital(user_id)
        
        # Check authorization
        if user_role == 'HospitalAdmin' and user_hospital != hospital_id:
            return jsonify({'success': False, 'message': 'Forbidden'}), 403
        elif user_role == 'Doctor':
            return jsonify({'success': False, 'message': 'Forbidden'}), 403
        
        data = request.get_json(silent=True) or {}
        doctor_id = (data.get('doctor_id', '') or '').strip().lower()
        
        if not doctor_id:
            return jsonify({'success': False, 'message': 'doctor_id is required'}), 400

        doctor_role_query = """
        SELECT user_id, hospital_id
        FROM user_roles
        WHERE LOWER(user_id) = LOWER(%s) AND role = 'Doctor'
        LIMIT 1
        """
        doctor_role = database_manager.execute_with_retry(doctor_role_query, (doctor_id,))

        if not doctor_role and cognito_auth_manager:
            cognito_user = cognito_auth_manager.get_user_by_username(doctor_id)
            if cognito_user:
                cognito_attrs = cognito_user.get('attributes', {})
                if cognito_attrs.get('custom:role') == 'Doctor':
                    from utils.auth_helpers import sync_user_role_from_cognito
                    sync_user_role_from_cognito(
                        database_manager,
                        cognito_user,
                        (cognito_user.get('username') or doctor_id).lower()
                    )
                    doctor_role = database_manager.execute_with_retry(doctor_role_query, (doctor_id,))

        if not doctor_role:
            return jsonify({
                'success': False,
                'message': 'Doctor is not registered in the system. Ask them to sign up first.'
            }), 404

        doctor_user_id = doctor_role[0][0]
        doctor_hospital_id = doctor_role[0][1]
        if doctor_hospital_id and doctor_hospital_id != hospital_id:
            return jsonify({
                'success': False,
                'message': f'Doctor is registered under hospital {doctor_hospital_id}.'
            }), 409

        display_name = doctor_user_id.split('@')[0].replace('.', ' ').title()

        query = """
        INSERT INTO doctors (doctor_id, hospital_id, name)
        VALUES (%s, %s, %s)
        ON CONFLICT (doctor_id) DO UPDATE
        SET hospital_id = EXCLUDED.hospital_id,
            name = COALESCE(NULLIF(EXCLUDED.name, ''), doctors.name),
            updated_at = CURRENT_TIMESTAMP
        """

        role_update_query = """
        UPDATE user_roles
        SET hospital_id = %s,
            approval_status = 'Approved',
            approved_by = %s,
            approved_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s AND role = 'Doctor'
        """
        
        database_manager.execute_with_retry(query, (doctor_user_id, hospital_id, display_name))
        database_manager.execute_with_retry(role_update_query, (hospital_id, user_id, doctor_user_id))
        
        logger.info(f"Doctor {doctor_user_id} added to hospital {hospital_id}")
        
        return jsonify({
            'success': True,
            'message': 'Doctor added successfully',
            'approval_status': 'Approved'
        })
        
    except Exception as e:
        logger.error(f"Failed to add doctor to hospital {hospital_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to add doctor'}), 500


@hospital_bp.route('/hospitals/<hospital_id>/doctors/<doctor_id>/approve', methods=['POST'])
@login_required
def approve_hospital_doctor(hospital_id, doctor_id):
    """Approve a pending doctor for a hospital."""
    try:
        user_id = session.get('user_id')
        user_role = rbac_service.get_user_role(user_id)
        user_hospital = rbac_service.get_user_hospital(user_id)

        if user_role == 'HospitalAdmin' and user_hospital != hospital_id:
            return jsonify({'success': False, 'message': 'Forbidden'}), 403
        elif user_role == 'Doctor':
            return jsonify({'success': False, 'message': 'Forbidden'}), 403

        with database_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE user_roles
                    SET approval_status = 'Approved',
                        approved_by = %s,
                        approved_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                      AND role = 'Doctor'
                      AND hospital_id = %s
                    RETURNING user_id
                    """,
                    (user_id, doctor_id, hospital_id)
                )
                updated = cursor.fetchone()
                if not updated:
                    conn.rollback()
                    return jsonify({'success': False, 'message': 'Doctor not found for this hospital'}), 404

                cursor.execute("SELECT name FROM doctors WHERE doctor_id = %s", (doctor_id,))
                existing_doctor = cursor.fetchone()
                if not existing_doctor:
                    default_name = doctor_id.split('@')[0].replace('.', ' ').title()
                    cursor.execute(
                        """
                        INSERT INTO doctors (doctor_id, hospital_id, name)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (doctor_id) DO UPDATE
                        SET hospital_id = EXCLUDED.hospital_id,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        (doctor_id, hospital_id, default_name)
                    )
                conn.commit()

        logger.info(f"Doctor {doctor_id} approved for hospital {hospital_id} by {user_id}")
        return jsonify({'success': True, 'message': 'Doctor approved successfully'})

    except Exception as e:
        logger.error(f"Failed to approve doctor {doctor_id} for hospital {hospital_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to approve doctor'}), 500


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
