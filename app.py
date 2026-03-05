"""
SEVA Arogya - Flask Application
Voice-enabled clinical note capture and prescription generation system
"""

# Apply eventlet monkey patching FIRST (before any other imports)
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
from flask_cors import CORS
from flask_socketio import SocketIO
from functools import wraps
import os
import json
import logging
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import urlopen
from collections import deque
from dotenv import load_dotenv

# Import AWS service managers
from aws_services.config_manager import ConfigManager
from aws_services.auth_manager import AuthManager
from aws_services.storage_manager import StorageManager
from aws_services.transcribe_manager import TranscribeManager
from aws_services.comprehend_manager import ComprehendManager
from aws_services.database_manager import DatabaseManager
from aws_services.connectivity_checker import AWSConnectivityChecker
from aws_services.transcription_queue_manager import TranscriptionQueueManager
from aws_services.consultation_session_manager import ConsultationSessionManager

# Import models
from models.prescription import Prescription
from models.transcription import Transcription

# Import utilities
from utils.logger import setup_logging
from utils.error_handler import handle_aws_error, AuthenticationError

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Initialize SocketIO (will be configured in init_app)
socketio = None

# Global service managers (initialized in init_app)
config_manager = None
auth_manager = None
storage_manager = None
transcribe_manager = None
comprehend_manager = None
database_manager = None
transcription_queue_manager = None
consultation_session_manager = None


def init_app():
    """Initialize application with AWS services"""
    global config_manager, auth_manager, storage_manager, transcribe_manager, comprehend_manager, database_manager, socketio, transcription_queue_manager, consultation_session_manager
    
    try:
        # Setup logging
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        json_format = os.getenv('FLASK_ENV', 'production') == 'production'
        setup_logging(log_level=log_level, json_format=json_format)
        
        logger = logging.getLogger(__name__)
        logger.info("Initializing SEVA Arogya application")
        
        # Initialize configuration manager
        config_manager = ConfigManager()
        
        # Validate required configuration
        if not config_manager.validate_required_config():
            raise Exception("Required configuration validation failed")
        
        # Get Flask secret key from Secrets Manager
        flask_secret = config_manager.get_flask_secret_key()
        if flask_secret:
            app.secret_key = flask_secret
        else:
            app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
            logger.warning("Using fallback secret key from environment")
        
        # Configure Flask app
        app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
        
        # Configure CORS
        cors_origins = config_manager.get('cors_allowed_origins', [])
        if cors_origins and cors_origins[0]:  # Check if not empty
            CORS(app, origins=cors_origins, supports_credentials=True)
            logger.info(f"CORS configured with origins: {cors_origins}")
        
        # Initialize SocketIO
        socketio = SocketIO(
            app,
            cors_allowed_origins=cors_origins if cors_origins and cors_origins[0] else '*',
            async_mode='eventlet',
            ping_timeout=60,
            ping_interval=25,
            max_http_buffer_size=1024 * 1024,  # 1MB max message size
            logger=False,
            engineio_logger=False
        )
        logger.info("Flask-SocketIO initialized with eventlet async mode")
        
        # Initialize AWS service managers
        region = config_manager.get('aws_region')
        
        # Auth Manager
        auth_manager = AuthManager(
            region=region,
            user_pool_id=config_manager.get('cognito_user_pool_id'),
            client_id=config_manager.get('cognito_client_id'),
            client_secret=config_manager.get('cognito_client_secret')
        )
        
        # Storage Manager
        storage_manager = StorageManager(
            region=region,
            audio_bucket=config_manager.get('s3_audio_bucket'),
            pdf_bucket=config_manager.get('s3_pdf_bucket')
        )
        
        # Transcribe Manager
        transcribe_manager = TranscribeManager(region=region)
        
        # Comprehend Medical is not available in all AWS regions.
        # Use dedicated comprehend region config instead of generic AWS_REGION.
        comprehend_region = config_manager.get('aws_comprehend_region', region)
        comprehend_manager = ComprehendManager(region=comprehend_region)
        
        # Database Manager
        db_credentials = config_manager.get_database_credentials()
        if db_credentials:
            database_manager = DatabaseManager(db_credentials)
            
            # Validate database connection
            if not database_manager.health_check():
                logger.warning("Database health check failed during initialization")
            else:
                logger.info("Database connection validated successfully")
                
                # Create tables if they don't exist
                try:
                    database_manager.execute_with_retry(Prescription.create_table_sql())
                    database_manager.execute_with_retry(Transcription.create_table_sql())
                    database_manager.execute_with_retry("""
                    CREATE TABLE IF NOT EXISTS consultations (
                        consultation_id VARCHAR(64) PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        status VARCHAR(50) NOT NULL DEFAULT 'IN_PROGRESS',
                        merged_transcript_text TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE INDEX IF NOT EXISTS idx_consultations_user_id ON consultations(user_id);
                    CREATE INDEX IF NOT EXISTS idx_consultations_created_at ON consultations(created_at DESC);
                    """)
                    database_manager.execute_with_retry("""
                    ALTER TABLE transcriptions
                    ADD COLUMN IF NOT EXISTS consultation_id VARCHAR(64),
                    ADD COLUMN IF NOT EXISTS clip_order INTEGER DEFAULT 1;
                    """)
                    database_manager.execute_with_retry("""
                    CREATE INDEX IF NOT EXISTS idx_transcriptions_consultation_id
                    ON transcriptions(consultation_id);
                    """)
                    logger.info("Database tables created/verified")
                except Exception as e:
                    logger.error(f"Failed to create database tables: {str(e)}")
                
                # Run database migrations
                try:
                    from migrations.migration_manager import MigrationManager
                    migration_manager = MigrationManager(database_manager)
                    migration_success = migration_manager.run_migrations()
                    
                    if migration_success:
                        logger.info("Database migrations completed successfully")
                    else:
                        logger.warning("Some database migrations failed - check logs for details")
                except Exception as e:
                    logger.error(f"Failed to run database migrations: {str(e)}")
                    # Don't fail startup if migrations fail - allow app to start
                    logger.warning("Application starting despite migration failures")
        else:
            logger.error("Database credentials not available")
            raise Exception("Database configuration failed")
        
        # Initialize Transcription Queue Manager
        max_concurrent_jobs = config_manager.get('max_concurrent_transcription_jobs', 10)
        max_retries = config_manager.get('transcription_max_retries', 3)
        transcription_queue_manager = TranscriptionQueueManager(
            max_concurrent_jobs=max_concurrent_jobs,
            max_retries=max_retries
        )
        logger.info(f"Transcription Queue Manager initialized: max_concurrent={max_concurrent_jobs}, max_retries={max_retries}")
        
        # Initialize Consultation Session Manager
        consultation_session_manager = ConsultationSessionManager(database_manager)
        logger.info("Consultation Session Manager initialized")
        
        # Initialize Cleanup Scheduler for prescription soft delete
        cleanup_enabled = os.getenv('CLEANUP_SCHEDULE_ENABLED', 'true').lower() == 'true'
        if cleanup_enabled:
            from services.cleanup_scheduler import CleanupScheduler
            cleanup_scheduler = CleanupScheduler(database_manager, storage_manager)
            cleanup_scheduler.start()
            logger.info("Cleanup Scheduler initialized and started")
        else:
            logger.info("Cleanup Scheduler disabled by configuration")
        
        # Start background cleanup task for job metadata
        def cleanup_job_metadata():
            """Background task to clean up old job metadata every hour"""
            while True:
                try:
                    eventlet.sleep(3600)  # Sleep for 1 hour
                    if transcription_queue_manager:
                        removed_count = transcription_queue_manager.cleanup_old_metadata(max_age_seconds=86400)
                        if removed_count > 0:
                            logger.info(f"Cleaned up {removed_count} old job metadata entries")
                except Exception as e:
                    logger.error(f"Error in cleanup task: {str(e)}")
        
        # Start cleanup task in background
        eventlet.spawn(cleanup_job_metadata)
        logger.info("Background cleanup task started")
        
        # Initialize SocketIO handlers
        from socketio_handlers import init_socketio_handlers
        init_socketio_handlers(socketio, database_manager, storage_manager, config_manager)
        
        # Register prescription and hospital management blueprints
        from routes.prescription_routes import prescription_bp, init_prescription_routes
        from routes.hospital_routes import hospital_bp, init_hospital_routes
        from services.prescription_service import PrescriptionService
        from services.rbac_service import RBACService
        from services.pdf_generator import PDFGenerator
        from services.cloudwatch_service import CloudWatchService
        from services.lambda_pdf_service import LambdaPDFService
        
        # Initialize services
        prescription_service = PrescriptionService(database_manager)
        rbac_service = RBACService(database_manager)
        pdf_generator = PDFGenerator(storage_manager)
        lambda_pdf_service = None
        lambda_function_name = os.getenv('PRESCRIPTION_PDF_LAMBDA_NAME', '').strip()
        if lambda_function_name:
            lambda_pdf_service = LambdaPDFService(region=region, function_name=lambda_function_name)
            logger.info(f"Lambda PDF service enabled: function={lambda_function_name}")
        else:
            logger.info("Lambda PDF service disabled: PRESCRIPTION_PDF_LAMBDA_NAME is not set")
        
        # Initialize CloudWatch service if configured
        cloudwatch_log_group = os.getenv('CLOUDWATCH_LOG_GROUP_NAME')
        cloudwatch_region = os.getenv('AWS_CLOUDWATCH_REGION', region)
        cloudwatch_service = None
        if cloudwatch_log_group:
            cloudwatch_service = CloudWatchService(cloudwatch_log_group, cloudwatch_region)
            logger.info(f"CloudWatch service initialized: log_group={cloudwatch_log_group}")
        else:
            logger.warning("CloudWatch service disabled: CLOUDWATCH_LOG_GROUP_NAME is not set")
        
        # Initialize route blueprints with services
        init_prescription_routes(
            prescription_service,
            rbac_service,
            pdf_generator,
            db_manager=database_manager,
            lambda_pdf_svc=lambda_pdf_service,
            cfg_manager=config_manager
        )
        init_hospital_routes(rbac_service, database_manager, cloudwatch_service)
        
        # Register blueprints
        app.register_blueprint(prescription_bp)
        app.register_blueprint(hospital_bp)
        logger.info("Prescription and hospital management routes registered")
        
        logger.info("Application initialized successfully")
        
    except Exception as e:
        logger.error(f"Application initialization failed: {str(e)}")
        raise


