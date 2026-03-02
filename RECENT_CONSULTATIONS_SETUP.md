# Recent Consultations Feature - Setup Guide

## Overview
The recent consultations feature has been fully implemented and includes a **development mode** with mock data for local testing when the database is not accessible.

## What Was Implemented

### Backend Components
1. **ConsultationService** (`services/consultation_service.py`)
   - Retrieves consultations from database with LEFT JOIN
   - Extracts patient names from medical entities or prescriptions
   - Generates patient initials
   - Formats consultation objects for API response

2. **API Endpoint** (`/api/consultations`)
   - Authenticated endpoint returning JSON
   - Supports `limit` query parameter (default 10, max 50)
   - **Mock data mode** for local development
   - Error handling with user-friendly messages

3. **Consultation Detail Route** (`/consultation/<id>`)
   - Displays complete consultation information
   - Shows transcript, medical entities, and prescriptions
   - **Mock data mode** for local development
   - Handles missing data gracefully

### Frontend Components
1. **JavaScript Module** (`static/js/home.js` and `static/js/home_debug.js`)
   - Fetches consultations from API
   - Renders consultation cards dynamically
   - Formats relative timestamps
   - Handles expand/collapse functionality
   - Navigates to detail view

2. **Home Template** (`templates/home.html`)
   - Recent Consultations section
   - View All button
   - Empty state handling
   - Loading state

3. **Detail Template** (`templates/consultation_detail.html`)
   - Patient information header
   - Transcript section
   - Medical entities grouped by category
   - Prescription medications
   - Back navigation

## Development Mode (Mock Data)

### Why Mock Data?
Your database is hosted on AWS RDS and not accessible from your local machine. To enable local development and testing, mock data mode provides sample consultations.

### How to Enable Mock Data

1. **Set environment variable in `.env`:**
   ```
   USE_MOCK_CONSULTATIONS=true
   ```

2. **Restart your Flask application**

3. **Access the home page** - You should now see 5 mock consultations

### Mock Data Includes:
- 5 sample consultations with different patients
- Various statuses (COMPLETED, IN_PROGRESS)
- Medical entities and prescriptions
- Realistic timestamps

### Switching to Real Data

When running on AWS or with database access:

1. **Set environment variable in `.env`:**
   ```
   USE_MOCK_CONSULTATIONS=false
   ```

2. **Restart your Flask application**

3. **The app will now fetch real data from the database**

## Testing the Feature

### With Mock Data (Local Development)

1. **Start your Flask app:**
   ```bash
   python app.py
   ```

2. **Navigate to `/home` in your browser**

3. **You should see:**
   - 2 consultation cards initially
   - "View All" button (click to expand to 5 consultations)
   - Click any card to view details

4. **Open browser console (F12)** to see debug logs if using `home_debug.js`

### With Real Data (AWS/Production)

1. **Ensure `USE_MOCK_CONSULTATIONS=false` in `.env`**

2. **Ensure database is accessible**

3. **Create some consultations** by using the transcription feature

4. **Navigate to `/home`** to see your real consultations

## Debugging

### Enable Debug Logging

The `home_debug.js` file includes extensive console logging. To use it:

1. **Update `templates/home.html`:**
   ```html
   <script src="{{ url_for('static', filename='js/home_debug.js') }}"></script>
   ```

2. **Open browser console (F12)** to see:
   - API requests and responses
   - Consultation data
   - Rendering steps
   - Button clicks

### Common Issues

#### Issue: "Loading consultations..." never goes away
**Solution:** Check browser console for errors. Likely causes:
- API endpoint not responding
- Authentication failure
- JavaScript error

#### Issue: "No recent consultations found" appears
**Possible causes:**
- Mock data is disabled and database has no consultations
- Database connection failed
- User has no consultations

**Solution:**
- Enable mock data: `USE_MOCK_CONSULTATIONS=true`
- Or create consultations using the transcription feature

#### Issue: View All button doesn't work
**Solution:**
- Check browser console for JavaScript errors
- Verify `home.js` or `home_debug.js` is loaded
- Check that button has `id="view-all-btn"`

## File Structure

```
.
├── app.py                              # Flask routes with mock data support
├── services/
│   └── consultation_service.py         # Consultation data retrieval
├── static/js/
│   ├── home.js                         # Production JavaScript
│   └── home_debug.js                   # Debug version with console logs
├── templates/
│   ├── home.html                       # Home page template
│   └── consultation_detail.html        # Detail view template
├── tests/
│   ├── test_api_consultations.py       # API endpoint tests
│   └── test_consultation_integration.py # Integration tests
└── .env                                # Environment configuration
```

## Production Deployment

### Before Deploying to AWS:

1. **Disable mock data:**
   ```
   USE_MOCK_CONSULTATIONS=false
   ```

2. **Use production JavaScript:**
   In `templates/home.html`:
   ```html
   <script src="{{ url_for('static', filename='js/home.js') }}"></script>
   ```

3. **Ensure database credentials are in AWS Secrets Manager**

4. **Deploy and test with real data**

## Next Steps

1. **Test locally with mock data** to verify UI/UX
2. **Create real consultations** using the transcription feature
3. **Test with real data** on AWS
4. **Adjust styling** if needed
5. **Add pagination** if you have many consultations (future enhancement)

## Support

If you encounter issues:

1. Check browser console for JavaScript errors
2. Check Flask logs for backend errors
3. Verify `.env` configuration
4. Ensure mock data is enabled for local development
5. Test API endpoint directly: `curl http://localhost:5000/api/consultations`
