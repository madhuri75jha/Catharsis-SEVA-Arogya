"""Debug script to test consultation API and database"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Import database manager
from aws_services.database_manager import DatabaseManager
from services.consultation_service import ConsultationService

def test_database_connection():
    """Test if we can connect to the database"""
    print("Testing database connection...")
    try:
        from aws_services.config_manager import ConfigManager
        config_manager = ConfigManager()
        db_credentials = config_manager.get_database_credentials()
        
        if not db_credentials:
            print("✗ No database credentials found")
            return None
            
        db_manager = DatabaseManager(db_credentials)
        result = db_manager.execute_with_retry("SELECT 1", ())
        print("✓ Database connection successful")
        return db_manager
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_transcriptions(db_manager):
    """Check if there are any transcriptions in the database"""
    print("\nChecking transcriptions table...")
    try:
        query = "SELECT COUNT(*) FROM transcriptions"
        result = db_manager.execute_with_retry(query, ())
        count = result[0][0] if result else 0
        print(f"Total transcriptions: {count}")
        
        if count > 0:
            # Get sample transcriptions
            query = """
            SELECT transcription_id, user_id, status, created_at 
            FROM transcriptions 
            ORDER BY created_at DESC 
            LIMIT 5
            """
            results = db_manager.execute_with_retry(query, ())
            print("\nRecent transcriptions:")
            for row in results:
                print(f"  ID: {row[0]}, User: {row[1]}, Status: {row[2]}, Created: {row[3]}")
        
        return count
    except Exception as e:
        print(f"✗ Failed to check transcriptions: {e}")
        return 0

def check_prescriptions(db_manager):
    """Check if there are any prescriptions in the database"""
    print("\nChecking prescriptions table...")
    try:
        query = "SELECT COUNT(*) FROM prescriptions"
        result = db_manager.execute_with_retry(query, ())
        count = result[0][0] if result else 0
        print(f"Total prescriptions: {count}")
        
        if count > 0:
            # Get sample prescriptions
            query = """
            SELECT prescription_id, user_id, patient_name, created_at 
            FROM prescriptions 
            ORDER BY created_at DESC 
            LIMIT 5
            """
            results = db_manager.execute_with_retry(query, ())
            print("\nRecent prescriptions:")
            for row in results:
                print(f"  ID: {row[0]}, User: {row[1]}, Patient: {row[2]}, Created: {row[3]}")
        
        return count
    except Exception as e:
        print(f"✗ Failed to check prescriptions: {e}")
        return 0

def test_consultation_service(db_manager, user_id=None):
    """Test the ConsultationService"""
    print("\nTesting ConsultationService...")
    
    # If no user_id provided, get one from the database
    if not user_id:
        try:
            query = "SELECT DISTINCT user_id FROM transcriptions LIMIT 1"
            result = db_manager.execute_with_retry(query, ())
            if result:
                user_id = result[0][0]
                print(f"Using user_id: {user_id}")
            else:
                print("✗ No transcriptions found, cannot test service")
                return
        except Exception as e:
            print(f"✗ Failed to get user_id: {e}")
            return
    
    try:
        consultations = ConsultationService.get_recent_consultations(
            user_id=user_id,
            db_manager=db_manager,
            limit=10
        )
        print(f"✓ Retrieved {len(consultations)} consultations")
        
        if consultations:
            print("\nSample consultation:")
            import json
            print(json.dumps(consultations[0], indent=2, default=str))
        else:
            print("No consultations found for this user")
            
    except Exception as e:
        print(f"✗ ConsultationService failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 60)
    print("CONSULTATION FEATURE DEBUG SCRIPT")
    print("=" * 60)
    
    db_manager = test_database_connection()
    if not db_manager:
        sys.exit(1)
    
    trans_count = check_transcriptions(db_manager)
    presc_count = check_prescriptions(db_manager)
    
    if trans_count > 0:
        test_consultation_service(db_manager)
    else:
        print("\n⚠ No transcriptions in database. Create some consultations first!")
    
    print("\n" + "=" * 60)
    print("DEBUG COMPLETE")
    print("=" * 60)