# Initialize app on startup
init_app()


# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # Validate token if present
        access_token = session.get('access_token')
        if access_token and auth_manager:
            user_info = auth_manager.validate_token(access_token)
            if not user_info:
                # Token invalid or expired, try to refresh
                refresh_token = session.get('refresh_token')
                if refresh_token:
                    new_tokens = auth_manager.refresh_token(refresh_token)
                    if new_tokens:
                        # Update session with new tokens
                        session['access_token'] = new_tokens['access_token']
                        session['id_token'] = new_tokens['id_token']
                        return f(*args, **kwargs)
                
                # Refresh failed, clear session and redirect to login
                session.clear()
                return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function


# Routes
@app.route('/')
def index():
    """Redirect to login or home based on session"""
    if 'user_id' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))


def _get_request_data() -> dict:
    """Safely parse JSON or form data from a request."""
    data = request.get_json(silent=True)
    if not data:
        data = request.form.to_dict()
    return data or {}


def _read_log_tail(log_path: str, lines: int) -> str:
    """Read last N lines from a log file."""
    if lines <= 0:
        return ""
    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
        return "".join(deque(f, maxlen=lines))


def _rebuild_consultation_transcript(consultation_id: str, user_id: str) -> str:
    """
    Rebuild merged transcript text for a consultation from all clip rows.

    Returns merged transcript text (may be empty string).
    """
    merged_query = """
    SELECT COALESCE(
        STRING_AGG(NULLIF(TRIM(transcript_text), ''), ' ' ORDER BY clip_order, created_at),
        ''
    ) AS merged_transcript
    FROM transcriptions
    WHERE consultation_id = %s AND user_id = %s
    """
    merged_result = database_manager.execute_with_retry(merged_query, (consultation_id, user_id))
    merged_text = ""
    if merged_result and len(merged_result) > 0 and merged_result[0][0]:
        merged_text = merged_result[0][0]

    status_query = """
    SELECT
      CASE
        WHEN c.status = 'COMPLETED' THEN 'COMPLETED'
        WHEN COUNT(*) FILTER (WHERE t.status = 'FAILED') > 0 THEN 'FAILED'
        ELSE 'IN_PROGRESS'
      END AS consultation_status
    FROM consultations c
    LEFT JOIN transcriptions t
      ON t.consultation_id = c.consultation_id
     AND t.user_id = c.user_id
    WHERE c.consultation_id = %s AND c.user_id = %s
    GROUP BY c.status
    """
    status_result = database_manager.execute_with_retry(status_query, (consultation_id, user_id))
    consultation_status = 'IN_PROGRESS'
    if status_result and len(status_result) > 0 and status_result[0][0]:
        consultation_status = status_result[0][0]

    update_query = """
    UPDATE consultations
    SET merged_transcript_text = %s, status = %s, updated_at = CURRENT_TIMESTAMP
    WHERE consultation_id = %s AND user_id = %s
    """
    database_manager.execute_with_retry(
        update_query, (merged_text, consultation_status, consultation_id, user_id)
    )

    return merged_text


@app.route('/login')
def login():
    """Login page"""
    return render_template(
        'login.html',
        google_client_id=os.getenv('GOOGLE_CLIENT_ID', '')
    )


@app.route('/debug/logs')
def debug_logs():
    """Temporary log viewer endpoint (protected by token)."""
    token = os.getenv('LOG_VIEW_TOKEN')
    provided = request.headers.get('X-Log-Token') or request.args.get('token')
    if not token or provided != token:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    log_path = os.getenv('LOG_FILE_PATH', 'logs/app.log')
    try:
        lines = int(request.args.get('lines', '200'))
    except ValueError:
        lines = 200
    lines = max(1, min(lines, 2000))

    if not os.path.exists(log_path):
        return jsonify({'success': False, 'message': f'Log file not found: {log_path}'}), 404

    try:
        content = _read_log_tail(log_path, lines)
        return app.response_class(content, mimetype='text/plain')
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to read log file: {e}")
        return jsonify({'success': False, 'message': 'Failed to read log file'}), 500


@app.route('/home')
@login_required
def home():
    """Home page - Start new consultation"""
    return render_template('home.html')


@app.route('/transcription')
@login_required
def transcription():
    """Transcription page - Voice capture and real-time transcription"""
    return render_template('transcription.html')


@app.route('/live-transcription')
@login_required
def live_transcription():
    """Live transcription page - Real-time streaming transcription"""
    return render_template('live_transcription.html')


@app.route('/final-prescription')
@login_required
def final_prescription():
    """Final prescription review page"""
    return render_template('final_prescription.html')


@app.route('/bedrock-prescription')
@login_required
def bedrock_prescription():
    """AI-assisted prescription page with Bedrock extraction"""
    return render_template('bedrock_prescription.html')


@app.route('/consultations')
@login_required
def consultations_list():
    """Consultations list page"""
    return render_template('prescriptions_list.html')


@app.route('/prescriptions')
@login_required
def prescriptions_list_legacy():
    """Legacy route - redirect prescriptions list to consultations list"""
    return redirect(url_for('consultations_list'))


@app.route('/prescriptions/<prescription_id>')
@login_required
def prescription_detail(prescription_id):
    """Single prescription detail page"""
    return render_template('prescription_detail.html', prescription_id=prescription_id)


@app.route('/prescriptions/<prescription_id>/finalize')
@login_required
def prescription_finalize(prescription_id):
    """Prescription finalization page"""
    return render_template('prescription_finalize.html', prescription_id=prescription_id)


@app.route('/thank-you')
@login_required
def thank_you_page():
    """Thank you page after prescription finalization"""
    return render_template('thank_you.html')


@app.route('/profile')
@login_required
def profile_page():
    """User profile page"""
    return render_template('profile.html')


@app.route('/hospitals')
@login_required
def hospitals_page():
    """Hospitals list page (DeveloperAdmin only)"""
    if session.get('user_role') != 'DeveloperAdmin':
        return redirect(url_for('hospital_settings_page'))
    return render_template('hospitals_list.html')


@app.route('/hospital-settings')
@app.route('/hospital-settings/<hospital_id>')
@login_required
def hospital_settings_page(hospital_id=None):
    """Hospital settings page"""
    if session.get('user_role') == 'DeveloperAdmin' and not hospital_id:
        return redirect(url_for('hospitals_page'))
    return render_template('hospital_settings.html', selected_hospital_id=hospital_id)


@app.route('/hospital-settings/prescription-config')
@app.route('/hospital-settings/<hospital_id>/prescription-config')
@login_required
def hospital_prescription_config_page(hospital_id=None):
    """Prescription configuration management page"""
    user_role = session.get('user_role')
    user_hospital = session.get('hospital_id')

    if user_role == 'DeveloperAdmin':
        if not hospital_id:
            return redirect(url_for('hospitals_page'))
        return render_template('prescription_config_settings.html', selected_hospital_id=hospital_id)

    if not user_hospital:
        return redirect(url_for('hospital_settings_page'))

    # HospitalAdmin should only edit their own hospital config.
    if hospital_id and hospital_id != user_hospital:
        return redirect(url_for('hospital_prescription_config_page', hospital_id=user_hospital))

    return render_template('prescription_config_settings.html', selected_hospital_id=user_hospital)


@app.route('/logs')
@login_required
def logs_viewer_page():
    """CloudWatch logs viewer page (DeveloperAdmin only)"""
    return render_template('logs_viewer.html')


