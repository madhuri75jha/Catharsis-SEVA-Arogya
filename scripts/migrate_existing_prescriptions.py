#!/usr/bin/env python3
"""
Migrate Existing Prescriptions Script

This script migrates existing prescriptions to the new schema with state management,
sections, and metadata fields.
"""

import os
import sys
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aws_services.database_manager import DatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def migrate_existing_prescriptions(db_manager):
    """
    Migrate existing prescriptions to new schema.
    
    Sets:
    - state to 'Draft' for all existing prescriptions
    - created_by_doctor_id from user_id (if available)
    - hospital_id from user's hospital (if available)
    - sections as empty array
    """
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        # Check if prescriptions table has the new columns
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'prescriptions' 
            AND column_name IN ('state', 'sections', 'created_by_doctor_id', 'hospital_id')
        """)
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        if not existing_columns:
            logger.error("New columns not found. Please run migrations first.")
            return False
        
        logger.info(f"Found new columns: {existing_columns}")
        
        # Get count of prescriptions to migrate
        cursor.execute("""
            SELECT COUNT(*) 
            FROM prescriptions 
            WHERE state IS NULL OR state = ''
        """)
        count = cursor.fetchone()[0]
        
        if count == 0:
            logger.info("No prescriptions to migrate")
            return True
        
        logger.info(f"Found {count} prescriptions to migrate")
        
        # Update prescriptions with default values
        cursor.execute("""
            UPDATE prescriptions
            SET 
                state = COALESCE(state, 'Draft'),
                sections = COALESCE(sections, '[]'::jsonb),
                created_by_doctor_id = COALESCE(created_by_doctor_id, user_id),
                updated_at = CURRENT_TIMESTAMP
            WHERE state IS NULL OR state = ''
        """)
        
        migrated_count = cursor.rowcount
        logger.info(f"Updated {migrated_count} prescriptions with default state and sections")
        
        # Try to set hospital_id from user_roles table if it exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'user_roles'
            )
        """)
        
        if cursor.fetchone()[0]:
            cursor.execute("""
                UPDATE prescriptions p
                SET hospital_id = ur.hospital_id
                FROM user_roles ur
                WHERE p.created_by_doctor_id = ur.user_id
                AND p.hospital_id IS NULL
                AND ur.hospital_id IS NOT NULL
            """)
            
            hospital_count = cursor.rowcount
            logger.info(f"Set hospital_id for {hospital_count} prescriptions from user_roles")
        
        conn.commit()
        logger.info("✓ Successfully migrated existing prescriptions")
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to migrate prescriptions: {str(e)}")
        return False
    finally:
        cursor.close()


def verify_migration(db_manager):
    """Verify migration was successful"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        # Check prescriptions with state
        cursor.execute("""
            SELECT state, COUNT(*) 
            FROM prescriptions 
            GROUP BY state
        """)
        
        logger.info("Prescription states after migration:")
        for row in cursor.fetchall():
            logger.info(f"  {row[0]}: {row[1]} prescriptions")
        
        # Check prescriptions with sections
        cursor.execute("""
            SELECT COUNT(*) 
            FROM prescriptions 
            WHERE sections IS NOT NULL
        """)
        
        sections_count = cursor.fetchone()[0]
        logger.info(f"Prescriptions with sections field: {sections_count}")
        
        # Check prescriptions with hospital_id
        cursor.execute("""
            SELECT COUNT(*) 
            FROM prescriptions 
            WHERE hospital_id IS NOT NULL
        """)
        
        hospital_count = cursor.fetchone()[0]
        logger.info(f"Prescriptions with hospital_id: {hospital_count}")
        
        return True
        
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")
        return False
    finally:
        cursor.close()


def main():
    """Main entry point"""
    try:
        logger.info("Starting prescription migration...")
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Migrate prescriptions
        if not migrate_existing_prescriptions(db_manager):
            logger.error("✗ Migration failed")
            sys.exit(1)
        
        # Verify migration
        if not verify_migration(db_manager):
            logger.warning("⚠ Verification had issues")
        
        logger.info("✓ Prescription migration completed successfully")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Migration script failed: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
