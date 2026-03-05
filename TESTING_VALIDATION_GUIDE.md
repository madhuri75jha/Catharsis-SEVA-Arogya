# SEVA Arogya Prescription Enhancement - Testing & Validation Guide

## Overview

This guide provides comprehensive testing procedures for the prescription enhancement feature, covering unit tests, integration tests, end-to-end workflows, and validation criteria.

## Pre-Testing Setup

### 1. Environment Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set up test database
export DATABASE_URL="postgresql://user:password@localhost:5432/seva_arogya_test"

# Run migrations
python scripts/run_migrations.py

# Seed test data
python scripts/seed_hospitals.py
```

### 2. Test User Setup

Create test users in Cognito with different roles:

**Doctor User:**
- Email: `doctor@test.com`
- Password: `Test123!`
- Custom attributes:
  - `custom:role` = `Doctor`
  - `custom:hospital_id` = `hosp_12345`

**Hospital Admin User:**
- Email: `admin@test.com`
- Password: `Test123!`
- Custom attributes:
  - `custom:role` = `HospitalAdmin`
  - `custom:hospital_id` = `hosp_12345`

**Developer Admin User:**
- Email: `devadmin@test.com`
- Password: `Test123!`
- Custom attributes:
  - `custom:role` = `DeveloperAdmin`
  - `custom:hospital_id` = `default`

## Testing Checklist

### ✅ Database Schema Validation

- [ ] All migration files executed successfully
- [ ] `prescriptions` table has new columns: `state`, `sections`, `bedrock_payload`, `finalized_at`, `finalized_by`, `deleted_at`, `deleted_by`, `pre_deleted_state`
- [ ] `hospitals` table created with all required fields
- [ ] `doctors` table created with foreign key to hospitals
- [ ] `user_roles` table created with role constraints
- [ ] All indexes created successfully
- [ ] State constraint check works (only allows Draft, InProgress, Finalized, Deleted)
- [ ] Role constraint check works (only allows Doctor, HospitalAdmin, DeveloperAdmin)

**Validation SQL:**
```sql
-- Check prescriptions table columns
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'prescriptions';

-- Check state constraint
SELECT constraint_name, check_clause 
FROM information_schema.check_constraints 
WHERE constraint_name LIKE '%state%';

-- Verify indexes
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'prescriptions';
```

### ✅ Backend Services Testing

#### PrescriptionService

- [ ] `create_prescription()` creates prescription in Draft state
- [ ] `transition_to_in_progress()` loads Bedrock content and sets sections
- [ ] `approve_section()` sets section status to Approved
- [ ] `reject_section()` sets section status to Rejected
- [ ] `update_section_content()` resets status to Pending
- [ ] `can_finalize()` returns true only when all required sections approved
- [ ] `finalize_prescription()` sets state to Finalized and records metadata
- [ ] `soft_delete()` sets deleted_at and preserves state
- [ ] `restore_prescription()` clears deletion metadata and restores state
- [ ] State transitions follow valid_transitions rules

**Test Commands:**
```python
# Test prescription creation
from services.prescription_service import PrescriptionService
service = PrescriptionService(database_manager)

prescription_id = service.create_prescription(
    user_id="doctor@test.com",
    consultation_id="test_consultation_1",
    hospital_id="hosp_12345",
    patient_name="Test Patient"
)
print(f"Created prescription: {prescription_id}")

