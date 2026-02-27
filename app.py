"""
SEVA Arogya - Flask Application
Voice-enabled clinical note capture and prescription generation system
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_cors import CORS
from functools import wraps
import os
import logging
from dotenv import load_dotenv

# Import AWS service managers
from aws_services.config_manager import ConfigManager
from aws_services.auth_manager import AuthManager
from aws_services.storage_manager import StorageManager
from aws_services.transcribe_manager import TranscribeManager
from aws_services.comprehend_manager import ComprehendManager
from aws_services.database_manager import DatabaseManager

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

# Global service managers (initialized in init_app)
config_manager = None
auth_manager = None
storage_manager = None
transcribe_manager = None
comprehend_manager = None
database_manager = None


def init_app():
    """Initialize application with AWS services"""
    global config_manager, auth_manager, storage_manager, transcribe_manager, comprehend_manager, database_manager
    
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
        
        # Comprehend Manager
        comprehend_manager = ComprehendManager(region=region)
        
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
                    logger.info("Database tables created/verified")
                except Exception as e:
                    logger.error(f"Failed to create database tables: {str(e)}")
        else:
            logger.error("Database credentials not available")
            raise Exception("Database configuration failed")
        
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


@app.route('/login')
def login():
    """Login page"""
    return render_template('login.html')


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


@app.route('/final-prescription')
@login_required
def final_prescription():
    """Final prescription review page"""
    return render_template('final_prescription.html')


# API Endpoints
@app.route('/api/v1/auth/login', methods=['POST'])
def api_login():
    """API endpoint for login with AWS Cognito"""
    logger = logging.getLogger(__name__)
    
    try:
        data = request.get_json()
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
            
            # Get user info
            user_info = auth_manager.validate_token(tokens['access_token'])
            if user_info:
                session['user_name'] = user_info['attributes'].get('name', email.split('@')[0].title())
            else:
                session['user_name'] = email.split('@')[0].title()
            
            logger.info(f"User logged in successfully: {email}")
            return jsonify({'success': True, 'message': 'Login successful'})
        else:
            logger.warning(f"Login failed for user: {email}")
            message = auth_error['message'] if auth_error else 'Invalid credentials'
            error_code = auth_error['code'] if auth_error else None
            return jsonify({'success': False, 'message': message, 'error_code': error_code}), 401
            
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred during login'}), 500


@app.route('/api/v1/auth/register', methods=['POST'])
def api_register():
    """API endpoint for user registration with AWS Cognito"""
    logger = logging.getLogger(__name__)
    
    try:
        data = request.get_json()
        email = data.get('email', '')
        password = data.get('password', '')
        name = data.get('name', '')
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password required'}), 400
        
        # Register with Cognito
        attributes = {}
        if name:
            attributes['name'] = name
        
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
        data = request.get_json()
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
        data = request.get_json()
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
        data = request.get_json()
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


@app.route('/api/v1/transcribe', methods=['POST'])
@login_required
def api_transcribe():
    """API endpoint for audio transcription with AWS Transcribe Medical"""
    logger = logging.getLogger(__name__)
    
    try:
        data = request.get_json()
        s3_key = data.get('s3_key', '')
        
        if not s3_key:
            return jsonify({'success': False, 'message': 'S3 key required'}), 400
        
        user_id = session.get('user_id')
        
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
            
            logger.info(f"Transcription job started: {job_id}")
            return jsonify({
                'success': True,
                'message': 'Transcription started',
                'job_id': job_id
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
        status_info = transcribe_manager.get_job_status(job_id)
        
        if status_info:
            # Update database if status changed
            transcription = Transcription.get_by_job_id(job_id, database_manager)
            if transcription and transcription.status != status_info['status']:
                transcription.status = status_info['status']
                transcription.update(database_manager)
            
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
        if transcription:
            transcription.transcript_text = transcript_text
            transcription.medical_entities = entities
            transcription.status = 'COMPLETED'
            transcription.update(database_manager)
        
        logger.info(f"Transcript and entities retrieved for job: {job_id}")
        return jsonify({
            'success': True,
            'transcript': transcript_text,
            'entities': entities,
            'categorized_entities': categorized_entities
        })
        
    except Exception as e:
        logger.error(f"Result retrieval error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


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
    if database_manager:
        database_manager.close_all_connections()


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
