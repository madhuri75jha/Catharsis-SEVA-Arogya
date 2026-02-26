"""
SEVA Arogya - Flask Application
Voice-enabled clinical note capture and prescription generation system
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size


# Authentication decorator (placeholder for now)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
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


# API Endpoints (placeholders for future implementation)
@app.route('/api/v1/auth/login', methods=['POST'])
def api_login():
    """API endpoint for login"""
    data = request.get_json()
    email = data.get('email', '')
    password = data.get('password', '')
    
    # Demo credentials for testing
    # TODO: Implement actual authentication with AWS Cognito
    DEMO_USERS = {
        'doctor@hospital.com': 'password123',
        'admin@seva.com': 'admin123',
        'demo@demo.com': 'demo'
    }
    
    # Check credentials or allow any login for demo purposes
    if email in DEMO_USERS and DEMO_USERS[email] == password:
        session['user_id'] = email
        session['user_name'] = email.split('@')[0].title()
        return jsonify({'success': True, 'message': 'Login successful'})
    elif email and password:  # Allow any credentials for demo
        session['user_id'] = email
        session['user_name'] = email.split('@')[0].title()
        return jsonify({'success': True, 'message': 'Login successful (demo mode)'})
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401


@app.route('/api/v1/auth/logout', methods=['POST'])
def api_logout():
    """API endpoint for logout"""
    session.pop('user_id', None)
    return jsonify({'success': True, 'message': 'Logout successful'})


@app.route('/api/v1/transcribe', methods=['POST'])
@login_required
def api_transcribe():
    """API endpoint for audio transcription"""
    # TODO: Implement AWS Transcribe Medical integration
    return jsonify({'success': True, 'transcript': 'Sample transcription'})


@app.route('/api/v1/prescriptions', methods=['POST'])
@login_required
def api_create_prescription():
    """API endpoint to create prescription"""
    # TODO: Implement prescription creation logic
    return jsonify({'success': True, 'prescription_id': '12345'})


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