# Verify state is Draft
prescription = service.get_prescription(prescription_id)
assert prescription['state'] == 'Draft'
```

#### RBACService

- [ ] `get_user_role()` returns correct role from user_roles table
- [ ] `get_user_hospital()` returns correct hospital_id
- [ ] `check_permission()` enforces creator-only for finalize/delete
- [ ] `check_permission()` allows DeveloperAdmin to restore any prescription
- [ ] `get_prescription_filter_sql()` returns correct WHERE clause for each role
- [ ] Doctor sees only own prescriptions
- [ ] HospitalAdmin sees hospital prescriptions
- [ ] DeveloperAdmin sees all prescriptions

#### PDFGenerator

- [ ] `generate_prescription_pdf()` creates valid PDF file
- [ ] PDF includes hospital branding (logo, name, address)
- [ ] PDF renders all sections in correct order
- [ ] PDF only renders existing sections (skips empty ones)
- [ ] Medications formatted as table
- [ ] Doctor signature included in footer
- [ ] `upload_to_s3()` successfully uploads PDF
- [ ] `get_signed_url()` returns valid signed URL

#### CleanupScheduler

- [ ] Scheduler starts successfully
- [ ] `find_expired_prescriptions()` identifies prescriptions > 30 days old
- [ ] `permanently_delete_prescription()` removes database record
- [ ] `delete_s3_objects()` removes audio, transcription, and PDF files
- [ ] Cleanup runs on schedule (daily)

### ✅ API Endpoints Testing

#### Authentication

```bash
# Test login
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"email":"doctor@test.com","password":"Test123!"}'

# Expected: {"success":true,"message":"Login successful"}
# Verify session has user_role set
```

#### Prescription Management

```bash
# Create prescription
curl -X POST http://localhost:5000/api/v1/prescriptions \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"consultation_id":"test_1","patient_name":"John Doe","hospital_id":"hosp_12345"}'

# List prescriptions
curl http://localhost:5000/api/v1/prescriptions \
  -b cookies.txt

# Get single prescription
curl http://localhost:5000/api/v1/prescriptions/1 \
  -b cookies.txt

# Transition to InProgress
curl -X POST http://localhost:5000/api/v1/prescriptions/1/transition-to-in-progress \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{}'

# Approve section
curl -X POST http://localhost:5000/api/v1/prescriptions/1/sections/diagnosis/approve \
  -b cookies.txt

# Finalize prescription
curl -X POST http://localhost:5000/api/v1/prescriptions/1/finalize \
  -b cookies.txt

# Generate PDF
curl -X POST http://localhost:5000/api/v1/prescriptions/1/pdf \
  -b cookies.txt

# Soft delete
curl -X DELETE http://localhost:5000/api/v1/prescriptions/1 \
  -b cookies.txt

# Restore
curl -X POST http://localhost:5000/api/v1/prescriptions/1/restore \
  -b cookies.txt
```

#### Hospital Management

```bash
# Get hospitals (DeveloperAdmin only)
curl http://localhost:5000/api/v1/hospitals \
  -b cookies.txt

# Get hospital details
curl http://localhost:5000/api/v1/hospitals/hosp_12345 \
  -b cookies.txt

# Update hospital
curl -X PUT http://localhost:5000/api/v1/hospitals/hosp_12345 \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"name":"Updated Hospital Name"}'

# Get doctors
curl http://localhost:5000/api/v1/hospitals/hosp_12345/doctors \
  -b cookies.txt
```

#### CloudWatch Logs

```bash
# Get logs (DeveloperAdmin only)
curl "http://localhost:5000/api/v1/logs?limit=100" \
  -b cookies.txt
