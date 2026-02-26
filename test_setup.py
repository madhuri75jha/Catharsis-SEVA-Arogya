"""
SEVA Arogya - Setup Verification Script
Tests that all required files and dependencies are in place
"""

import os
import sys

def check_file(filepath, description):
    """Check if a file exists"""
    if os.path.exists(filepath):
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ {description}: {filepath} - NOT FOUND")
        return False

def check_directory(dirpath, description):
    """Check if a directory exists"""
    if os.path.isdir(dirpath):
        print(f"✓ {description}: {dirpath}")
        return True
    else:
        print(f"✗ {description}: {dirpath} - NOT FOUND")
        return False

def main():
    print("SEVA Arogya - Setup Verification")
    print("=" * 50)
    print()
    
    all_checks = []
    
    # Check core files
    print("Checking core application files...")
    all_checks.append(check_file("app.py", "Main application"))
    all_checks.append(check_file("requirements.txt", "Dependencies"))
    all_checks.append(check_file(".env.example", "Environment template"))
    print()
    
    # Check templates directory
    print("Checking templates directory...")
    all_checks.append(check_directory("templates", "Templates directory"))
    all_checks.append(check_file("templates/base.html", "Base template"))
    all_checks.append(check_file("templates/login.html", "Login page"))
    all_checks.append(check_file("templates/home.html", "Home page"))
    all_checks.append(check_file("templates/transcription.html", "Transcription page"))
    all_checks.append(check_file("templates/final_prescription.html", "Final prescription page"))
    print()
    
    # Check documentation
    print("Checking documentation files...")
    all_checks.append(check_file("FLASK_README.md", "Flask README"))
    all_checks.append(check_file("PROJECT_STRUCTURE.md", "Project structure"))
    all_checks.append(check_file("requirements.md", "Requirements doc"))
    all_checks.append(check_file("design.md", "Design doc"))
    print()
    
    # Check run scripts
    print("Checking run scripts...")
    all_checks.append(check_file("run.sh", "Unix run script"))
    all_checks.append(check_file("run.bat", "Windows run script"))
    print()
    
    # Check screens directory
    print("Checking screens directory...")
    all_checks.append(check_directory("screens", "Screens directory"))
    print()
    
    # Try importing Flask
    print("Checking Python dependencies...")
    try:
        import flask
        print(f"✓ Flask installed (version {flask.__version__})")
        all_checks.append(True)
    except ImportError:
        print("✗ Flask not installed - run: pip install -r requirements.txt")
        all_checks.append(False)
    print()
    
    # Summary
    print("=" * 50)
    passed = sum(all_checks)
    total = len(all_checks)
    print(f"Setup verification: {passed}/{total} checks passed")
    
    if passed == total:
        print("✓ All checks passed! You're ready to run the application.")
        print("\nTo start the application:")
        print("  - Unix/Linux/Mac: ./run.sh")
        print("  - Windows: run.bat")
        print("  - Or directly: python app.py")
        return 0
    else:
        print("✗ Some checks failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