@app.route('/consultation/<consultation_id>')
@login_required
def consultation_detail(consultation_id):
    """
    Consultation detail view
    
    Display complete consultation information including merged transcript,
    medical entities, and prescription data.
    
    Args:
        consultation_id: The consultation_id or legacy transcription_id
        
    Returns:
        Rendered consultation_detail.html template or 404 error
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Get user_id from session
        user_id = session.get('user_id')
        
        if not user_id:
            logger.warning("Consultation detail request without user_id in session")
            return redirect(url_for('login'))
        
        # Check if we should use mock data (for local development)
        use_mock_data = os.getenv('USE_MOCK_CONSULTATIONS', 'false').lower() == 'true'
        
        if use_mock_data:
            logger.info(f"Using mock consultation detail data for consultation {consultation_id}")
            from datetime import datetime, timedelta
            
            # Mock consultation data
            mock_consultations = {
                1: {
                    'consultation_id': 1,
                    'patient_name': 'Arjun Kumar',
                    'status': 'COMPLETED',
                    'transcript_text': 'Patient complains of headache and fever for the past 3 days. Temperature recorded at 101°F. Patient reports body aches and fatigue. No history of recent travel. Prescribed paracetamol for fever and advised rest.',
                    'medical_entities': [
                        {"Text": "Arjun Kumar", "Category": "PROTECTED_HEALTH_INFORMATION", "Type": "NAME", "Score": 0.99},
                        {"Text": "headache", "Category": "MEDICAL_CONDITION", "Type": "DX_NAME", "Score": 0.95},
                        {"Text": "fever", "Category": "MEDICAL_CONDITION", "Type": "DX_NAME", "Score": 0.97},
                        {"Text": "paracetamol", "Category": "MEDICATION", "Type": "GENERIC_NAME", "Score": 0.98}
                    ],
                    'created_at': datetime.now() - timedelta(hours=2),
                    'updated_at': datetime.now() - timedelta(hours=2),
                    'prescription': {
                        'prescription_id': 101,
                        'patient_name': 'Arjun Kumar',
                        'medications': [
                            {"name": "Paracetamol", "dosage": "500mg", "frequency": "Twice daily", "duration": "5 days"}
                        ],
                        'created_at': datetime.now() - timedelta(hours=2)
                    }
                },
                2: {
                    'consultation_id': 2,
                    'patient_name': 'Priya Sharma',
                    'status': 'COMPLETED',
                    'transcript_text': 'Follow-up visit for diabetes management. Blood sugar levels have improved. Patient reports better adherence to diet plan. Continue current medication regimen.',
                    'medical_entities': [
                        {"Text": "Priya Sharma", "Category": "PROTECTED_HEALTH_INFORMATION", "Type": "NAME", "Score": 0.99},
                        {"Text": "diabetes", "Category": "MEDICAL_CONDITION", "Type": "DX_NAME", "Score": 0.98}
                    ],
                    'created_at': datetime.now() - timedelta(days=1),
                    'updated_at': datetime.now() - timedelta(days=1),
                    'prescription': None
                },
                3: {
                    'consultation_id': 3,
                    'patient_name': 'Rajesh Patel',
                    'status': 'IN_PROGRESS',
                    'transcript_text': 'Patient reports chest pain and shortness of breath. ECG ordered. Awaiting test results.',
                    'medical_entities': [
                        {"Text": "Rajesh Patel", "Category": "PROTECTED_HEALTH_INFORMATION", "Type": "NAME", "Score": 0.99},
                        {"Text": "chest pain", "Category": "MEDICAL_CONDITION", "Type": "DX_NAME", "Score": 0.96},
                        {"Text": "shortness of breath", "Category": "MEDICAL_CONDITION", "Type": "DX_NAME", "Score": 0.94}
                    ],
                    'created_at': datetime.now() - timedelta(days=2),
                    'updated_at': datetime.now() - timedelta(days=2),
                    'prescription': {
                        'prescription_id': 102,
                        'patient_name': 'Rajesh Patel',
                        'medications': [
                            {"name": "Aspirin", "dosage": "75mg", "frequency": "Once daily", "duration": "Ongoing"}
                        ],
                        'created_at': datetime.now() - timedelta(days=2)
                    }
                },
                4: {
                    'consultation_id': 4,
                    'patient_name': 'Sunita Reddy',
                    'status': 'COMPLETED',
                    'transcript_text': 'Routine checkup. Blood pressure slightly elevated at 140/90. Advised lifestyle modifications including reduced salt intake and regular exercise.',
                    'medical_entities': [
                        {"Text": "Sunita Reddy", "Category": "PROTECTED_HEALTH_INFORMATION", "Type": "NAME", "Score": 0.99},
                        {"Text": "elevated blood pressure", "Category": "MEDICAL_CONDITION", "Type": "DX_NAME", "Score": 0.95}
                    ],
                    'created_at': datetime.now() - timedelta(days=3),
                    'updated_at': datetime.now() - timedelta(days=3),
                    'prescription': {
                        'prescription_id': 103,
                        'patient_name': 'Sunita Reddy',
                        'medications': [
                            {"name": "Amlodipine", "dosage": "5mg", "frequency": "Once daily", "duration": "30 days"}
                        ],
                        'created_at': datetime.now() - timedelta(days=3)
                    }
                },
                5: {
                    'consultation_id': 5,
                    'patient_name': 'Vikram Singh',
                    'status': 'COMPLETED',
                    'transcript_text': 'Patient complains of back pain after lifting heavy objects. Physical examination shows muscle strain. Prescribed pain relief medication and advised rest.',
                    'medical_entities': [
                        {"Text": "Vikram Singh", "Category": "PROTECTED_HEALTH_INFORMATION", "Type": "NAME", "Score": 0.99},
                        {"Text": "back pain", "Category": "MEDICAL_CONDITION", "Type": "DX_NAME", "Score": 0.97},
                        {"Text": "muscle strain", "Category": "MEDICAL_CONDITION", "Type": "DX_NAME", "Score": 0.94}
                    ],
                    'created_at': datetime.now() - timedelta(days=5),
                    'updated_at': datetime.now() - timedelta(days=5),
                    'prescription': None
                }
            }
            
            mock_key = int(consultation_id) if str(consultation_id).isdigit() else consultation_id
            if mock_key not in mock_consultations:
                abort(404)
            
            consultation_data = mock_consultations[mock_key]
            return render_template('consultation_detail.html', consultation=consultation_data)
        
        # Query consultation-level data first
        query_consultation = """
        SELECT
            c.consultation_id,
            c.user_id,
            c.merged_transcript_text,
            c.status,
            (
                SELECT t.medical_entities
                FROM transcriptions t
                WHERE t.consultation_id = c.consultation_id
                  AND t.user_id = c.user_id
                  AND t.medical_entities IS NOT NULL
                ORDER BY t.updated_at DESC, t.created_at DESC
                LIMIT 1
            ) AS medical_entities,
            c.created_at,
            c.updated_at
        FROM consultations c
        WHERE c.consultation_id = %s AND c.user_id = %s
        """
        consultation_result = database_manager.execute_with_retry(
            query_consultation,
            (consultation_id, user_id)
        )

        # Backward compatibility for legacy consultation links by transcription_id
        if not consultation_result and str(consultation_id).isdigit():
            legacy_query = """
            SELECT
                CAST(t.transcription_id AS VARCHAR),
                t.user_id,
                t.transcript_text,
                t.status,
                t.medical_entities,
                t.created_at,
                t.updated_at
            FROM transcriptions t
            WHERE t.transcription_id = %s AND t.user_id = %s
            """
            consultation_result = database_manager.execute_with_retry(
                legacy_query,
                (int(consultation_id), user_id)
            )

        if not consultation_result or len(consultation_result) == 0:
            logger.warning(f"Consultation {consultation_id} not found for user {user_id}")
            abort(404)

        consultation_row = consultation_result[0]
        (consultation_id_value, trans_user_id, transcript_text, status, medical_entities_json,
         created_at, updated_at) = consultation_row
        
        # Parse medical_entities JSONB
        medical_entities = []
        if medical_entities_json:
            try:
                if isinstance(medical_entities_json, str):
                    medical_entities = json.loads(medical_entities_json)
                else:
                    medical_entities = medical_entities_json
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse medical_entities for consultation {consultation_id}: {str(e)}")
                medical_entities = []
        
        # Query associated prescription by consultation_id first (deterministic match).
        query_prescription = """
        SELECT
            prescription_id,
            patient_name,
            medications,
            sections,
            state,
            s3_key,
            created_at,
            finalized_at
        FROM prescriptions
        WHERE user_id = %s
          AND consultation_id = %s
        ORDER BY created_at DESC
        LIMIT 1
        """

        prescription_result = database_manager.execute_with_retry(
            query_prescription,
            (user_id, str(consultation_id_value))
        )

        # Legacy fallback for old records that may not have consultation_id populated.
        if not prescription_result:
            legacy_query_prescription = """
            SELECT
                prescription_id,
                patient_name,
                medications,
                sections,
                state,
                s3_key,
                created_at,
                finalized_at
            FROM prescriptions
            WHERE user_id = %s
              AND created_at >= %s
              AND created_at <= %s + INTERVAL '1 hour'
            ORDER BY created_at ASC
            LIMIT 1
            """
            prescription_result = database_manager.execute_with_retry(
                legacy_query_prescription,
                (user_id, created_at, created_at)
            )
        
        prescription = None
        if prescription_result and len(prescription_result) > 0:
            presc_row = prescription_result[0]
            (
                presc_id,
                patient_name,
                medications,
                sections,
                prescription_state,
                prescription_s3_key,
                presc_created_at,
                presc_finalized_at
            ) = presc_row
            
            # Parse medications JSONB
            medications_list = []
            if medications:
                try:
                    if isinstance(medications, str):
                        medications_list = json.loads(medications)
                    else:
                        medications_list = medications
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to parse medications for prescription {presc_id}: {str(e)}")
                    medications_list = []

            # Parse sections JSONB (for finalized prescriptions where content is stored in sections)
            sections_list = []
            if sections:
                try:
                    if isinstance(sections, str):
                        sections_list = json.loads(sections)
                    else:
                        sections_list = sections
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to parse sections for prescription {presc_id}: {str(e)}")
                    sections_list = []

            # In save-and-finalize flow, medications are persisted under sections.medications.
            # Build medications fallback if medications column is empty/missing.
            if not medications_list:
                extracted_medications = []
                try:
                    if isinstance(sections_list, dict):
                        meds_section = sections_list.get('medications')
                        if isinstance(meds_section, dict):
                            meds_section = [meds_section]
                        if isinstance(meds_section, list):
                            for item in meds_section:
                                if not isinstance(item, dict):
                                    continue
                                mapped = {
                                    'name': item.get('medicine_name') or item.get('name') or '',
                                    'dosage': item.get('dose') or item.get('dosage') or '',
                                    'frequency': item.get('frequency') or '',
                                    'duration': item.get('duration') or ''
                                }
                                if any(mapped.values()):
                                    extracted_medications.append(mapped)
                    elif isinstance(sections_list, list):
                        for section_item in sections_list:
                            if not isinstance(section_item, dict):
                                continue
                            section_key = (section_item.get('key') or section_item.get('section_id') or '').lower()
                            if section_key != 'medications':
                                continue

                            content = section_item.get('content')
                            fields = section_item.get('fields')

                            if isinstance(content, list):
                                for item in content:
                                    if isinstance(item, dict):
                                        mapped = {
                                            'name': item.get('medicine_name') or item.get('name') or '',
                                            'dosage': item.get('dose') or item.get('dosage') or '',
                                            'frequency': item.get('frequency') or '',
                                            'duration': item.get('duration') or ''
                                        }
                                        if any(mapped.values()):
                                            extracted_medications.append(mapped)
                            elif isinstance(fields, list):
                                row = {}
                                for field in fields:
                                    if not isinstance(field, dict):
                                        continue
                                    fname = field.get('field_name')
                                    if not fname:
                                        continue
                                    row[fname] = field.get('value')
                                mapped = {
                                    'name': row.get('medicine_name') or row.get('name') or '',
                                    'dosage': row.get('dose') or row.get('dosage') or '',
                                    'frequency': row.get('frequency') or '',
                                    'duration': row.get('duration') or ''
                                }
                                if any(mapped.values()):
                                    extracted_medications.append(mapped)
                except Exception as e:
                    logger.warning(f"Failed to derive medications from sections for prescription {presc_id}: {str(e)}")

                if extracted_medications:
                    medications_list = extracted_medications
            
            prescription = {
                'prescription_id': presc_id,
                'patient_name': patient_name,
                'medications': medications_list,
                'sections': sections_list,
                'state': prescription_state,
                's3_key': prescription_s3_key,
                'created_at': presc_created_at,
                'finalized_at': presc_finalized_at
            }

        clip_rows = database_manager.execute_with_retry(
            """
            SELECT clip_order, job_id, status, audio_s3_key, transcript_text, created_at
            FROM transcriptions
            WHERE consultation_id = %s AND user_id = %s
            ORDER BY clip_order ASC, created_at ASC
            """,
            (str(consultation_id_value), user_id)
        ) or []
        clips = []
        for clip_order, clip_job_id, clip_status, clip_audio_s3_key, clip_transcript_text, clip_created_at in clip_rows:
            clips.append({
                'clip_order': clip_order,
                'job_id': clip_job_id,
                'status': clip_status,
                'audio_s3_key': clip_audio_s3_key,
                'transcript_preview': (clip_transcript_text or '')[:140],
                'created_at': clip_created_at
            })
        
        # Extract patient name using ConsultationService logic
        from services.consultation_service import ConsultationService
        patient_name = ConsultationService._extract_patient_name(
            prescription['patient_name'] if prescription else None,
            medical_entities
        )
        
        # Prepare template data
        consultation_data = {
            'consultation_id': consultation_id_value,
            'patient_name': patient_name,
            'status': status,
            'transcript_text': transcript_text if transcript_text else "No transcript available",
            'medical_entities': medical_entities,
            'clips': clips,
            'created_at': created_at,
            'updated_at': updated_at,
            'prescription': prescription
        }
        
        # Render consultation_detail.html template with data
        return render_template('consultation_detail.html', consultation=consultation_data)
        
    except Exception as e:
        logger.error(f"Failed to retrieve consultation {consultation_id}: {str(e)}", exc_info=True)
        abort(500)


# API Endpoints
@app.route('/api/v1/auth/login', methods=['POST'])
def api_login():
    """API endpoint for login with AWS Cognito"""
    logger = logging.getLogger(__name__)
    
    try:
        data = _get_request_data()
        email = data.get('email', '')
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password required'}), 400
        
        # Authenticate with Cognito
        tokens, auth_error = auth_manager.authenticate(email, password)
        
        if tokens:
            # Store tokens in session
            session['user_id'] = email
            session['access_token'] = tokens['access_token']
            session['id_token'] = tokens['id_token']
            session['refresh_token'] = tokens['refresh_token']
            session['login_at'] = datetime.now(timezone.utc).isoformat()
            
            # Get user info and sync role from Cognito
            user_info = auth_manager.validate_token(tokens['access_token'])
            if user_info:
                attributes = user_info.get('attributes', {})
                session['user_name'] = attributes.get('name', email.split('@')[0].title())
                session['user_attributes'] = attributes

                # Backfill legacy users missing role attributes in Cognito
                needs_role_backfill = (
                    not attributes.get('custom:role') or
                    (
                        attributes.get('custom:role') in ['Doctor', 'HospitalAdmin'] and
                        not attributes.get('custom:hospital_id')
                    )
                )
                if needs_role_backfill:
                    updated_attributes = auth_manager.ensure_role_attributes(
                        tokens['access_token'],
                        attributes,
                        default_role='Doctor',
                        default_hospital_id='default'
                    )
                    if updated_attributes:
                        attributes = updated_attributes
                        user_info['attributes'] = updated_attributes
                    else:
                        session.clear()
                        logger.warning(f"Login blocked for {email}: failed to auto-backfill role attributes")
                        return jsonify({
                            'success': False,
                            'message': 'Account role setup failed. Contact your administrator.'
                        }), 403

                # Sync user role from Cognito to database
                from utils.auth_helpers import sync_user_role_from_cognito
                user_role = sync_user_role_from_cognito(database_manager, user_info, email)

                if user_role:
                    session['user_role'] = user_role
                    hospital_id = attributes.get('custom:hospital_id')
                    session['hospital_id'] = hospital_id
                else:
                    session.clear()
                    logger.warning(f"Login blocked for {email}: missing or invalid Cognito role attributes")
                    return jsonify({
                        'success': False,
                        'message': 'Account role configuration is missing or invalid. Contact your administrator.'
                    }), 403
            else:
                session.clear()
                logger.warning(f"Login blocked for {email}: unable to fetch Cognito user attributes")
                return jsonify({
                    'success': False,
                    'message': 'Unable to validate user profile from Cognito. Please try again.'
                }), 401
            
            logger.info(f"User logged in successfully: {email} (role: {session.get('user_role')})")
            return jsonify({'success': True, 'message': 'Login successful'})
        else:
            logger.warning(f"Login failed for user: {email}")
            message = auth_error['message'] if auth_error else 'Invalid credentials'
            error_code = auth_error['code'] if auth_error else None
            return jsonify({'success': False, 'message': message, 'error_code': error_code}), 401
            
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred during login'}), 500


@app.route('/api/v1/auth/google', methods=['POST'])
def api_google_login():
    """API endpoint for Google Sign-In"""
    logger = logging.getLogger(__name__)

    try:
        data = _get_request_data()
        id_token = data.get('id_token', '')
        google_client_id = os.getenv('GOOGLE_CLIENT_ID', '')

        if not google_client_id:
            return jsonify({
                'success': False,
                'message': 'Google login is not configured. Set GOOGLE_CLIENT_ID in environment.'
            }), 503

        if not id_token:
            return jsonify({'success': False, 'message': 'Google ID token is required'}), 400

        tokeninfo_url = "https://oauth2.googleapis.com/tokeninfo?" + urlencode({'id_token': id_token})
        try:
            with urlopen(tokeninfo_url, timeout=10) as response:
                payload = json.loads(response.read().decode('utf-8'))
        except Exception as e:
            logger.warning(f"Google token verification failed: {str(e)}")
            return jsonify({'success': False, 'message': 'Invalid Google token'}), 401

        audience = payload.get('aud')
        issuer = payload.get('iss')
        email = payload.get('email', '')
        email_verified = str(payload.get('email_verified', 'false')).lower() == 'true'
        expiry = payload.get('exp')

        if audience != google_client_id:
            return jsonify({'success': False, 'message': 'Invalid Google audience'}), 401
        if issuer not in {'accounts.google.com', 'https://accounts.google.com'}:
            return jsonify({'success': False, 'message': 'Invalid Google issuer'}), 401
        if not email:
            return jsonify({'success': False, 'message': 'Email not available from Google'}), 400
        if not email_verified:
            return jsonify({'success': False, 'message': 'Google email is not verified'}), 401

        if expiry:
            try:
                if int(expiry) <= int(datetime.now(timezone.utc).timestamp()):
                    return jsonify({'success': False, 'message': 'Google token expired'}), 401
            except ValueError:
                pass

        role_query = """
        SELECT role, hospital_id
        FROM user_roles
        WHERE user_id = %s
        """
        role_result = database_manager.execute_with_retry(role_query, (email,))
        if not role_result:
            return jsonify({
                'success': False,
                'message': 'No application account found for this Google user. Ask an administrator to register your account first.'
            }), 403

        user_role = role_result[0][0]
        hospital_id = role_result[0][1]

        session['user_id'] = email
        session['user_name'] = payload.get('name', email.split('@')[0].title())
        session['user_role'] = user_role
        session['hospital_id'] = hospital_id
        session['login_at'] = datetime.now(timezone.utc).isoformat()
        session['user_attributes'] = {
            'name': payload.get('name', ''),
            'email': email,
            'email_verified': 'true'
        }

        logger.info(f"User logged in with Google: {email} (role: {user_role})")
        return jsonify({'success': True, 'message': 'Google login successful'})

    except Exception as e:
        logger.error(f"Google login error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred during Google login'}), 500


@app.route('/api/v1/auth/register', methods=['POST'])
def api_register():
    """API endpoint for user registration with AWS Cognito"""
    logger = logging.getLogger(__name__)
    
    try:
        data = _get_request_data()
        email = data.get('email', '')
        password = data.get('password', '')
        name = data.get('name', '')
        role = data.get('role', '')
        hospital_id = data.get('hospital_id', '')

        if not email or not password or not role:
            return jsonify({'success': False, 'message': 'Email, password, and role are required'}), 400

        from utils.validation import validate_user_role
        role_valid, role_error = validate_user_role(role)
        if not role_valid:
            return jsonify({'success': False, 'message': role_error}), 400

        if role in ['Doctor', 'HospitalAdmin'] and not hospital_id:
            return jsonify({
                'success': False,
                'message': 'hospital_id is required for Doctor and HospitalAdmin users'
            }), 400

        if role == 'DeveloperAdmin' and not hospital_id:
            hospital_id = 'default'

        # Register with Cognito
        attributes = {}
        if name:
            attributes['name'] = name
        attributes['custom:role'] = role
        attributes['custom:hospital_id'] = hospital_id
        
        result = auth_manager.register(email, password, attributes)
        
        if result:
            logger.info(f"User registered successfully: {email}")
            return jsonify({
                'success': True,
                'message': 'Registration successful. Please check your email for verification code.',
                'user_confirmed': result['user_confirmed']
            })
        else:
            return jsonify({'success': False, 'message': 'Registration failed. User may already exist or password does not meet requirements.'}), 400
            
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred during registration'}), 500


@app.route('/api/v1/auth/verify', methods=['POST'])
def api_verify():
    """API endpoint for user verification with confirmation code"""
    logger = logging.getLogger(__name__)
    
    try:
        data = _get_request_data()
        email = data.get('email', '')
        code = data.get('code', '')
        
        if not email or not code:
            return jsonify({'success': False, 'message': 'Email and verification code required'}), 400
        
        # Verify with Cognito
        success = auth_manager.verify_user(email, code)
        
        if success:
            logger.info(f"User verified successfully: {email}")
            return jsonify({'success': True, 'message': 'Account verified successfully. You can now login.'})
        else:
            return jsonify({'success': False, 'message': 'Verification failed. Invalid or expired code.'}), 400
            
    except Exception as e:
        logger.error(f"Verification error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred during verification'}), 500


@app.route('/api/v1/auth/forgot-password', methods=['POST'])
def api_forgot_password():
    """API endpoint to start forgot password flow"""
    logger = logging.getLogger(__name__)
    
    try:
        data = _get_request_data()
        email = data.get('email', '')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email required'}), 400
        
        success, auth_error = auth_manager.forgot_password(email)
        
        if success:
            logger.info(f"Forgot password initiated for user: {email}")
            return jsonify({'success': True, 'message': 'Verification code sent to your email.'})
        else:
            message = auth_error['message'] if auth_error else 'Failed to send verification code.'
            error_code = auth_error['code'] if auth_error else None
            return jsonify({'success': False, 'message': message, 'error_code': error_code}), 400
            
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred during password reset.'}), 500


@app.route('/api/v1/auth/confirm-forgot-password', methods=['POST'])
def api_confirm_forgot_password():
    """API endpoint to confirm forgot password with code and new password"""
    logger = logging.getLogger(__name__)
    
    try:
        data = _get_request_data()
        email = data.get('email', '')
        code = data.get('code', '')
        new_password = data.get('new_password', '')
        
        if not email or not code or not new_password:
            return jsonify({'success': False, 'message': 'Email, verification code, and new password required'}), 400
        
        success, auth_error = auth_manager.confirm_forgot_password(email, code, new_password)
        
        if success:
            logger.info(f"Password reset confirmed for user: {email}")
            return jsonify({'success': True, 'message': 'Password reset successful. You can now login.'})
        else:
            message = auth_error['message'] if auth_error else 'Password reset failed.'
            error_code = auth_error['code'] if auth_error else None
            return jsonify({'success': False, 'message': message, 'error_code': error_code}), 400
            
    except Exception as e:
        logger.error(f"Confirm forgot password error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred during password reset.'}), 500


@app.route('/api/v1/auth/logout', methods=['POST'])
def api_logout():
    """API endpoint for logout"""
    logger = logging.getLogger(__name__)
    
    try:
        access_token = session.get('access_token')
        
        # Revoke tokens in Cognito
        if access_token and auth_manager:
            auth_manager.logout(access_token)
        
        # Clear session
        session.clear()
        
        logger.info("User logged out successfully")
        return jsonify({'success': True, 'message': 'Logout successful'})
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        # Clear session anyway
        session.clear()
        return jsonify({'success': True, 'message': 'Logout successful'})


@app.route('/api/v1/audio/upload', methods=['POST'])
@login_required
def api_upload_audio():
    """API endpoint for audio file upload to S3"""
    logger = logging.getLogger(__name__)
    
    try:
        if 'audio' not in request.files:
            return jsonify({'success': False, 'message': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        
        if audio_file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        user_id = session.get('user_id')
        
        # Upload to S3
        s3_key = storage_manager.upload_audio(audio_file, audio_file.filename, user_id)
        
        if s3_key:
            logger.info(f"Audio uploaded successfully: {s3_key}")
            return jsonify({
                'success': True,
                'message': 'Audio uploaded successfully',
                's3_key': s3_key
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to upload audio file'}), 500
            
    except ValueError as e:
        # Validation error
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Audio upload error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred during upload'}), 500


@app.route('/api/v1/consultations/start', methods=['POST'])
@login_required
def api_start_consultation():
    """Create a new consultation container for multiple audio clips."""
    logger = logging.getLogger(__name__)

    try:
        import uuid

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401

        consultation_id = str(uuid.uuid4())
        query = """
        INSERT INTO consultations (consultation_id, user_id, status, merged_transcript_text)
        VALUES (%s, %s, 'IN_PROGRESS', '')
        """
        database_manager.execute_with_retry(query, (consultation_id, user_id))

        logger.info(f"Consultation started: consultation_id={consultation_id}, user={user_id}")
        return jsonify({
            'success': True,
            'consultation_id': consultation_id
        })
    except Exception as e:
        logger.error(f"Failed to start consultation: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to start consultation'}), 500


@app.route('/api/v1/transcribe', methods=['POST'])
@login_required
def api_transcribe():
    """API endpoint for audio transcription with AWS Transcribe Medical"""
    logger = logging.getLogger(__name__)
    
    try:
        data = request.get_json()
        s3_key = data.get('s3_key', '')
        consultation_id = data.get('consultation_id', '')
        clip_order = data.get('clip_order', 1)
        
        if not s3_key:
            return jsonify({'success': False, 'message': 'S3 key required'}), 400
        if not consultation_id:
            return jsonify({'success': False, 'message': 'consultation_id required'}), 400

        try:
            clip_order = int(clip_order)
            if clip_order < 1:
                clip_order = 1
        except (TypeError, ValueError):
            clip_order = 1
        
        user_id = session.get('user_id')
        consultation_exists = database_manager.execute_with_retry(
            """
            SELECT consultation_id
            FROM consultations
            WHERE consultation_id = %s AND user_id = %s
            LIMIT 1
            """,
            (consultation_id, user_id)
        )
        if not consultation_exists:
            return jsonify({'success': False, 'message': 'Consultation not found'}), 404
        
        # Get S3 URI for transcription
        audio_uri = storage_manager.get_audio_uri(s3_key)
        
        # Determine media format from S3 key
        file_ext = s3_key.split('.')[-1].lower()
        media_format = file_ext if file_ext in ['mp3', 'mp4', 'wav', 'flac'] else 'mp3'
        
        # Start transcription job
        job_id = transcribe_manager.start_transcription(audio_uri, media_format=media_format)
        
        if job_id:
            # Save transcription record to database
            transcription = Transcription(
                user_id=user_id,
                audio_s3_key=s3_key,
                job_id=job_id,
                status='IN_PROGRESS'
            )
            transcription.save(database_manager)
            database_manager.execute_with_retry(
                """
                UPDATE transcriptions
                SET consultation_id = %s, clip_order = %s, updated_at = CURRENT_TIMESTAMP
                WHERE job_id = %s AND user_id = %s
                """,
                (consultation_id, clip_order, job_id, user_id)
            )
            database_manager.execute_with_retry(
                """
                UPDATE consultations
                SET status = 'IN_PROGRESS', updated_at = CURRENT_TIMESTAMP
                WHERE consultation_id = %s AND user_id = %s
                """,
                (consultation_id, user_id)
            )
            
            logger.info(f"Transcription job started: {job_id}")
            return jsonify({
                'success': True,
                'message': 'Transcription started',
                'job_id': job_id,
                'consultation_id': consultation_id,
                'clip_order': clip_order
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to start transcription'}), 500
            
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred during transcription'}), 500


@app.route('/api/v1/transcribe/status/<job_id>', methods=['GET'])
@login_required
def api_transcribe_status(job_id):
    """API endpoint to check transcription job status"""
    logger = logging.getLogger(__name__)
    
    try:
        user_id = session.get('user_id')
        status_info = transcribe_manager.get_job_status(job_id)
        
        if status_info:
            # Update database if status changed
            transcription = Transcription.get_by_job_id(job_id, database_manager)
            if transcription and transcription.status != status_info['status']:
                transcription.status = status_info['status']
                transcription.update(database_manager)

            if user_id:
                consultation_result = database_manager.execute_with_retry(
                    """
                    SELECT consultation_id
                    FROM transcriptions
                    WHERE job_id = %s AND user_id = %s
                    LIMIT 1
                    """,
                    (job_id, user_id)
                )
                if consultation_result and consultation_result[0][0]:
                    _rebuild_consultation_transcript(consultation_result[0][0], user_id)
            
            return jsonify({
                'success': True,
                'status': status_info['status'],
                'job_id': job_id
            })
        else:
            return jsonify({'success': False, 'message': 'Job not found'}), 404
            
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@app.route('/api/v1/transcribe/result/<job_id>', methods=['GET'])
@login_required
def api_transcribe_result(job_id):
    """API endpoint to get transcription result with medical entity extraction"""
    logger = logging.getLogger(__name__)
    
    try:
        user_id = session.get('user_id')
        # Get transcript from Transcribe
        transcript_text = transcribe_manager.get_transcript(job_id)
        
        if not transcript_text:
            return jsonify({'success': False, 'message': 'Transcript not available yet'}), 404
        
        # Extract medical entities with Comprehend Medical
        entities = comprehend_manager.extract_entities(transcript_text)
        
        if entities is None:
            # Entity extraction failed, but return transcript anyway
            logger.warning(f"Entity extraction failed for job {job_id}, returning transcript only")
            entities = []
        
        # Categorize entities
        categorized_entities = comprehend_manager.categorize_entities(entities) if entities else {}
        
        # Update database
        transcription = Transcription.get_by_job_id(job_id, database_manager)
        consultation_id = None
        if transcription:
            transcription.transcript_text = transcript_text
            transcription.medical_entities = entities
            transcription.status = 'COMPLETED'
            transcription.update(database_manager)
            if user_id:
                consultation_result = database_manager.execute_with_retry(
                    """
                    SELECT consultation_id
                    FROM transcriptions
                    WHERE job_id = %s AND user_id = %s
                    LIMIT 1
                    """,
                    (job_id, user_id)
                )
                if consultation_result and consultation_result[0][0]:
                    consultation_id = consultation_result[0][0]
                    _rebuild_consultation_transcript(consultation_id, user_id)
        
        logger.info(f"Transcript and entities retrieved for job: {job_id}")
        return jsonify({
            'success': True,
            'transcript': transcript_text,
            'entities': entities,
            'categorized_entities': categorized_entities,
            'consultation_id': consultation_id
        })
        
    except Exception as e:
        logger.error(f"Result retrieval error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@app.route('/api/v1/transcribe/transcript/<job_id>', methods=['PUT'])
@login_required
def api_update_transcript_text(job_id):
    """Update transcript text after manual user edits."""
    logger = logging.getLogger(__name__)

    try:
        data = request.get_json(silent=True) or {}
        transcript_text = (data.get('transcript_text') or '').strip()

        if not transcript_text:
            return jsonify({'success': False, 'message': 'transcript_text is required'}), 400

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401

        update_query = """
        UPDATE transcriptions
        SET transcript_text = %s, status = 'COMPLETED', updated_at = CURRENT_TIMESTAMP
        WHERE job_id = %s AND user_id = %s
        """
        database_manager.execute_with_retry(update_query, (transcript_text, job_id, user_id))

        verify_query = """
        SELECT transcription_id
        FROM transcriptions
        WHERE job_id = %s AND user_id = %s
        LIMIT 1
        """
        result = database_manager.execute_with_retry(verify_query, (job_id, user_id))
        if not result:
            return jsonify({'success': False, 'message': 'Transcription not found'}), 404

        logger.info(f"Transcript updated by user edit: job_id={job_id}, user={user_id}")
        return jsonify({
            'success': True,
            'message': 'Transcript updated successfully',
            'job_id': job_id
        })

    except Exception as e:
        logger.error(f"Transcript update error for job {job_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to update transcript'}), 500


@app.route('/api/v1/consultations/<consultation_id>/transcript', methods=['GET'])
@login_required
def api_get_consultation_transcript(consultation_id):
    """Get merged transcript for a consultation."""
    logger = logging.getLogger(__name__)

    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401

        row = database_manager.execute_with_retry(
            """
            SELECT consultation_id, status, merged_transcript_text
            FROM consultations
            WHERE consultation_id = %s AND user_id = %s
            LIMIT 1
            """,
            (consultation_id, user_id)
        )
        if not row:
            return jsonify({'success': False, 'message': 'Consultation not found'}), 404

        merged_text = _rebuild_consultation_transcript(consultation_id, user_id)
        return jsonify({
            'success': True,
            'consultation_id': consultation_id,
            'status': row[0][1],
            'transcript': merged_text
        })
    except Exception as e:
        logger.error(f"Failed to get consultation transcript {consultation_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to load transcript'}), 500


@app.route('/api/v1/consultations/<consultation_id>/transcript', methods=['PUT'])
@login_required
def api_update_consultation_transcript(consultation_id):
    """Save edited merged transcript for a consultation."""
    logger = logging.getLogger(__name__)

    try:
        data = request.get_json(silent=True) or {}
        transcript_text = (data.get('transcript_text') or '').strip()
        if not transcript_text:
            return jsonify({'success': False, 'message': 'transcript_text is required'}), 400

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401

        exists = database_manager.execute_with_retry(
            """
            SELECT consultation_id
            FROM consultations
            WHERE consultation_id = %s AND user_id = %s
            LIMIT 1
            """,
            (consultation_id, user_id)
        )
        if not exists:
            return jsonify({'success': False, 'message': 'Consultation not found'}), 404

        database_manager.execute_with_retry(
            """
            UPDATE consultations
            SET merged_transcript_text = %s, updated_at = CURRENT_TIMESTAMP
            WHERE consultation_id = %s AND user_id = %s
            """,
            (transcript_text, consultation_id, user_id)
        )

        # Keep at least one underlying clip row aligned for downstream consumers.
        database_manager.execute_with_retry(
            """
            UPDATE transcriptions t
            SET transcript_text = %s, status = 'COMPLETED', updated_at = CURRENT_TIMESTAMP
            WHERE t.transcription_id = (
                SELECT t2.transcription_id
                FROM transcriptions t2
                WHERE t2.consultation_id = %s AND t2.user_id = %s
                ORDER BY t2.clip_order DESC, t2.created_at DESC
                LIMIT 1
            )
            """,
            (transcript_text, consultation_id, user_id)
        )

        logger.info(f"Consultation transcript updated: consultation_id={consultation_id}, user={user_id}")
        return jsonify({
            'success': True,
            'consultation_id': consultation_id,
            'message': 'Transcript updated successfully'
        })
    except Exception as e:
        logger.error(f"Failed to update consultation transcript {consultation_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to update transcript'}), 500


@app.route('/api/v1/consultations/<consultation_id>/finalize', methods=['POST'])
@login_required
def api_finalize_consultation(consultation_id):
    """Mark consultation as completed when user confirms finalization."""
    logger = logging.getLogger(__name__)

    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401

        merged_text = _rebuild_consultation_transcript(consultation_id, user_id)
        if not merged_text or not merged_text.strip():
            return jsonify({'success': False, 'message': 'Cannot finalize empty consultation'}), 400

        exists = database_manager.execute_with_retry(
            """
            SELECT consultation_id
            FROM consultations
            WHERE consultation_id = %s AND user_id = %s
            LIMIT 1
            """,
            (consultation_id, user_id)
        )
        if not exists:
            return jsonify({'success': False, 'message': 'Consultation not found'}), 404

        database_manager.execute_with_retry(
            """
            UPDATE consultations
            SET status = 'COMPLETED', updated_at = CURRENT_TIMESTAMP
            WHERE consultation_id = %s AND user_id = %s
            """,
            (consultation_id, user_id)
        )

        logger.info(f"Consultation finalized: consultation_id={consultation_id}, user={user_id}")
        return jsonify({
            'success': True,
            'consultation_id': consultation_id,
            'status': 'COMPLETED'
        })
    except Exception as e:
        logger.error(f"Failed to finalize consultation {consultation_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to finalize consultation'}), 500


@app.route('/api/v1/consultations/<consultation_id>/save-and-finalize', methods=['POST'])
@login_required
def api_save_and_finalize_consultation(consultation_id):
    """Save prescription for consultation and mark consultation as completed."""
    logger = logging.getLogger(__name__)

    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401

        data = request.get_json(silent=True) or {}
        hospital_id = data.get('hospital_id') or session.get('hospital_id') or 'default'
        patient_name = (data.get('patient_name') or '').strip()
        sections = data.get('sections')

        # Validate consultation ownership
        exists = database_manager.execute_with_retry(
            """
            SELECT consultation_id
            FROM consultations
            WHERE consultation_id = %s AND user_id = %s
            LIMIT 1
            """,
            (consultation_id, user_id)
        )
        if not exists:
            return jsonify({'success': False, 'message': 'Consultation not found'}), 404

        merged_text = _rebuild_consultation_transcript(consultation_id, user_id)
        if not merged_text or not merged_text.strip():
            return jsonify({'success': False, 'message': 'Cannot finalize empty consultation'}), 400

        if not patient_name:
            from services.consultation_service import ConsultationService
            patient_name = ConsultationService._extract_patient_name(merged_text, [])

        # Reuse existing prescription for this consultation if one exists.
        existing = database_manager.execute_with_retry(
            """
            SELECT prescription_id
            FROM prescriptions
            WHERE consultation_id = %s
              AND user_id = %s
              AND state <> 'Deleted'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (consultation_id, user_id)
        )

        if existing and len(existing) > 0:
            prescription_id = str(existing[0][0])
        else:
            created = database_manager.execute_with_retry(
                """
                INSERT INTO prescriptions
                (user_id, created_by_doctor_id, consultation_id, hospital_id, patient_name,
                 state, medications, s3_key, sections, created_at)
                VALUES (%s, %s, %s, %s, %s, 'Draft', '[]'::jsonb, '', '[]'::jsonb, CURRENT_TIMESTAMP)
                RETURNING prescription_id
                """,
                (user_id, user_id, consultation_id, hospital_id, patient_name)
            )
            if not created or len(created) == 0:
                return jsonify({'success': False, 'message': 'Failed to save prescription'}), 500
            prescription_id = str(created[0][0])

        # Persist edited sections from Bedrock form if provided.
        if sections is not None:
            database_manager.execute_with_retry(
                """
                UPDATE prescriptions
                SET sections = %s::jsonb,
                    state = CASE WHEN state = 'Draft' THEN 'InProgress' ELSE state END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE prescription_id = %s AND user_id = %s
                """,
                (json.dumps(sections), prescription_id, user_id)
            )

        # Finalize consultation
        database_manager.execute_with_retry(
            """
            UPDATE consultations
            SET status = 'COMPLETED', updated_at = CURRENT_TIMESTAMP
            WHERE consultation_id = %s AND user_id = %s
            """,
            (consultation_id, user_id)
        )

        logger.info(
            f"Saved prescription {prescription_id} and finalized consultation {consultation_id} for user {user_id}"
        )
        return jsonify({
            'success': True,
            'consultation_id': consultation_id,
            'prescription_id': prescription_id,
            'status': 'COMPLETED',
            'redirect_url': '/thank-you'
        })
    except Exception as e:
        logger.error(f"Failed to save and finalize consultation {consultation_id}: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to save and finalize consultation'}), 500


@app.route('/api/v1/prescriptions', methods=['POST'])
@login_required
def api_create_prescription():
    """API endpoint to create prescription with PDF storage"""
    logger = logging.getLogger(__name__)
    
    try:
        data = request.get_json()
        patient_name = data.get('patient_name', '')
        medications = data.get('medications', [])
        
        if not patient_name or not medications:
            return jsonify({'success': False, 'message': 'Patient name and medications required'}), 400
        
        user_id = session.get('user_id')
        
        # Generate PDF (placeholder - you'll need to implement actual PDF generation)
        # For now, we'll create a simple text-based PDF
        from io import BytesIO
        pdf_data = f"Prescription for {patient_name}\n\nMedications:\n".encode()
        for med in medications:
            pdf_data += f"- {med.get('name', 'Unknown')}: {med.get('dosage', 'N/A')}\n".encode()
        
        # Create prescription record first to get ID
        prescription = Prescription(
            user_id=user_id,
            patient_name=patient_name,
            medications=medications,
            s3_key='pending'  # Temporary value
        )
        
        # Save to get prescription ID
        prescription_id = prescription.save(database_manager)
        
        if not prescription_id:
            return jsonify({'success': False, 'message': 'Failed to create prescription record'}), 500
        
        # Upload PDF to S3
        s3_key = storage_manager.upload_pdf(pdf_data, user_id, prescription_id)
        
        if not s3_key:
            # PDF upload failed, don't create prescription
            logger.error(f"PDF upload failed for prescription {prescription_id}")
            return jsonify({'success': False, 'message': 'Failed to upload prescription PDF'}), 500
        
        # Update prescription with S3 key
        prescription.s3_key = s3_key
        prescription.update(database_manager) if hasattr(prescription, 'update') else None
        
        logger.info(f"Prescription created successfully: {prescription_id}")
        return jsonify({
            'success': True,
            'message': 'Prescription created successfully',
            'prescription_id': prescription_id
        })
        
    except Exception as e:
        logger.error(f"Prescription creation error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@app.route('/api/v1/prescriptions/<prescription_id>/download', methods=['GET'])
@login_required
def api_download_prescription(prescription_id):
    """API endpoint to get presigned URL for prescription PDF download"""
    logger = logging.getLogger(__name__)
    
    try:
        # Get prescription from database
        prescription = Prescription.get_by_id(prescription_id, database_manager)
        
        if not prescription:
            return jsonify({'success': False, 'message': 'Prescription not found'}), 404
        
        # Verify user owns this prescription
        if prescription.user_id != session.get('user_id'):
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        # Generate presigned URL
        presigned_url = storage_manager.generate_presigned_url(prescription.s3_key)
        
        if presigned_url:
            logger.info(f"Presigned URL generated for prescription: {prescription_id}")
            return jsonify({
                'success': True,
                'download_url': presigned_url
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to generate download URL'}), 500
            
    except Exception as e:
        logger.error(f"Download URL generation error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


# Bedrock Medical Extraction Endpoints
@app.route('/api/v1/extract', methods=['POST'])
@login_required
def api_extract_prescription():
    """API endpoint for medical prescription extraction using Bedrock"""
    logger = logging.getLogger(__name__)
    
    try:
        # Parse request
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'error_code': 'INVALID_INPUT',
                'error_message': 'Request body is required'
            }), 400
        
        # Validate request using Pydantic model
        from models.bedrock_extraction import ExtractionRequest
        from pydantic import ValidationError
        
        try:
            extraction_request = ExtractionRequest(**data)
        except ValidationError as e:
            logger.warning(f"Invalid extraction request: {e}")
            return jsonify({
                'status': 'error',
                'error_code': 'VALIDATION_ERROR',
                'error_message': str(e)
            }), 400
        
        # Initialize extraction pipeline if not already done
        from aws_services.extraction_pipeline import ExtractionPipeline
        extraction_pipeline = ExtractionPipeline(config_manager)
        
        # Validate request
        is_valid, error_msg = extraction_pipeline.validate_request(extraction_request)
        if not is_valid:
            return jsonify({
                'status': 'error',
                'error_code': 'INVALID_INPUT',
                'error_message': error_msg
            }), 400
        
        # Extract prescription data
        logger.info(f"Starting extraction for hospital {extraction_request.hospital_id}")
        prescription_data = extraction_pipeline.extract_prescription_data(
            transcript=extraction_request.transcript,
            hospital_id=extraction_request.hospital_id,
            request_id=extraction_request.request_id
        )
        
        if prescription_data is None:
            return jsonify({
                'status': 'error',
                'error_code': 'EXTRACTION_FAILED',
                'error_message': 'Failed to extract prescription data'
            }), 500
        
        # Return success response
        return jsonify({
            'status': 'success',
            'prescription_data': prescription_data.model_dump(mode='json'),
            'request_id': prescription_data.request_id
        }), 200
        
    except Exception as e:
        logger.error(f"Extraction error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error_code': 'INTERNAL_ERROR',
            'error_message': 'An unexpected error occurred'
        }), 500


@app.route('/api/v1/config/<hospital_id>', methods=['GET'])
@login_required
def api_get_hospital_config(hospital_id):
    """API endpoint to get hospital configuration"""
    logger = logging.getLogger(__name__)
    
    try:
        from aws_services.config_manager import ConfigurationNotFoundError
        
        # Load hospital configuration
        try:
            hospital_config = config_manager.load_hospital_configuration(hospital_id)
        except ConfigurationNotFoundError:
            logger.warning(f"Hospital config not found for {hospital_id}, using default")
            hospital_config = config_manager.get_default_hospital_configuration()
        
        # Return configuration
        return jsonify(hospital_config.model_dump(mode='json')), 200
        
    except Exception as e:
        logger.error(f"Config retrieval error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error_code': 'INTERNAL_ERROR',
            'error_message': 'Failed to retrieve configuration'
        }), 500


@app.route('/api/consultations', methods=['GET'])
@app.route('/api/v1/consultations', methods=['GET'])
@login_required
def api_get_consultations():
    """
    API endpoint for consultation retrieval
    
    Retrieve recent consultations for authenticated user
    
    Query Parameters:
        limit (int, optional): Maximum consultations to return (default: 15, max: 50)
    
    Returns:
        JSON response with consultation list or error
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Extract user_id from session
        user_id = session.get('user_id')
        
        if not user_id:
            logger.warning("API consultation request without user_id in session")
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        
        # Parse and validate limit query parameter
        limit = request.args.get('limit', '15')
        try:
            limit = int(limit)
            # Cap limit at 50, default to 15 if invalid
            if limit < 1 or limit > 50:
                logger.warning(f"Invalid limit parameter: {limit}, using default 15")
                limit = 15
        except ValueError:
            logger.warning(f"Non-integer limit parameter: {limit}, using default 15")
            limit = 15

        # Optional server-side filters
        search = (request.args.get('search', '') or '').strip()
        status = (request.args.get('status', '') or '').strip().upper()
        if status and status not in {'COMPLETED', 'IN_PROGRESS', 'FAILED'}:
            logger.warning(f"Ignoring invalid status filter: {status}")
            status = ''
        start_date = (request.args.get('start_date', '') or '').strip()
        end_date = (request.args.get('end_date', '') or '').strip()
        
        # Check if we should use mock data (for local development)
        use_mock_data = os.getenv('USE_MOCK_CONSULTATIONS', 'false').lower() == 'true'
        
        if use_mock_data:
            logger.info("Using mock consultation data for development")
            from datetime import datetime, timedelta
            mock_consultations = [
                {
                    "consultation_id": "1",
                    "patient_name": "Arjun Kumar",
                    "patient_initials": "AK",
                    "status": "COMPLETED",
                    "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
                    "has_prescription": True,
                    "prescription_id": "101",
                    "transcript_preview": "Patient complains of headache and fever for the past 3 days..."
                },
                {
                    "consultation_id": "2",
                    "patient_name": "Priya Sharma",
                    "patient_initials": "PS",
                    "status": "COMPLETED",
                    "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
                    "has_prescription": False,
                    "prescription_id": None,
                    "transcript_preview": "Follow-up visit for diabetes management..."
                },
                {
                    "consultation_id": "3",
                    "patient_name": "Rajesh Patel",
                    "patient_initials": "RP",
                    "status": "IN_PROGRESS",
                    "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
                    "has_prescription": True,
                    "prescription_id": "102",
                    "transcript_preview": "Patient reports chest pain and shortness of breath..."
                },
                {
                    "consultation_id": "4",
                    "patient_name": "Sunita Reddy",
                    "patient_initials": "SR",
                    "status": "COMPLETED",
                    "created_at": (datetime.now() - timedelta(days=3)).isoformat(),
                    "has_prescription": True,
                    "prescription_id": "103",
                    "transcript_preview": "Routine checkup, blood pressure slightly elevated..."
                },
                {
                    "consultation_id": "5",
                    "patient_name": "Vikram Singh",
                    "patient_initials": "VS",
                    "status": "COMPLETED",
                    "created_at": (datetime.now() - timedelta(days=5)).isoformat(),
                    "has_prescription": False,
                    "prescription_id": None,
                    "transcript_preview": "Patient complains of back pain after lifting heavy objects..."
                }
            ]
            
            consultations = mock_consultations[:limit]
            if search:
                search_lower = search.lower()
                consultations = [
                    c for c in consultations
                    if search_lower in str(c.get('patient_name', '')).lower()
                    or search_lower in str(c.get('consultation_id', '')).lower()
                    or search_lower in str(c.get('status', '')).lower()
                    or search_lower in str(c.get('transcript_preview', '')).lower()
                    or search_lower in str(c.get('prescription_id', '')).lower()
                    or search_lower in str(c.get('created_at', '')).lower()
                ]
            if status:
                consultations = [
                    c for c in consultations
                    if str(c.get('status', '')).upper() == status
                ]
            if start_date:
                try:
                    start_dt = datetime.fromisoformat(start_date)
                    consultations = [
                        c for c in consultations
                        if c.get('created_at') and datetime.fromisoformat(c['created_at']) >= start_dt
                    ]
                except ValueError:
                    logger.warning(f"Ignoring invalid mock start_date filter: {start_date}")
            if end_date:
                try:
                    end_dt = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59)
                    consultations = [
                        c for c in consultations
                        if c.get('created_at') and datetime.fromisoformat(c['created_at']) <= end_dt
                    ]
                except ValueError:
                    logger.warning(f"Ignoring invalid mock end_date filter: {end_date}")

            consultations = consultations[:limit]
            return jsonify({
                'success': True,
                'consultations': consultations,
                'count': len(consultations)
            }), 200
        
        # Import ConsultationService
        from services.consultation_service import ConsultationService
        
        # Call ConsultationService.get_recent_consultations()
        consultations = ConsultationService.get_recent_consultations(
            user_id=user_id,
            db_manager=database_manager,
            limit=limit,
            search=search or None,
            status=status or None,
            start_date=start_date or None,
            end_date=end_date or None
        )
        
        # Return JSON response with consultation list
        logger.info(f"Retrieved {len(consultations)} consultations for user {user_id}")
        return jsonify({
            'success': True,
            'consultations': consultations,
            'count': len(consultations)
        }), 200
        
    except Exception as e:
        # Log error with sufficient detail for debugging
        logger.error(f"Failed to retrieve consultations: {str(e)}", exc_info=True)
        
        # Return user-friendly error message without exposing internal details
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve consultations. Please try again later.'
        }), 500


# AWS Connectivity check endpoint
@app.route('/health/aws-connectivity', methods=['GET'])
def aws_connectivity_check():
    """AWS connectivity check endpoint for deployment validation"""
    logger = logging.getLogger(__name__)
    import time
    
    try:
        if not config_manager:
            return jsonify({
                'status': 'error',
                'message': 'Configuration manager not initialized'
            }), 503
        
        # Create connectivity checker
        region = config_manager.get('aws_region')
        check_timeout = config_manager.get('aws_connectivity_check_timeout', 5)
        checker = AWSConnectivityChecker(region, check_timeout=check_timeout)
        
        # Prepare config for checks
        check_config = {
            'cognito_user_pool_id': config_manager.get('cognito_user_pool_id'),
            'cognito_client_id': config_manager.get('cognito_client_id'),
            's3_audio_bucket': config_manager.get('s3_audio_bucket'),
            's3_pdf_bucket': config_manager.get('s3_pdf_bucket'),
            'db_secret_name': config_manager.get('db_secret_name'),
            'enable_comprehend_medical': config_manager.get('enable_comprehend_medical', True),
            'comprehend_region': config_manager.get('aws_comprehend_region')
        }
        
        # Run all checks
        results = checker.run_all_checks(check_config)
        
        # Return appropriate status code
        if results['overall_status'] == 'healthy':
            return jsonify(results), 200
        else:
            return jsonify(results), 503
            
    except Exception as e:
        logger.error(f"AWS connectivity check error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Connectivity check failed: {str(e)}',
            'timestamp': time.time()
        }), 503


# Health check endpoint
@app.route('/health/live', methods=['GET'])
def health_live():
    """Lightweight liveness endpoint for ECS/ALB health checks"""
    import time
    return jsonify({
        'status': 'alive',
        'timestamp': time.time()
    }), 200


# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    logger = logging.getLogger(__name__)
    import time
    
    start_time = time.time()
    health_status = {
        'status': 'healthy',
        'timestamp': time.time(),
        'checks': {}
    }
    
    try:
        # Check database connectivity
        if database_manager:
            db_healthy = database_manager.health_check()
            health_status['checks']['database'] = 'healthy' if db_healthy else 'unhealthy'
            
            if not db_healthy:
                health_status['status'] = 'unhealthy'
            
            # Check migration status
            try:
                from migrations.migration_manager import MigrationManager
                migration_manager = MigrationManager(database_manager)
                migration_status = migration_manager.get_migration_status()
                health_status['checks']['migrations'] = {
                    'status': migration_status.get('status', 'unknown'),
                    'applied': migration_status.get('applied_count', 0),
                    'pending': migration_status.get('pending_count', 0)
                }
                
                if migration_status.get('pending_count', 0) > 0:
                    health_status['checks']['migrations']['warning'] = 'Pending migrations detected'
            except Exception as e:
                health_status['checks']['migrations'] = 'error'
                logger.error(f"Migration status check failed: {str(e)}")
        else:
            health_status['checks']['database'] = 'not_initialized'
            health_status['status'] = 'unhealthy'
        
        # Check Secrets Manager connectivity
        try:
            if config_manager:
                # Try to retrieve a test value
                test_secret = config_manager.get('aws_region')
                health_status['checks']['secrets_manager'] = 'healthy' if test_secret else 'unhealthy'
            else:
                health_status['checks']['secrets_manager'] = 'not_initialized'
                health_status['status'] = 'unhealthy'
        except Exception as e:
            health_status['checks']['secrets_manager'] = 'unhealthy'
            health_status['status'] = 'unhealthy'
            logger.error(f"Secrets Manager health check failed: {str(e)}")
        
        # Check if health check took too long (> 5 seconds)
        duration = time.time() - start_time
        if duration > 5.0:
            health_status['status'] = 'timeout'
            health_status['message'] = 'Health check exceeded timeout'
            return jsonify(health_status), 503
        
        # Return appropriate status code
        if health_status['status'] == 'healthy':
            return jsonify(health_status), 200
        else:
            return jsonify(health_status), 503
            
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Health check failed',
            'timestamp': time.time()
        }), 503


# Cleanup handler
@app.teardown_appcontext
def cleanup(error=None):
    """Cleanup resources on application shutdown"""
    # Do not close the global connection pool per-request.
    # Closing here causes "connection pool is closed" on subsequent requests.
    if os.getenv('CLOSE_DB_ON_TEARDOWN', 'false').lower() in ('1', 'true', 'yes'):
        if database_manager:
            database_manager.close_all_connections()


# Graceful shutdown handler
def handle_shutdown(signum, frame):
    """Handle shutdown signals for graceful cleanup"""
    logger = logging.getLogger(__name__)
    logger.info(f"Received shutdown signal: {signum}")
    
    # Cleanup SocketIO resources
    if socketio:
        from socketio_handlers import shutdown_handler
        shutdown_handler(socketio)
    
    # Exit
    import sys
    sys.exit(0)


# Register signal handlers
import signal
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
