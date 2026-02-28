#!/usr/bin/env python3
"""
Database Migration Runner

This script runs SQL migration files against the database.
Usage: python migrations/run_migration.py <migration_file>
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import aws_services
sys.path.insert(0, str(Path(__file__).parent.parent))

from aws_services.database_manager import DatabaseManager
from aws_services.config_manager import ConfigManager
from utils.logger import get_logger

logger = get_logger(__name__)


def run_migration(migration_file: str) -> bool:
    """
    Run a SQL migration file
    
    Args:
        migration_file: Path to the SQL migration file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Initialize config and database manager
        config_manager = ConfigManager()
        db_manager = DatabaseManager(config_manager)
        
        # Read migration file
        migration_path = Path(migration_file)
        if not migration_path.exists():
            logger.error(f"Migration file not found: {migration_file}")
            return False
        
        logger.info(f"Running migration: {migration_path.name}")
        
        with open(migration_path, 'r') as f:
            sql = f.read()
        
        # Execute migration
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                conn.commit()
        
        logger.info(f"Migration completed successfully: {migration_path.name}")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python migrations/run_migration.py <migration_file>")
        print("\nExample:")
        print("  python migrations/run_migration.py migrations/001_add_streaming_columns.sql")
        sys.exit(1)
    
    migration_file = sys.argv[1]
    success = run_migration(migration_file)
    
    if success:
        print(f"✓ Migration completed: {migration_file}")
        sys.exit(0)
    else:
        print(f"✗ Migration failed: {migration_file}")
        sys.exit(1)


if __name__ == "__main__":
    main()
