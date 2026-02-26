@echo off
REM SEVA Arogya - Flask Application Runner (Windows)

echo Starting SEVA Arogya Flask Application...
echo ==========================================

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Run the application
echo Starting Flask server...
echo Access the application at: http://localhost:5000
python app.py

pause
