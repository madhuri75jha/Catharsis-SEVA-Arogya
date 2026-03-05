"""Prescription Management API Routes"""
import logging
from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Create blueprint
prescription_bp = Blueprint('prescriptions', __name__, url_prefix='/api/v1/prescriptions')

# Global service instances (will be initialized by app.py)
prescription_service = None
rbac_service = None
pdf_generator = None
bedrock_client = None
database_manager = None


def init_prescription_routes(presc_service, rbac_svc, pdf_gen, bedrock=None, db_manager=None):
    """Initialize prescription routes with service instances"""
    global prescription_service, rbac_service, pdf_generator, bedrock_client, database_manager
    # Backward compatibility: older callers pass 4 args with db_manager as 4th param.
    if db_manager is None and bedrock is not None and hasattr(bedrock, 'execute_with_retry'):
        db_manager = bedrock
        bedrock = None

    prescription_service = presc_service
    rbac_service = rbac_svc
    pdf_generator = pdf_gen
    bedrock_client = bedrock
    database_manager = db_manager
    logger.info("Prescription routes initialized")


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


@prescription_bp.route('', methods=['GET'])
@login_required
def get_prescriptions():
    """
    Get list of prescriptions with filtering and pagination
    
    Query Parameters:
        - search: Search query for patient name or prescription ID
        - doctor_id: Filter by doctor
        - start_date: Filter by created_at >= start_date
        - end_date: Filter by created_at <= end_date
        - state: Filter by state (Draft, InProgress, Finalized, Deleted)
        - limit: Number of results (default 50, max 100)
        - offset: Pagination offset (default 0)
    """
    try:
        user_id = session.get('user_id')
        user_role = rbac_service.get_user_role(user_id)
        user_hospital = rbac_service.get_user_hospital(user_id)
        
        # Parse query parameters
        search = request.args.get('search', '').strip()
        doctor_id = request.args.get('doctor_id', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        state = request.args.get('state', '').strip()
        
        try:
            limit = min(int(request.args.get('limit', 50)), 100)
            offset = int(request.args.get('offset', 0))
        except ValueError:
            limit, offset = 50, 0
        
        # Build WHERE clause based on role
        where_clauses = [rbac_service.get_prescription_filter_sql(user_id, user_role, user_hospital)]
        params = []
        
        # Add search filter
        if search:
            where_clauses.append("(patient_name ILIKE %s OR CAST(prescription_id AS TEXT) LIKE %s)")
            params.extend([f'%{search}%', f'%{search}%'])
        
        # Add doctor filter
        if doctor_id:
            where_clauses.append("created_by_doctor_id = %s")
            params.append(doctor_id)
        
        # Add date range filters
        if start_date:
            where_clauses.append("created_at >= %s")
            params.append(start_date)
        if end_date:
            where_clauses.append("created_at <= %s")
            params.append(end_date)
        
        # Add state filter
        if state and state in ['Draft', 'InProgress', 'Finalized', 'Deleted']:
            where_clauses.append("state = %s")
            params.append(state)
        
        where_sql = " AND ".join(where_clauses)
        
        # Query prescriptions
        query = f"""
        SELECT p.prescription_id, p.patient_name, p.state, p.created_at,
               p.created_by_doctor_id, p.sections, d.name as doctor_name
        FROM prescriptions p
        LEFT JOIN doctors d ON p.created_by_doctor_id = d.doctor_id
        WHERE {where_sql}
        ORDER BY p.created_at DESC
        LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        
        results = database_manager.execute_with_retry(query, tuple(params))
        
        # Count total
        count_query = f"SELECT COUNT(*) FROM prescriptions p WHERE {where_sql}"
        count_result = database_manager.execute_with_retry(count_query, tuple(params[:-2]))
        total = count_result[0][0] if count_result else 0
        
        # Format prescriptions
        prescriptions = []
        if results:
            for row in results:
                sections = json.loads(row[5]) if isinstance(row[5], str) else row[5]
                
                # Build section statuses summary
                section_statuses = {}
                for section in sections:
                    section_statuses[section['key']] = section.get('status', 'Pending')
                
                prescriptions.append({
                    'prescription_id': str(row[0]),
                    'patient_name': row[1],
                    'state': row[2],
                    'created_at': row[3].isoformat() if row[3] else None,
                    'doctor_id': row[4],
                    'doctor_name': row[6] or 'Unknown',
                    'section_statuses': section_statuses
                })
        
        return jsonify({
            'success': True,
            'prescriptions': prescriptions,
            'total': total,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        logger.error(f"Failed to get prescriptions: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to retrieve prescriptions'}), 500


@prescription_bp.route('/<prescription_id>', methods=['GET'])
@login_required
def get_prescription(prescription_id):
    """Get single prescription with full details"""
    try:
        user_id = session.get('user_id')
        user_role = rbac_service.get_user_role(user_id)
        
        # Get prescription with permissions
        prescription = prescription_service.get_prescription_with_permissions(
            prescription_id, user_id, user_role
        )
        
        if not prescription:
            return jsonify({'success': False, 'message': 'Prescription not found'}), 404
        
        # Check view permission
        has_permission, error_msg = rbac_service.check_permission(user_id, prescription, 'view')
        if not has_permission:
            return jsonify({'success': False, 'message': error_msg}), 403
        
        # Get doctor name
        doctor_query = "SELECT name, specialty FROM doctors WHERE doctor_id = %s"
        doctor_result = database_manager.execute_with_retry(doctor_query, (prescription['created_by_doctor_id'],))
        if doctor_result:
            prescription['doctor_name'] = doctor_result[0][0]
            prescription['doctor_specialty'] = doctor_result[0][1]
        
        # Get hospital name
        hospital_query = "SELECT name FROM hospitals WHERE hospital_id = %s"
        hospital_result = database_manager.execute_with_retry(hospital_query, (prescription['hospital_id'],))
        if hospital_result:
            prescription['hospital_name'] = hospital_result[0][0]
        
        # Get audio files from consultation
        if prescription.get('consultation_id'):
            audio_query = """
            SELECT audio_s3_key, transcript_text, clip_order
            FROM transcriptions
            WHERE consultation_id = %s
            ORDER BY clip_order ASC
            """
            audio_results = database_manager.execute_with_retry(audio_query, (prescription['consultation_id'],))
            
            audio_files = []
            if audio_results:
                for audio_row in audio_results:
                    audio_files.append({
                        'audio_s3_key': audio_row[0],
                        'transcription_text': audio_row[1],
                        'clip_order': audio_row[2]
                    })
            prescription['audio_files'] = audio_files
        
        return jsonify({
            'success': True,
            'prescription': prescription
        })
        
    except Exception as e:
        logger.error(f"Failed to get prescription {prescription_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to retrieve prescription'}), 500


@prescription_bp.route('', methods=['POST'])
@login_required
def create_prescription():
    """Create new prescription in Draft state"""
    try:
        data = request.get_json()
        consultation_id = data.get('consultation_id', '')
        hospital_id = data.get('hospital_id', 'default')
        patient_name = data.get('patient_name', '')
        
        if not consultation_id or not patient_name:
            return jsonify({'success': False, 'message': 'consultation_id and patient_name required'}), 400
        
        user_id = session.get('user_id')
        
        # Create prescription
        prescription_id = prescription_service.create_prescription(
            user_id, consultation_id, hospital_id, patient_name
        )
        
        if prescription_id:
            logger.info(f"Prescription created: {prescription_id}")
            return jsonify({
                'success': True,
                'prescription_id': prescription_id,
                'state': 'Draft'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to create prescription'}), 500
            
    except Exception as e:
        logger.error(f"Failed to create prescription: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to create prescription'}), 500


@prescription_bp.route('/<prescription_id>/transition-to-in-progress', methods=['POST'])
@login_required
def transition_to_in_progress(prescription_id):
    """Transition prescription from Draft to InProgress and load Bedrock content"""
    try:
        data = request.get_json()
        
        user_id = session.get('user_id')
        
        # Get prescription
        prescription = prescription_service.get_prescription_with_permissions(
            prescription_id, user_id, rbac_service.get_user_role(user_id)
        )
        
        if not prescription:
            return jsonify({'success': False, 'message': 'Prescription not found'}), 404
        
        # Check if user is creator
        if prescription['created_by_doctor_id'] != user_id:
            return jsonify({'success': False, 'message': 'Only creator can transition prescription'}), 403
        
        # Get transcript from consultation
        consultation_id = prescription.get('consultation_id')
        if not consultation_id:
            return jsonify({'success': False, 'message': 'No consultation linked to prescription'}), 400
        
        transcript_query = "SELECT merged_transcript_text FROM consultations WHERE consultation_id = %s"
        transcript_result = database_manager.execute_with_retry(transcript_query, (consultation_id,))
        
        if not transcript_result or not transcript_result[0][0]:
            return jsonify({'success': False, 'message': 'No transcript available'}), 400
        
        transcript_text = transcript_result[0][0]
        
        # Extract prescription sections using Bedrock
        bedrock_sections = bedrock_client.extract_prescription_sections(transcript_text)
        
        if not bedrock_sections:
            return jsonify({'success': False, 'message': 'Failed to extract prescription sections'}), 500
        
        # Prepare bedrock payload
        bedrock_payload = {
            'sections': bedrock_sections,
            'timestamp': datetime.now().isoformat(),
            'model': bedrock_client.model_id
        }
        
        # Transition to InProgress
        success = prescription_service.transition_to_in_progress(prescription_id, bedrock_payload)
        
        if success:
            # Get updated prescription
            updated_prescription = prescription_service.get_prescription_with_permissions(
                prescription_id, user_id, rbac_service.get_user_role(user_id)
            )
            
            return jsonify({
                'success': True,
                'state': 'InProgress',
                'sections': updated_prescription['sections']
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to transition prescription'}), 500
            
    except Exception as e:
        logger.error(f"Failed to transition prescription {prescription_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to transition prescription'}), 500


@prescription_bp.route('/<prescription_id>/sections/<section_key>/approve', methods=['POST'])
@login_required
def approve_section(prescription_id, section_key):
    """Approve a prescription section"""
    try:
        user_id = session.get('user_id')
        
        success = prescription_service.approve_section(prescription_id, section_key, user_id)
        
        if success:
            can_finalize = prescription_service.can_finalize(prescription_id)
            
            return jsonify({
                'success': True,
                'section_key': section_key,
                'status': 'Approved',
                'can_finalize': can_finalize
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to approve section'}), 500
            
    except Exception as e:
        logger.error(f"Failed to approve section: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to approve section'}), 500


@prescription_bp.route('/<prescription_id>/sections/<section_key>/reject', methods=['POST'])
@login_required
def reject_section(prescription_id, section_key):
    """Reject a prescription section (enables editing)"""
    try:
        user_id = session.get('user_id')
        
        success = prescription_service.reject_section(prescription_id, section_key, user_id)
        
        if success:
            return jsonify({
                'success': True,
                'section_key': section_key,
                'status': 'Rejected'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to reject section'}), 500
            
    except Exception as e:
        logger.error(f"Failed to reject section: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to reject section'}), 500


@prescription_bp.route('/<prescription_id>/sections/<section_key>', methods=['PUT'])
@login_required
def update_section(prescription_id, section_key):
    """Update section content (after rejection)"""
    try:
        data = request.get_json()
        content = data.get('content', '')
        
        if not content:
            return jsonify({'success': False, 'message': 'Content required'}), 400
        
        success = prescription_service.update_section_content(prescription_id, section_key, content)
        
        if success:
            return jsonify({
                'success': True,
                'section_key': section_key,
                'status': 'Pending'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to update section'}), 500
            
    except Exception as e:
        logger.error(f"Failed to update section: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to update section'}), 500


@prescription_bp.route('/<prescription_id>/finalize', methods=['POST'])
@login_required
def finalize_prescription(prescription_id):
    """Finalize prescription (all sections must be approved)"""
    try:
        user_id = session.get('user_id')
        
        # Get prescription
        prescription = prescription_service.get_prescription_with_permissions(
            prescription_id, user_id, rbac_service.get_user_role(user_id)
        )
        
        if not prescription:
            return jsonify({'success': False, 'message': 'Prescription not found'}), 404
        
        # Check permission
        has_permission, error_msg = rbac_service.check_permission(user_id, prescription, 'finalize')
        if not has_permission:
            return jsonify({'success': False, 'message': error_msg}), 403
        
        # Finalize
        success = prescription_service.finalize_prescription(prescription_id, user_id)
        
        if success:
            return jsonify({
                'success': True,
                'state': 'Finalized',
                'finalized_at': datetime.now().isoformat(),
                'redirect_url': '/thank-you'
            })
        else:
            return jsonify({'success': False, 'message': 'Cannot finalize: not all required sections approved'}), 400
            
    except Exception as e:
        logger.error(f"Failed to finalize prescription {prescription_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to finalize prescription'}), 500


@prescription_bp.route('/<prescription_id>/pdf', methods=['POST'])
@login_required
def generate_pdf(prescription_id):
    """Generate PDF on-demand and return signed URL"""
    try:
        user_id = session.get('user_id')
        user_role = rbac_service.get_user_role(user_id)
        
        # Get prescription
        prescription = prescription_service.get_prescription_with_permissions(
            prescription_id, user_id, user_role
        )
        
        if not prescription:
            return jsonify({'success': False, 'message': 'Prescription not found'}), 404
        
        # Check view permission
        has_permission, error_msg = rbac_service.check_permission(user_id, prescription, 'view')
        if not has_permission:
            return jsonify({'success': False, 'message': error_msg}), 403
        
        # Get hospital data
        hospital_query = "SELECT * FROM hospitals WHERE hospital_id = %s"
        hospital_result = database_manager.execute_with_retry(hospital_query, (prescription['hospital_id'],))
        
        if not hospital_result:
            return jsonify({'success': False, 'message': 'Hospital not found'}), 404
        
        hospital_row = hospital_result[0]
        hospital = {
            'hospital_id': hospital_row[0],
            'name': hospital_row[1],
            'address': hospital_row[2],
            'phone': hospital_row[3],
            'email': hospital_row[4],
            'registration_number': hospital_row[5],
            'website': hospital_row[6],
            'logo_url': hospital_row[7]
        }
        
        # Get doctor info
        doctor_query = "SELECT name, specialty, signature_url FROM doctors WHERE doctor_id = %s"
        doctor_result = database_manager.execute_with_retry(doctor_query, (prescription['created_by_doctor_id'],))
        if doctor_result:
            prescription['doctor_name'] = doctor_result[0][0]
            prescription['doctor_specialty'] = doctor_result[0][1]
            prescription['doctor_signature_url'] = doctor_result[0][2]
        
        # Generate PDF
        s3_key = pdf_generator.generate_prescription_pdf(prescription, hospital)
        
        if not s3_key:
            return jsonify({'success': False, 'message': 'Failed to generate PDF'}), 500
        
        # Update prescription with S3 key
        update_query = "UPDATE prescriptions SET s3_key = %s WHERE prescription_id = %s"
        database_manager.execute_with_retry(update_query, (s3_key, prescription_id))
        
        # Get signed URL
        download_url = pdf_generator.get_signed_url(s3_key, expiration=3600)
        
        if download_url:
            return jsonify({
                'success': True,
                'download_url': download_url,
                'expires_in': 3600
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to generate download URL'}), 500
            
    except Exception as e:
        logger.error(f"Failed to generate PDF for prescription {prescription_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to generate PDF'}), 500


@prescription_bp.route('/<prescription_id>', methods=['DELETE'])
@login_required
def delete_prescription(prescription_id):
    """Soft delete prescription"""
    try:
        user_id = session.get('user_id')
        
        # Get prescription
        prescription = prescription_service.get_prescription_with_permissions(
            prescription_id, user_id, rbac_service.get_user_role(user_id)
        )
        
        if not prescription:
            return jsonify({'success': False, 'message': 'Prescription not found'}), 404
        
        # Check permission
        has_permission, error_msg = rbac_service.check_permission(user_id, prescription, 'delete')
        if not has_permission:
            return jsonify({'success': False, 'message': error_msg}), 403
        
        # Soft delete
        success = prescription_service.soft_delete(prescription_id, user_id)
        
        if success:
            from datetime import timedelta
            restore_deadline = datetime.now() + timedelta(days=30)
            
            return jsonify({
                'success': True,
                'state': 'Deleted',
                'deleted_at': datetime.now().isoformat(),
                'restore_deadline': restore_deadline.isoformat()
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to delete prescription'}), 500
            
    except Exception as e:
        logger.error(f"Failed to delete prescription {prescription_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to delete prescription'}), 500


@prescription_bp.route('/<prescription_id>/restore', methods=['POST'])
@login_required
def restore_prescription(prescription_id):
    """Restore soft-deleted prescription"""
    try:
        user_id = session.get('user_id')
        
        # Get prescription
        prescription = prescription_service.get_prescription_with_permissions(
            prescription_id, user_id, rbac_service.get_user_role(user_id)
        )
        
        if not prescription:
            return jsonify({'success': False, 'message': 'Prescription not found'}), 404
        
        # Check permission
        has_permission, error_msg = rbac_service.check_permission(user_id, prescription, 'restore')
        if not has_permission:
            return jsonify({'success': False, 'message': error_msg}), 403
        
        # Restore
        success = prescription_service.restore_prescription(prescription_id, user_id)
        
        if success:
            # Get restored state
            restored_prescription = prescription_service.get_prescription_with_permissions(
                prescription_id, user_id, rbac_service.get_user_role(user_id)
            )
            
            return jsonify({
                'success': True,
                'state': restored_prescription['state'],
                'restored_at': datetime.now().isoformat()
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to restore prescription or restore window expired'}), 400
            
    except Exception as e:
        logger.error(f"Failed to restore prescription {prescription_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to restore prescription'}), 500
