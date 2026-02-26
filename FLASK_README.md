# SEVA Arogya - Flask Application

Voice-enabled clinical note capture and prescription generation system.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python app.py
```

The application will start on `http://localhost:5000`

### 3. Access the Application

Open your browser and navigate to:
- Login: `http://localhost:5000/login`
- Home: `http://localhost:5000/home` (requires login)
- Transcription: `http://localhost:5000/transcription` (requires login)
- Final Prescription: `http://localhost:5000/final-prescription` (requires login)

**Default Login Credentials:**
- Email: `doctor@hospital.com` | Password: `password123`
- Email: `admin@seva.com` | Password: `admin123`
- Email: `demo@demo.com` | Password: `demo`
- Or use any email/password (demo mode accepts all credentials)

## Application Structure

```
.
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── templates/                      # HTML templates
│   ├── base.html                  # Base template with shared styles
│   ├── login.html                 # Login page
│   ├── home.html                  # Home page (start consultation)
│   ├── transcription.html         # Voice capture page
│   └── final_prescription.html    # Prescription review page
└── screens/                        # Original screen designs (reference)
```

## Features Implemented

### ✅ Login Screen
- Email/password login form
- Password visibility toggle
- Social sign-in buttons (Google, Apple)
- Responsive design matching screen.png

### ✅ Home Screen
- Search bar for patients
- Large mic button to start consultation
- Recent consultations list
- Centered hero layout

### ✅ Transcription Screen
- Recording status with timer
- Real-time transcription display
- Smart suggestions carousel
- Stop and review button

### ✅ Final Prescription Screen
- Professional prescription layout
- Patient details section
- Vitals display
- Diagnosis section
- Medications table
- Clinical notes
- Share and finalize buttons

## Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Redirect to login or home |
| `/login` | GET | Login page |
| `/home` | GET | Home page (requires auth) |
| `/transcription` | GET | Voice capture page (requires auth) |
| `/final-prescription` | GET | Prescription review (requires auth) |
| `/api/v1/auth/login` | POST | Login API endpoint |
| `/api/v1/auth/logout` | POST | Logout API endpoint |
| `/api/v1/transcribe` | POST | Audio transcription API |
| `/api/v1/prescriptions` | POST | Create prescription API |

## Design System

### Colors
- Primary: `#127ae2` (Blue)
- Background Light: `#f6f7f8`
- Background Dark: `#101922`

### Typography
- Font Family: Lexend (sans-serif)
- Material Symbols for icons

### Components
- iOS-style inputs with rounded corners
- Pill-shaped buttons and chips
- Card-based layouts
- Subtle shadows and glows
- Responsive mobile-first design

## Next Steps

### Backend Integration
1. Implement AWS Cognito authentication
2. Add AWS Transcribe Medical for voice-to-text
3. Integrate AWS Comprehend Medical for entity extraction
4. Add PostgreSQL database connection
5. Implement PDF generation service
6. Add AWS S3 for PDF storage

### Frontend Enhancements
1. Add Web Audio API for actual voice recording
2. Implement real-time transcription updates
3. Add form validation and error handling
4. Implement edit functionality for prescription fields
5. Add loading states and animations

### Security
1. Add CSRF protection
2. Implement proper JWT token handling
3. Add rate limiting
4. Enable HTTPS in production
5. Add input sanitization

## Development Notes

- The application uses session-based authentication (placeholder)
- All API endpoints are placeholders for future AWS integration
- The UI matches the exact design from the screen.png files
- Tailwind CSS is loaded via CDN for rapid development
- Material Symbols are used for all icons

## Production Deployment

For production deployment:
1. Set `SECRET_KEY` environment variable
2. Disable debug mode
3. Use a production WSGI server (Gunicorn)
4. Configure AWS services (Cognito, Transcribe, Comprehend, S3, RDS)
5. Set up proper logging and monitoring
6. Enable HTTPS with SSL certificates

## License

Proprietary - SEVA Arogya