```

### ✅ Frontend Testing

#### Sidebar Navigation

- [ ] Sidebar displays on all pages
- [ ] Mobile: Hamburger menu opens/closes sidebar
- [ ] Desktop: Sidebar fixed on left side
- [ ] Menu items filtered by role:
  - Doctor: Home, My Prescriptions, Profile
  - HospitalAdmin: Home, Prescriptions, Hospital Settings, Profile
  - DeveloperAdmin: Home, All Prescriptions, Hospital Settings, CloudWatch Logs, Profile
- [ ] Active route highlighted
- [ ] User profile section shows name and role
- [ ] Clicking profile navigates to /profile

#### Transition Overlay

- [ ] Overlay shows on page navigation
- [ ] SEVA Arogya logo and text displayed
- [ ] Icon animates (slide up)
- [ ] Fade in/out animations smooth (500ms)
- [ ] Overlay hides after navigation completes

#### Prescriptions List Page

- [ ] Search box filters prescriptions (debounced 300ms)
- [ ] State filter works (Draft, InProgress, Finalized, Deleted)
- [ ] Date range filter works
- [ ] Table displays: ID, Patient, Doctor, Created Date, State, Section Statuses
- [ ] Section status indicators show (Pending/Approved/Rejected)
- [ ] Clicking row navigates to detail page
- [ ] Pagination works (limit/offset)
- [ ] Responsive on mobile (horizontal scroll)

#### Prescription Detail Page

- [ ] Patient info displayed
- [ ] Audio files playable
- [ ] Transcription text displayed
- [ ] Sections displayed (read-only for Finalized)
- [ ] Download PDF button works
- [ ] Delete button shows confirmation modal
- [ ] Restore button visible for deleted prescriptions (creator or DeveloperAdmin)
- [ ] Permissions enforced (can_edit, can_delete, can_restore)

#### Prescription Finalization Page

- [ ] Auto-transitions to InProgress on load
- [ ] Bedrock-generated sections displayed
- [ ] Approve/Reject buttons per section
- [ ] Rejected sections show inline editor
- [ ] Section status indicators update
- [ ] Finalize button disabled until all required sections approved
- [ ] Finalize button enabled when ready
- [ ] Redirects to /thank-you after finalization

#### Thank You Page

- [ ] Random success message displayed
- [ ] "Back to Prescriptions" button works
- [ ] Consistent styling with app theme

#### Profile Page

- [ ] User name displayed
- [ ] Email displayed
- [ ] Role displayed (formatted: "Developer Admin" not "DeveloperAdmin")
- [ ] Specialty displayed (if doctor)
- [ ] Hospital name displayed
- [ ] Signature image displayed (if available)
- [ ] All fields read-only

#### Hospital Settings Page

- [ ] Hospital info editable (name, address, phone, email, etc.)
- [ ] Save button updates hospital
- [ ] Doctors list displayed
- [ ] Add doctor button works
- [ ] Remove doctor button works
- [ ] Only accessible to HospitalAdmin (own hospital) or DeveloperAdmin

#### CloudWatch Logs Viewer

- [ ] Date range selector works (default 24 hours)
- [ ] Search filter works
- [ ] Logs table displays timestamp and message
- [ ] Log levels highlighted (ERROR in red, WARN in yellow, INFO in blue)
- [ ] Load More pagination works
- [ ] Auto-refresh toggle works (30s interval)
- [ ] Only accessible to DeveloperAdmin

### ✅ Role-Based Access Control Testing

#### Doctor Role

- [ ] Can create prescriptions
- [ ] Can view own prescriptions only
- [ ] Can finalize own prescriptions
- [ ] Can delete own prescriptions
- [ ] Can restore own prescriptions
- [ ] Cannot view other doctors' prescriptions
- [ ] Cannot access hospital settings
- [ ] Cannot access CloudWatch logs

#### HospitalAdmin Role

- [ ] Can view all prescriptions in own hospital
- [ ] Cannot finalize prescriptions (creator only)
- [ ] Cannot delete prescriptions (creator only)
- [ ] Can access hospital settings for own hospital
- [ ] Cannot access other hospitals' settings
- [ ] Cannot access CloudWatch logs

#### DeveloperAdmin Role

- [ ] Can view all prescriptions (all hospitals)
- [ ] Can restore any deleted prescription
- [ ] Can access all hospital settings
- [ ] Can access CloudWatch logs viewer
- [ ] Cannot finalize prescriptions (creator only)
- [ ] Cannot delete prescriptions (creator only)

### ✅ Complete Workflow Testing

#### Workflow 1: Create and Finalize Prescription

1. Login as doctor
2. Create new prescription (Draft state)
3. Navigate to finalization page
4. Verify auto-transition to InProgress
5. Verify Bedrock sections populated
6. Approve all required sections
7. Verify Finalize button enabled
8. Click Finalize
9. Verify redirect to thank-you page
10. Verify prescription state is Finalized
11. Generate PDF
12. Verify PDF download works

#### Workflow 2: Section Rejection and Edit

1. Create prescription and transition to InProgress
2. Reject a section
3. Verify inline editor appears
4. Edit section content
5. Save changes
6. Verify status reset to Pending
7. Approve section
8. Finalize prescription

#### Workflow 3: Soft Delete and Restore

1. Create and finalize prescription
2. Delete prescription
3. Verify state is Deleted
4. Verify restore_deadline is 30 days from now
5. Restore prescription
6. Verify state restored to previous state (Finalized)
7. Verify deleted_at cleared

#### Workflow 4: Role-Based Access

1. Login as Doctor
2. Create prescription
3. Logout
4. Login as different Doctor
5. Verify cannot see first doctor's prescription
6. Login as HospitalAdmin (same hospital)
7. Verify can see both doctors' prescriptions
8. Verify cannot finalize or delete
9. Login as DeveloperAdmin
10. Verify can see all prescriptions
11. Verify can restore deleted prescriptions

### ✅ Performance Testing

- [ ] Prescriptions list loads in < 500ms (50 items)
- [ ] Single prescription detail loads in < 300ms
- [ ] PDF generation completes in < 5 seconds
- [ ] Bedrock extraction completes in < 10 seconds
- [ ] Search with filters returns in < 1 second
- [ ] CloudWatch logs query returns in < 2 seconds

### ✅ Error Handling Testing

- [ ] Invalid state transition returns error
- [ ] Unauthorized access returns 403
- [ ] Missing required fields returns 400
- [ ] PDF generation failure doesn't block finalization
- [ ] S3 upload retries on failure (3 attempts)
- [ ] Database transaction rollback on error
- [ ] Consistent error response format

### ✅ Backward Compatibility Testing

- [ ] Existing prescriptions migrated successfully
- [ ] Old prescriptions have state set to Draft
- [ ] Old prescriptions have sections as empty array
- [ ] Old prescriptions still viewable
- [ ] No data loss during migration

## Validation Criteria

### Must Pass (Blocking Issues)

- ✅ All database migrations execute successfully
- ✅ No data loss during migration
- ✅ All API endpoints return correct responses
- ✅ Role-based access control enforced
- ✅ Prescription workflow (Draft → InProgress → Finalized) works
- ✅ PDF generation works
- ✅ Soft delete and restore works

### Should Pass (Non-Blocking)

- ⚠️ All frontend pages render correctly
- ⚠️ Sidebar navigation works on all pages
- ⚠️ Transition overlay animates smoothly
- ⚠️ CloudWatch logs viewer works
- ⚠️ Hospital settings page works

### Nice to Have (Optional)

- 💡 Property-based tests pass
- 💡 Performance targets met
- 💡 Cleanup scheduler runs successfully

## Test Execution

### Run All Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# End-to-end tests
pytest tests/e2e/

# Property-based tests (optional)
pytest tests/property/
```

### Manual Testing

1. Follow each workflow in the checklist
2. Test with different user roles
3. Test on different devices (desktop, mobile)
4. Test error scenarios
5. Verify all UI elements work

## Issue Reporting

If issues found:

1. Document the issue:
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Screenshots/logs
   - User role and environment

2. Classify severity:
   - **Critical**: Blocks deployment (data loss, security issue)
   - **High**: Major functionality broken
   - **Medium**: Minor functionality issue
   - **Low**: UI/UX improvement

3. Report in issue tracker with label: `prescription-enhancement`

## Sign-Off Checklist

Before marking as complete:

- [ ] All "Must Pass" criteria met
- [ ] At least 90% of "Should Pass" criteria met
- [ ] No critical or high severity issues
- [ ] Documentation complete
- [ ] Deployment guide reviewed
- [ ] Rollback plan documented
- [ ] Monitoring configured
- [ ] Team trained on new features

## Conclusion

Once all validation criteria are met and sign-off checklist complete, the prescription enhancement feature is ready for production deployment.

**Tested by:** _________________  
**Date:** _________________  
**Sign-off:** _________________
