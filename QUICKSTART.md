# SEVA Arogya - Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Run the Application
```bash
python app.py
```

### Step 3: Open Your Browser
Navigate to: **http://localhost:5000**

---

## 🎯 What You'll See

### 1. Login Page
**Default Credentials:**
- Email: `doctor@hospital.com`
- Password: `password123`

Or use any of these:
- `admin@seva.com` / `admin123`
- `demo@demo.com` / `demo`
- Or enter any email/password (demo mode accepts all)

Click "Login" button and you'll be redirected to the home page

### 2. Home Page
- Click the large blue mic button
- You'll be taken to the transcription page

### 3. Transcription Page
- Watch the timer count up
- See sample transcription text
- Click "Stop and Review" button

### 4. Final Prescription Page
- Review the prescription details
- Click "Finalize & Print" to complete

---

## 🔧 Alternative Run Methods

### Using Run Scripts

**Windows:**
```bash
run.bat
```

**Unix/Linux/Mac:**
```bash
chmod +x run.sh
./run.sh
```

### With Virtual Environment

**Create and activate:**
```bash
# Create
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Unix/Linux/Mac)
source venv/bin/activate

# Install and run
pip install -r requirements.txt
python app.py
```

---

## 📱 Pages Available

| URL | Description |
|-----|-------------|
| http://localhost:5000/ | Redirects to login or home |
| http://localhost:5000/login | Login page |
| http://localhost:5000/home | Home page (requires login) |
| http://localhost:5000/transcription | Voice capture page |
| http://localhost:5000/final-prescription | Prescription review |

---

## ✅ Verify Setup

Run the verification script:
```bash
python test_setup.py
```

Expected: **17/17 checks passed**

---

## 🎨 Features Implemented

✅ Login with email/password  
✅ Password visibility toggle  
✅ Home page with mic button  
✅ Transcription with live timer  
✅ Smart suggestions carousel  
✅ Final prescription review  
✅ Professional prescription layout  
✅ Responsive mobile-first design  

---

## 🛠️ Troubleshooting

### Port Already in Use
If port 5000 is busy, edit `app.py` and change:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Use different port
```

### Flask Not Found
Install dependencies:
```bash
pip install -r requirements.txt
```

### Template Not Found
Make sure you're running from the project root directory where `app.py` is located.

---

## 📚 Documentation

- **FLASK_README.md** - Detailed Flask documentation
- **PROJECT_STRUCTURE.md** - File organization
- **IMPLEMENTATION_SUMMARY.md** - What's been built
- **requirements.md** - System requirements
- **design.md** - System design

---

## 🎯 Next Steps

1. ✅ Run the application
2. ✅ Test all 4 pages
3. ✅ Review the code structure
4. 🔜 Integrate AWS services
5. 🔜 Add real voice recording
6. 🔜 Implement PDF generation

---

## 💡 Tips

- The app auto-reloads when you edit files (debug mode)
- All API endpoints are placeholders for future AWS integration
- Session-based auth is temporary (will be replaced with AWS Cognito)
- UI matches the exact design from screen.png files

---

## 🆘 Need Help?

Check these files:
1. **FLASK_README.md** - Comprehensive guide
2. **PROJECT_STRUCTURE.md** - File organization
3. **IMPLEMENTATION_SUMMARY.md** - Feature list

---

**Ready to start? Run:** `python app.py`

**Then open:** http://localhost:5000

🎉 **Enjoy building with SEVA Arogya!**
