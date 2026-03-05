# SEVA Arogya Prescription Enhancement - Integration Guide

## Overview

This guide explains the prescription workflow enhancement that has been integrated into the SEVA Arogya Flask application.

## ✅ Completed Integration

### 1. Database Migrations (5 files) - COMPLETED
- `migrations/004_add_prescription_state_management.sql` ✅
- `migrations/005_add_prescription_sections_metadata.sql` ✅
- `migrations/006_create_hospitals_table.sql` ✅
- `migrations/007_create_doctors_table.sql` ✅
- `migrations/008_create_user_roles_table.sql` ✅

All migrations run automatically on app startup via the existing migration manager.

### 2. Backend Services (5 classes) - COMPLETED
- `services/prescription_service.py` - Prescription state machine and workflow ✅
- `services/rbac_service.py` - Role-based access control ✅
- `services/pdf_generator.py` - PDF generation with ReportLab ✅
- `services/cleanup_scheduler.py` - Automated 30-day deletion ✅
- `services/cloudwatch_service.py` - CloudWatch logs querying ✅

### 3. API Routes (2 blueprints) - COMPLETED
- `routes/prescription_routes.py` - 11 prescription management endpoints ✅
- `routes/hospital_routes.py` - Hospital, doctor, profile, logs, thank-you endpoints ✅

### 4. Extended Services - COMPLETED
- `aws_services/bedrock_client.py` - Added `extract_prescription_sections()` method ✅

### 5. App Integration - COMPLETED
- Services initialized in `app.py` ✅
- Blueprints registered in `app.py` ✅
- Cleanup scheduler started automatically ✅
- Dependencies added to `requirements.txt` ✅

### 6. Seed Data Script - COMPLETED
- `scripts/seed_hospitals.py` - Sample hospitals, doctors, and user roles ✅

## Installation & Setup

### Step 1: Install Dependencies

Dependencies have been added to `requirements.txt`:
```
reportlab==4.0.7
APScheduler==3.10.4
```

Install:
```bash
pip install -r requirements.txt
```

### Step 2: Run Database Migrations

Migrations run automatically on app startup. To run manually:
```bash
python migrations/run_migration.py
```

### Step 3: Seed Sample Data (Optional)

To add sample hospitals, doctors, and user roles:
```bash
python scripts/seed_hospitals.py
```

This creates:
- 2 sample hospitals (SEVA Arogya Medical Center, City General Hospital)
- 3 sample doctors
- 5 sample user roles (2 Doctors, 2 HospitalAdmins, 1 DeveloperAdmin)

### Step 4: Configure Environment Variables

Add to `.env`:
```bash
# Cleanup Scheduler
CLEANUP_SCHEDULE_ENABLED=true
CLEANUP_RETENTION_DAYS=30

# CloudWatch Logs (optional)
CLOUDWATCH_LOG_GROUP_NAME=/aws/seva-arogya/app
AWS_CLOUDWATCH_REGION=us-east-1

# PDF Generation
PDF_GENERATION_TIMEOUT=30
PDF_MAX_FILE_SIZE_MB=10
```

### Step 5: Start the Application

```bash
python app.py
```

The application will:
1. Run database migrations automatically
2. Initialize all services
3. Start the cleanup scheduler
4. Register prescription and hospital routes

## API Endpoints

### Prescription Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/prescriptions` | List prescriptions with filters |
| GET | `/api/v1/prescriptions/:id` | Get single prescription |
| POST | `/api/v1/prescriptions` | Create prescription (Draft) |
| POST | `/api/v1/prescriptions/:id/transition-to-in-progress` | Load Bedrock content |
| POST | `/api/v1/prescriptions/:id/sections/:key/approve` | Approve section |
| POST | `/api/v1/prescriptions/:id/sections/:key/reject` | Reject section |
| PUT | `/api/v1/prescriptions/:id/sections/:key` | Update section content |
| POST | `/api/v1/prescriptions/:id/finalize` | Finalize prescription |
| POST | `/api/v1/prescriptions/:id/pdf` | Generate PDF |
| DELETE | `/api/v1/prescriptions/:id` | Soft delete |
| POST | `/api/v1/prescriptions/:id/restore` | Restore deleted |

### Hospital & User Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/hospitals` | List all hospitals (DeveloperAdmin) |
| GET | `/api/v1/hospitals/:id` | Get hospital details |
| PUT | `/api/v1/hospitals/:id` | Update hospital |
| GET | `/api/v1/hospitals/:id/doctors` | List doctors |
| POST | `/api/v1/hospitals/:id/doctors` | Add doctor |
| DELETE | `/api/v1/hospitals/:id/doctors/:doctor_id` | Remove doctor |
| GET | `/api/v1/profile` | Get user profile |
| GET | `/api/v1/logs` | CloudWatch logs (DeveloperAdmin) |
| GET | `/api/v1/thank-you` | Thank you message |

