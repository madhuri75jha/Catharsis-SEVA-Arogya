# SEVA Arogya - Project Structure

## Directory Layout

```
seva-arogya/
├── app.py                          # Main Flask application entry point
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
├── .gitignore                      # Git ignore rules
├── run.sh                          # Unix/Linux run script
├── run.bat                         # Windows run script
├── FLASK_README.md                 # Flask app documentation
├── PROJECT_STRUCTURE.md            # This file
├── requirements.md                 # System requirements document
├── design.md                       # System design document
├── Readme.md                       # Project overview
│
├── templates/                      # Jinja2 HTML templates
│   ├── base.html                  # Base template (shared layout)
│   ├── login.html                 # Login page
│   ├── home.html                  # Home/dashboard page
│   ├── transcription.html         # Voice capture page
│   └── final_prescription.html    # Prescription review page
│
└── screens/                        # Original UI designs (reference)
    ├── Login Screen/
    │   ├── code.html
    │   └── screen.png
    ├── Home Screen/
    │   ├── code.html
    │   └── screen.png
    ├── Transcription Page/
    │   ├── code.html
    │   └── screen.png
    └── Final Prescription Screen/
        ├── code.html
        └── screen.png
```

## File Descriptions

### Core Application Files

#### `app.py`
Main Flask application with:
- Route definitions for all pages
- API endpoint placeholders
- Authentication decorator
- Error handlers
- Session management

#### `requirements.txt`
Python package dependencies:
- Flask 3.0.0
- Werkzeug 3.0.1
- Jinja2 3.1.2
- python-dotenv 1.0.0

#### `.env.example`
Template for environment variables:
- Flask configuration
- AWS credentials (for future use)
- Database connection strings
- S3 bucket configuration

### Templates

#### `templates/base.html`
Base template containing:
- Tailwind CSS configuration
- Google Fonts (Lexend, Material Symbols)
- Global styles and animations
- Shared layout structure
- Background decorations

#### `templates/login.html`
Login page with:
- Email/password form
- Password visibility toggle
- Social sign-in buttons (Google, Apple)
- Sign-up link
- Form validation and API integration

#### `templates/home.html`
Home page featuring:
- Patient search bar
- Large mic button for starting consultation
- Recent consultations carousel
- Navigation to transcription page

#### `templates/transcription.html`
Voice capture page with:
- Recording status indicator
- Live timer
- Transcription text display
- Smart suggestions carousel
- Stop and review button

#### `templates/final_prescription.html`
Prescription review page including:
- Clinic header
- Patient details section
- Vitals display
- Diagnosis section
- Medications table
- Doctor signature area
- Clinical notes
- Share and finalize buttons

### Documentation

#### `FLASK_README.md`
Flask application documentation:
- Quick start guide
- Installation instructions
- Route descriptions
- Design system details
- Next steps for development

#### `requirements.md`
Comprehensive system requirements:
- Executive summary
- Core features
- Non-functional requirements
- Technical specifications
- Architecture diagrams

#### `design.md`
System design document:
- Architecture overview
- Technology stack
- Database schema
- API design
- Security architecture
- Deployment strategy

### Scripts

#### `run.sh` (Unix/Linux/Mac)
Bash script to:
- Create virtual environment
- Install dependencies
- Start Flask server

#### `run.bat` (Windows)
Batch script to:
- Create virtual environment
- Install dependencies
- Start Flask server

## Page Flow

```
┌─────────┐
│  Login  │
└────┬────┘
     │
     ▼
┌─────────┐
│  Home   │ ◄─┐
└────┬────┘   │
     │        │
     ▼        │
┌──────────────┐
│Transcription │
└────┬─────────┘
     │
     ▼
┌──────────────────┐
│Final Prescription│
└──────────────────┘
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout

### Transcription
- `POST /api/v1/transcribe` - Audio transcription

### Prescriptions
- `POST /api/v1/prescriptions` - Create prescription
- `GET /api/v1/prescriptions` - List prescriptions
- `GET /api/v1/prescriptions/{id}` - Get specific prescription

### Profile
- `GET /api/v1/profile` - Get doctor profile
- `PUT /api/v1/profile` - Update profile

## Design System

### Colors
- **Primary**: `#127ae2` (Blue)
- **Background Light**: `#f6f7f8`
- **Background Dark**: `#101922`

### Typography
- **Font**: Lexend (sans-serif)
- **Weights**: 300, 400, 500, 600, 700

### Components
- iOS-style inputs
- Pill-shaped buttons
- Card layouts
- Material icons
- Subtle shadows and glows

## Technology Stack

### Frontend
- HTML5
- Tailwind CSS (via CDN)
- Vanilla JavaScript
- Material Symbols icons
- Google Fonts

### Backend
- Python 3.9+
- Flask 3.0
- Jinja2 templating
- Session-based auth (placeholder)

### Future Integration
- AWS Cognito (authentication)
- AWS Transcribe Medical (speech-to-text)
- AWS Comprehend Medical (NLP)
- AWS S3 (PDF storage)
- PostgreSQL (database)

## Development Workflow

1. **Setup**: Run `run.sh` or `run.bat`
2. **Development**: Edit templates and app.py
3. **Testing**: Access http://localhost:5000
4. **Iteration**: Make changes, Flask auto-reloads

## Next Development Phases

### Phase 1: Backend Integration
- AWS Cognito authentication
- Database setup (PostgreSQL)
- AWS Transcribe Medical integration
- AWS Comprehend Medical integration

### Phase 2: Features
- Real voice recording
- Live transcription
- PDF generation
- S3 storage integration

### Phase 3: Enhancement
- Form validation
- Error handling
- Loading states
- Edit functionality

### Phase 4: Production
- Security hardening
- Performance optimization
- Monitoring setup
- Deployment automation

## Notes

- All UI pages match the exact design from screen.png files
- Tailwind CSS is used for rapid styling
- Material Symbols provide consistent iconography
- Mobile-first responsive design
- Session-based auth is a placeholder for AWS Cognito
- API endpoints are placeholders for future AWS integration
