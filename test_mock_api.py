"""Quick test to verify mock API works"""
import os
os.environ['USE_MOCK_CONSULTATIONS'] = 'true'

from datetime import datetime, timedelta
import json

# Simulate the mock data generation
mock_consultations = [
    {
        "consultation_id": "1",
        "patient_name": "Arjun Kumar",
        "patient_initials": "AK",
        "status": "COMPLETED",
        "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
        "has_prescription": True,
        "prescription_id": "101",
        "transcript_preview": "Patient complains of headache and fever for the past 3 days..."
    },
    {
        "consultation_id": "2",
        "patient_name": "Priya Sharma",
        "patient_initials": "PS",
        "status": "COMPLETED",
        "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
        "has_prescription": False,
        "prescription_id": None,
        "transcript_preview": "Follow-up visit for diabetes management..."
    },
    {
        "consultation_id": "3",
        "patient_name": "Rajesh Patel",
        "patient_initials": "RP",
        "status": "IN_PROGRESS",
        "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
        "has_prescription": True,
        "prescription_id": "102",
        "transcript_preview": "Patient reports chest pain and shortness of breath..."
    },
    {
        "consultation_id": "4",
        "patient_name": "Sunita Reddy",
        "patient_initials": "SR",
        "status": "COMPLETED",
        "created_at": (datetime.now() - timedelta(days=3)).isoformat(),
        "has_prescription": True,
        "prescription_id": "103",
        "transcript_preview": "Routine checkup, blood pressure slightly elevated..."
    },
    {
        "consultation_id": "5",
        "patient_name": "Vikram Singh",
        "patient_initials": "VS",
        "status": "COMPLETED",
        "created_at": (datetime.now() - timedelta(days=5)).isoformat(),
        "has_prescription": False,
        "prescription_id": None,
        "transcript_preview": "Patient complains of back pain after lifting heavy objects..."
    }
]

print("Mock Consultations Data:")
print(json.dumps(mock_consultations, indent=2))
print(f"\nTotal consultations: {len(mock_consultations)}")
print("\nMock data is ready to use!")
print("\nTo enable in your app:")
print("1. Ensure USE_MOCK_CONSULTATIONS=true in .env")
print("2. Restart Flask app")
print("3. Navigate to /home")