## Prescription Workflow

### State Machine

```
Draft → InProgress → Finalized
  ↓         ↓           ↓
Deleted ← Deleted ← Deleted
```

### Section Approval Workflow

1. **Draft**: Prescription created, no sections yet
2. **InProgress**: Bedrock content loaded into sections (all Pending)
3. **Section Review**: Doctor approves/rejects each section
4. **Finalization**: When all required sections approved, doctor finalizes
5. **Finalized**: Immutable, PDF generated

### Soft Delete

- Prescriptions can be soft deleted (state → Deleted)
- Metadata preserved for 30 days
- Can be restored within 30 days
- Automatically permanently deleted after 30 days

## Role-Based Access Control

### Roles

1. **Doctor**: Can view/edit own prescriptions only
2. **HospitalAdmin**: Can view all prescriptions in their hospital
3. **DeveloperAdmin**: Can view all prescriptions, access logs

### Permissions

| Action | Doctor | HospitalAdmin | DeveloperAdmin |
|--------|--------|---------------|----------------|
| View own prescriptions | ✅ | ✅ | ✅ |
| View hospital prescriptions | ❌ | ✅ | ✅ |
| View all prescriptions | ❌ | ❌ | ✅ |
| Edit own prescriptions | ✅ | ❌ | ✅ |
| Delete own prescriptions | ✅ | ❌ | ✅ |
| Restore own prescriptions | ✅ | ❌ | ✅ |
| Manage hospital settings | ❌ | ✅ | ✅ |
| View CloudWatch logs | ❌ | ❌ | ✅ |

## What's Next (Frontend Implementation)

The following frontend pages need to be created:

1. **Prescriptions List Page** (`templates/prescriptions_list.html`)
   - Search and filter controls
   - Table with prescription list
   - Section status indicators

2. **Prescription Detail Page** (`templates/prescription_detail.html`)
   - Read-only view of prescription
   - Audio playback
   - Download PDF button
   - Delete/Restore buttons

3. **Prescription Finalization Page** (`templates/prescription_finalize.html`)
   - Section-by-section approval UI
   - Inline editing for rejected sections
   - Finalize button

4. **Thank You Page** (`templates/thank_you.html`)
   - Success message after finalization

5. **Hospital Settings Page** (`templates/hospital_settings.html`)
   - Edit hospital information
   - Manage doctors

6. **Profile Page** (`templates/profile.html`)
   - View user profile and role

7. **Logs Viewer Page** (`templates/logs_viewer.html`)
   - CloudWatch logs with filters (DeveloperAdmin only)

8. **Responsive Sidebar** (`templates/components/sidebar.html`)
   - Role-based menu items
   - Mobile drawer

9. **Transition Overlay** (`templates/components/transition_overlay.html`)
   - Page transition animation

## Testing

### Manual Testing Checklist

- [ ] Create prescription (Draft state)
- [ ] Transition to InProgress (Bedrock content loaded)
- [ ] Approve sections
- [ ] Reject and edit sections
- [ ] Finalize prescription
- [ ] Generate PDF
- [ ] Download PDF
- [ ] Soft delete prescription
- [ ] Restore prescription
- [ ] Wait 30 days for automatic deletion (or test with shorter retention)
- [ ] Test role-based access (Doctor, HospitalAdmin, DeveloperAdmin)
- [ ] Test CloudWatch logs viewer

### Property-Based Tests

53 correctness properties are defined in the design document. Optional property-based tests can be added for comprehensive validation.

## Troubleshooting

### Issue: Migrations not running
- Check database connection
- Verify migration files exist in `migrations/` folder
- Check logs for migration errors

### Issue: Cleanup scheduler not starting
- Check `CLEANUP_SCHEDULE_ENABLED` environment variable
- Verify APScheduler is installed
- Check logs for scheduler errors

### Issue: PDF generation fails
- Verify ReportLab is installed
- Check S3 bucket permissions
- Verify hospital logo URLs are accessible

### Issue: CloudWatch logs not loading
- Verify `CLOUDWATCH_LOG_GROUP_NAME` is set
- Check AWS credentials have CloudWatch permissions
- Verify log group exists in AWS

