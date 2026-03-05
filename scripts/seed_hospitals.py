"""
Seed data script for hospitals, doctors, and user roles

This script inserts sample hospital, doctor, and user role records
for development and testing purposes.
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aws_services.config_manager import ConfigManager
from aws_services.database_manager import DatabaseManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def seed_hospitals(db_manager):
    """Insert sample hospital records"""
    logger.info("Seeding hospitals...")
    
    hospitals = [
        {
            'hospital_id': 'hosp_12345',
            'name': 'SEVA Arogya Medical Center',
            'address': '123 Health Street, Bangalore, Karnataka 560001',
            'phone': '+91-80-12345678',
            'email': 'contact@sevaarogya.com',
            'registration_number': 'KA-BLR-2020-001',
            'website': 'https://sevaarogya.com',
            'logo_url': 'https://sevaarogya.com/logo.png'
        },
        {
            'hospital_id': 'hosp_67890',
            'name': 'City General Hospital',
            'address': '456 Medical Avenue, Mumbai, Maharashtra 400001',
            'phone': '+91-22-98765432',
            'email': 'info@citygeneral.com',
            'registration_number': 'MH-MUM-2019-002',
            'website': 'https://citygeneral.com',
            'logo_url': 'https://citygeneral.com/logo.png'
        }
    ]
    
    for hospital in hospitals:
        query = """
        INSERT INTO hospitals (
            hospital_id, name, address, phone, email,
            registration_number, website, logo_url
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (hospital_id) DO UPDATE
        SET name = EXCLUDED.name,
            address = EXCLUDED.address,
            phone = EXCLUDED.phone,
            email = EXCLUDED.email,
            registration_number = EXCLUDED.registration_number,
            website = EXCLUDED.website,
            logo_url = EXCLUDED.logo_url,
            updated_at = CURRENT_TIMESTAMP
        """
        
        db_manager.execute_with_retry(query, (
            hospital['hospital_id'],
            hospital['name'],
            hospital['address'],
            hospital['phone'],
            hospital['email'],
            hospital['registration_number'],
            hospital['website'],
            hospital['logo_url']
        ))
        
        logger.info(f"Seeded hospital: {hospital['name']}")
    
    logger.info(f"Successfully seeded {len(hospitals)} hospitals")


def seed_doctors(db_manager):
    """Insert sample doctor records"""
    logger.info("Seeding doctors...")
    
    doctors = [
        {
            'doctor_id': 'doctor@sevaarogya.com',
            'hospital_id': 'hosp_12345',
            'name': 'Dr. Rajesh Kumar',
            'specialty': 'General Medicine',
            'signature_url': None,
            'availability': 'Mon-Fri 9AM-5PM'
        },
        {
            'doctor_id': 'dr.priya@sevaarogya.com',
            'hospital_id': 'hosp_12345',
            'name': 'Dr. Priya Sharma',
            'specialty': 'Pediatrics',
            'signature_url': None,
            'availability': 'Mon-Sat 10AM-6PM'
        },
        {
            'doctor_id': 'admin@citygeneral.com',
            'hospital_id': 'hosp_67890',
            'name': 'Dr. Amit Patel',
            'specialty': 'Cardiology',
            'signature_url': None,
            'availability': 'Mon-Fri 8AM-4PM'
        }
    ]
    
    for doctor in doctors:
        query = """
        INSERT INTO doctors (
            doctor_id, hospital_id, name, specialty, signature_url, availability
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (doctor_id) DO UPDATE
        SET hospital_id = EXCLUDED.hospital_id,
            name = EXCLUDED.name,
            specialty = EXCLUDED.specialty,
            signature_url = EXCLUDED.signature_url,
            availability = EXCLUDED.availability,
            updated_at = CURRENT_TIMESTAMP
        """
        
        db_manager.execute_with_retry(query, (
            doctor['doctor_id'],
            doctor['hospital_id'],
            doctor['name'],
            doctor['specialty'],
            doctor['signature_url'],
            doctor['availability']
        ))
        
        logger.info(f"Seeded doctor: {doctor['name']}")
    
    logger.info(f"Successfully seeded {len(doctors)} doctors")


def seed_user_roles(db_manager):
    """Insert sample user role records"""
    logger.info("Seeding user roles...")
    
    user_roles = [
        {
            'user_id': 'doctor@sevaarogya.com',
            'role': 'Doctor',
            'hospital_id': 'hosp_12345'
        },
        {
            'user_id': 'dr.priya@sevaarogya.com',
            'role': 'Doctor',
            'hospital_id': 'hosp_12345'
        },
        {
            'user_id': 'admin@sevaarogya.com',
            'role': 'HospitalAdmin',
            'hospital_id': 'hosp_12345'
        },
        {
            'user_id': 'admin@citygeneral.com',
            'role': 'HospitalAdmin',
            'hospital_id': 'hosp_67890'
        },
        {
            'user_id': 'dev@sevaarogya.com',
            'role': 'DeveloperAdmin',
            'hospital_id': None
        }
    ]
    
    for user_role in user_roles:
        query = """
        INSERT INTO user_roles (user_id, role, hospital_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE
        SET role = EXCLUDED.role,
            hospital_id = EXCLUDED.hospital_id,
            updated_at = CURRENT_TIMESTAMP
        """
        
        db_manager.execute_with_retry(query, (
            user_role['user_id'],
            user_role['role'],
            user_role['hospital_id']
        ))
        
        logger.info(f"Seeded user role: {user_role['user_id']} - {user_role['role']}")
    
    logger.info(f"Successfully seeded {len(user_roles)} user roles")


def main():
    """Main execution function"""
    try:
        logger.info("Starting seed data script...")
        
        # Initialize configuration manager
        config_manager = ConfigManager()
        
        # Get database credentials
        db_credentials = config_manager.get_database_credentials()
        if not db_credentials:
            logger.error("Failed to retrieve database credentials")
            sys.exit(1)
        
        # Initialize database manager
        db_manager = DatabaseManager(db_credentials)
        
        # Validate database connection
        if not db_manager.health_check():
            logger.error("Database health check failed")
            sys.exit(1)
        
        logger.info("Database connection validated")
        
        # Seed data
        seed_hospitals(db_manager)
        seed_doctors(db_manager)
        seed_user_roles(db_manager)
        
        logger.info("Seed data script completed successfully!")
        
    except Exception as e:
        logger.error(f"Seed data script failed: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        if 'db_manager' in locals():
            db_manager.close_all_connections()


if __name__ == '__main__':
    main()
