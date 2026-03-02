# Quick Start: Recent Consultations Feature

## Problem
You couldn't see consultations on the home page because:
1. Your database is on AWS RDS (not accessible locally)
2. The feature needs data to display

## Solution
I've added **mock data mode** for local development!

## How to Use (3 Steps)

### Step 1: Verify .env Configuration
Check that `.env` contains:
```
USE_MOCK_CONSULTATIONS=true
```
✅ This is already set in your .env file!

### Step 2: Restart Your Flask App
Stop and restart your Flask application to load the new configuration.

### Step 3: Test the Feature
1. Navigate to `http://localhost:5000/home` (or your app URL)
2. You should see **2 consultation cards** initially
3. Click **"View All"** to expand and see all 5 consultations
4. Click any consultation card to view full details

## What You'll See

### Home Page
- **2 consultation cards** showing:
  - Patient initials (avatar)
  - Patient name
  - Timestamp (e.g., "2 hours ago")
  - Status badge (Complete/In Progress)

- **"View All" button** to expand to 5 consultations

### Consultation Detail Page
When you click a card, you'll see:
- Patient name and consultation date
- Status badge
- Full transcript text
- Medical entities (grouped by category)
- Prescription medications (if available)
- Back button to return to home

## Mock Data Includes

5 sample consultations:
1. **Arjun Kumar** - Headache and fever (with prescription)
2. **Priya Sharma** - Diabetes follow-up (no prescription)
3. **Rajesh Patel** - Chest pain (with prescription, IN_PROGRESS)
4. **Sunita Reddy** - Blood pressure checkup (with prescription)
5. **Vikram Singh** - Back pain (no prescription)

## Debugging

### If you don't see consultations:

1. **Check browser console (F12)** for errors

2. **Verify the API endpoint works:**
   Open browser and go to:
   ```
   http://localhost:5000/api/consultations
   ```
   You should see JSON with 5 consultations

3. **Enable debug logging:**
   The template is already using `home_debug.js` which logs everything to console

4. **Check Flask logs** for any errors

### Common Issues

**Issue: Still see "Loading consultations..."**
- Check browser console for JavaScript errors
- Verify you're logged in (authentication required)
- Check Flask app is running

**Issue: "No recent consultations found"**
- Verify `USE_MOCK_CONSULTATIONS=true` in .env
- Restart Flask app
- Check Flask logs for errors

**Issue: View All button doesn't work**
- Open browser console (F12)
- Look for JavaScript errors
- Check that button has correct ID

## Switching to Real Data

When you deploy to AWS or have database access:

1. Change `.env`:
   ```
   USE_MOCK_CONSULTATIONS=false
   ```

2. Restart Flask app

3. Create real consultations using the transcription feature

4. They'll appear on the home page automatically!

## Files Modified

- ✅ `app.py` - Added mock data support to API endpoint and detail route
- ✅ `.env` - Added `USE_MOCK_CONSULTATIONS=true`
- ✅ `templates/home.html` - Using debug JavaScript
- ✅ `static/js/home_debug.js` - Created with console logging

## Next Steps

1. **Test the feature** with mock data
2. **Verify UI/UX** meets your requirements
3. **Deploy to AWS** when ready
4. **Switch to real data** by setting `USE_MOCK_CONSULTATIONS=false`

## Need Help?

Check these files for more details:
- `RECENT_CONSULTATIONS_SETUP.md` - Complete setup guide
- `INTEGRATION_VERIFICATION_SUMMARY.md` - Technical verification details

---

**Ready to test!** Just restart your Flask app and navigate to `/home` 🚀