### Issue: Role-based access not working
- Verify user_roles table is populated
- Check user_id matches Cognito email
- Verify RBAC service is initialized

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│  (Prescriptions List, Detail, Finalization, Settings, etc.) │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      Flask Routes                            │
│  prescription_routes.py  │  hospital_routes.py              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                       Services Layer                         │
│  PrescriptionService │ RBACService │ PDFGenerator │          │
│  CleanupScheduler    │ CloudWatchService                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    AWS Services Layer                        │
│  DatabaseManager │ StorageManager │ BedrockClient           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                         AWS                                  │
│  RDS PostgreSQL │ S3 │ Bedrock │ CloudWatch                 │
└─────────────────────────────────────────────────────────────┘
```

## Summary

The prescription enhancement backend is fully integrated and ready for use. All services are initialized, routes are registered, and the cleanup scheduler is running. The next step is to implement the frontend pages to provide the user interface for the new workflow.
            logger.info("CloudWatch Service initialized")
        
        # Cleanup Scheduler
        cleanup_enabled = os.getenv('CLEANUP_SCHEDULE_ENABLED', 'true').lower() == 'true'
        if cleanup_enabled:
            retention_days = int(os.getenv('CLEANUP_RETENTION_DAYS', '30'))
            cleanup_scheduler = CleanupScheduler(database_manager, storage_manager, retention_days)
            cleanup_scheduler.start()
            logger.info(f"Cleanup Scheduler started ({retention_days}-day retention)")
        
        # Initialize routes
        init_prescription_routes(
            prescription_service,
            rbac_service,
            pdf_generator,
            bedrock_client,  # Use existing bedrock_client
            database_manager
        )
        
        init_hospital_routes(
            rbac_service,
            database_manager,
            cloudwatch_service
        )
        
        # Register blueprints
        app.register_blueprint(prescription_bp)
        app.register_blueprint(hospital_bp)
        
        logger.info("Prescription enhancement routes registered")
        
    except Exception as e:
        logger.error(f"Failed to initialize prescription enhancement: {str(e)}")
        # Don't fail startup - allow app to run without enhancement
```

### Step 4: Add Environment Variables

Add to `.env`:
```bash
# Cleanup Scheduler
CLEANUP_SCHEDULE_ENABLED=true
CLEANUP_RETENTION_DAYS=30

# CloudWatch Logs (optional)
CLOUDWATCH_LOG_GROUP_NAME=/aws/seva-arogya/application
AWS_CLOUDWATCH_REGION=us-east-1

# PDF Generation
PDF_GENERATION_TIMEOUT=30
PDF_MAX_FILE_SIZE_MB=10
```

### Step 5: Seed Initial Data

Create a seed script or manually insert initial hospital and user role data:

```sql
-- Insert default hospital
INSERT INTO hospitals (hospital_id, name, address, phone, email)
VALUES ('default', 'SEVA Arogya Hospital', '123 Healthcare Street', '+91-1234567890', 'info@sevaarogya.com')
ON CONFLICT (hospital_id) DO NOTHING;

-- Insert user roles for existing users
INSERT INTO user_roles (user_id, role, hospital_id)
VALUES 
    ('admin@sevaarogya.com', 'DeveloperAdmin', NULL),
    ('doctor@sevaarogya.com', 'Doctor', 'default')
ON CONFLICT (user_id) DO NOTHING;

-- Insert doctor profiles
INSERT INTO doctors (doctor_id, hospital_id, name, specialty)
VALUES ('doctor@sevaarogya.com', 'default', 'Dr. Example', 'General Medicine')
ON CONFLICT (doctor_id) DO NOTHING;
```

## API Endpoints Reference

### Prescription Management

- `GET /api/v1/prescriptions` - List prescriptions with filters
- `GET /api/v1/prescriptions/:id` - Get single prescription
- `POST /api/v1/prescriptions` - Create prescription (Draft)
- `POST /api/v1/prescriptions/:id/transition-to-in-progress` - Load Bedrock content
- `POST /api/v1/prescriptions/:id/sections/:key/approve` - Approve section
- `POST /api/v1/prescriptions/:id/sections/:key/reject` - Reject section
- `PUT /api/v1/prescriptions/:id/sections/:key` - Update section content
- `POST /api/v1/prescriptions/:id/finalize` - Finalize prescription
- `POST /api/v1/prescriptions/:id/pdf` - Generate PDF
- `DELETE /api/v1/prescriptions/:id` - Soft delete
- `POST /api/v1/prescriptions/:id/restore` - Restore deleted

### Hospital Management

- `GET /api/v1/hospitals` - List hospitals (DeveloperAdmin)
- `GET /api/v1/hospitals/:id` - Get hospital details
- `PUT /api/v1/hospitals/:id` - Update hospital
- `GET /api/v1/hospitals/:id/doctors` - List doctors
- `POST /api/v1/hospitals/:id/doctors` - Add doctor
- `DELETE /api/v1/hospitals/:id/doctors/:doctor_id` - Remove doctor

### User & Logs

- `GET /api/v1/profile` - Get user profile
- `GET /api/v1/logs` - Get CloudWatch logs (DeveloperAdmin)
- `GET /api/v1/thank-you` - Thank you page data

## Frontend Integration

### Required Frontend Pages

1. **Prescriptions List** (`/prescriptions`)
   - Search and filter prescriptions
   - Display table with state and section statuses
   - Navigate to single prescription view

2. **Single Prescription View** (`/prescriptions/:id`)
   - Display prescription details
   - Show audio files and transcriptions
   - PDF download button
   - Delete/Restore buttons (based on permissions)

3. **Prescription Finalization** (`/prescriptions/:id/finalize`)
   - Display sections with Bedrock content
   - Approve/Reject buttons per section
   - Inline editing for rejected sections
   - Finalize button (enabled when all approved)

4. **Thank You Page** (`/thank-you`)
   - Display success message
   - "Back to Prescriptions" button

5. **Hospital Settings** (`/hospital-settings`)
   - Edit hospital information
   - Manage doctors

6. **Profile Page** (`/profile`)
   - Display doctor profile (read-only)

7. **CloudWatch Logs** (`/logs`)
   - Date range selector
   - Search filter
   - Log entries table
   - (DeveloperAdmin only)

### Sidebar Navigation

Update sidebar to show role-based menu items:

```javascript
// Get menu items from API
fetch('/api/v1/profile')
  .then(res => res.json())
  .then(data => {
    const role = data.profile.role;
    // Render menu based on role
    renderSidebar(role);
  });
```

## Testing

### Manual Testing Checklist

1. **Database**
   - [ ] Migrations run successfully
   - [ ] Tables created with correct schema
   - [ ] Seed data inserted

2. **Services**
   - [ ] Prescription service creates prescriptions
   - [ ] State transitions work correctly
   - [ ] RBAC filters prescriptions by role
   - [ ] PDF generation works
   - [ ] Cleanup scheduler starts

3. **API Endpoints**
   - [ ] List prescriptions with filters
   - [ ] Create prescription in Draft state
   - [ ] Transition to InProgress loads Bedrock content
   - [ ] Section approval/rejection works
   - [ ] Finalization requires all approvals
   - [ ] PDF generation returns signed URL
   - [ ] Soft delete and restore work
   - [ ] Hospital CRUD operations work
   - [ ] Profile endpoint returns user data
   - [ ] CloudWatch logs endpoint works (if configured)

4. **Permissions**
   - [ ] Doctor sees only own prescriptions
   - [ ] HospitalAdmin sees hospital prescriptions
   - [ ] DeveloperAdmin sees all prescriptions
   - [ ] Only creator can finalize/delete
   - [ ] Restore works within 30 days

## Troubleshooting

### Common Issues

1. **Migrations fail**
   - Check database connection
   - Ensure PostgreSQL version supports JSONB
   - Run migrations manually to see detailed errors

2. **PDF generation fails**
   - Ensure ReportLab is installed
   - Check S3 bucket permissions
   - Verify storage_manager is initialized

3. **Cleanup scheduler doesn't start**
   - Check CLEANUP_SCHEDULE_ENABLED environment variable
   - Ensure APScheduler is installed
   - Check logs for initialization errors

4. **CloudWatch logs not working**
   - Verify CLOUDWATCH_LOG_GROUP_NAME is set
   - Check AWS credentials have CloudWatch permissions
   - Ensure log group exists in AWS

5. **Bedrock extraction fails**
   - Verify Bedrock model supports function calling
   - Check AWS credentials and region
   - Ensure transcript text is not empty

## Next Steps

1. Create frontend pages (HTML/JS)
2. Add transition overlay component
3. Implement responsive sidebar
4. Add property-based tests
5. Add integration tests
6. Deploy to staging environment

## Support

For issues or questions, check:
- Application logs: `logs/app.log`
- Database logs: Check PostgreSQL logs
- AWS CloudWatch: Check service logs
- Migration logs: `migrations/` folder

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│  (Prescriptions List, Single View, Finalization, etc.)      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Flask Routes                            │
│  prescription_routes.py  │  hospital_routes.py              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Services                              │
│  PrescriptionService │ RBACService │ PDFGenerator            │
│  CleanupScheduler    │ CloudWatchService                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data & External Services                  │
│  PostgreSQL  │  S3  │  Bedrock  │  CloudWatch               │
└─────────────────────────────────────────────────────────────┘
```

## Conclusion

The prescription enhancement is now ready for integration. Follow the steps above to wire everything together and start testing. The architecture is modular and follows existing patterns, making it easy to maintain and extend.
