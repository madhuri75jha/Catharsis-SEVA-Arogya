#!/usr/bin/env python3
"""
Database Migration Execution Script

This script executes SQL migration files in order and provides rollback capability.
"""

import os
import sys
import logging
import psycopg2
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aws_services.database_manager import DatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationRunner:
    """Handles database migration execution and rollback"""
    
    def __init__(self, database_manager):
        self.db_manager = database_manager
        self.migrations_dir = Path(__file__).parent.parent / 'migrations'
        
    def create_migrations_table(self):
        """Create migrations tracking table if it doesn't exist"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    migration_id SERIAL PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL UNIQUE,
                    executed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN NOT NULL DEFAULT TRUE,
                    error_message TEXT
                )
            """)
            conn.commit()
            logger.info("Migrations tracking table ready")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create migrations table: {str(e)}")
            raise
        finally:
            cursor.close()
    
    def get_executed_migrations(self):
        """Get list of already executed migrations"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT filename FROM schema_migrations 
                WHERE success = TRUE 
                ORDER BY migration_id
            """)
            return [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()
    
    def get_migration_files(self):
        """Get sorted list of migration SQL files"""
        if not self.migrations_dir.exists():
            logger.error(f"Migrations directory not found: {self.migrations_dir}")
            return []
        
        migration_files = sorted([
            f for f in self.migrations_dir.glob('*.sql')
            if f.is_file()
        ])
        
        return migration_files
    
    def execute_migration(self, migration_file):
        """Execute a single migration file"""
        logger.info(f"Executing migration: {migration_file.name}")
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # Read migration SQL
            with open(migration_file, 'r') as f:
                sql = f.read()
            
            # Execute migration
            cursor.execute(sql)
            
            # Record successful migration
            cursor.execute("""
                INSERT INTO schema_migrations (filename, executed_at, success)
                VALUES (%s, %s, TRUE)
            """, (migration_file.name, datetime.now()))
            
            conn.commit()
            logger.info(f"✓ Migration {migration_file.name} executed successfully")
            return True
            
        except Exception as e:
            conn.rollback()
            error_msg = str(e)
            logger.error(f"✗ Migration {migration_file.name} failed: {error_msg}")
            
            # Record failed migration
            try:
                cursor.execute("""
                    INSERT INTO schema_migrations (filename, executed_at, success, error_message)
                    VALUES (%s, %s, FALSE, %s)
                """, (migration_file.name, datetime.now(), error_msg))
                conn.commit()
            except:
                pass
            
            return False
        finally:
            cursor.close()
    
    def run_migrations(self):
        """Run all pending migrations"""
        logger.info("Starting database migrations...")
        
        # Create migrations tracking table
        self.create_migrations_table()
        
        # Get executed migrations
        executed = set(self.get_executed_migrations())
        logger.info(f"Already executed: {len(executed)} migrations")
        
        # Get all migration files
        migration_files = self.get_migration_files()
        logger.info(f"Found {len(migration_files)} migration files")
        
        # Execute pending migrations
        pending = [f for f in migration_files if f.name not in executed]
        
        if not pending:
            logger.info("No pending migrations")
            return True
        
        logger.info(f"Pending migrations: {len(pending)}")
        
        success_count = 0
        for migration_file in pending:
            if self.execute_migration(migration_file):
                success_count += 1
            else:
                logger.error(f"Migration failed, stopping execution")
                return False
        
        logger.info(f"✓ Successfully executed {success_count} migrations")
        return True
    
    def rollback_migration(self, migration_name):
        """Rollback a specific migration (manual process)"""
        logger.warning(f"Rollback requested for: {migration_name}")
        logger.warning("Automatic rollback not implemented - manual intervention required")
        logger.warning("Please review the migration file and manually revert changes")
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # Mark migration as rolled back
            cursor.execute("""
                UPDATE schema_migrations 
                SET success = FALSE, 
                    error_message = 'Manually rolled back'
                WHERE filename = %s
            """, (migration_name,))
            conn.commit()
            logger.info(f"Marked {migration_name} as rolled back in tracking table")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to mark rollback: {str(e)}")
        finally:
            cursor.close()


def main():
    """Main entry point"""
    try:
        # Initialize database manager
        logger.info("Initializing database connection...")
        db_manager = DatabaseManager()
        
        # Create migration runner
        runner = MigrationRunner(db_manager)
        
        # Run migrations
        success = runner.run_migrations()
        
        if success:
            logger.info("✓ All migrations completed successfully")
            sys.exit(0)
        else:
            logger.error("✗ Migration execution failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Migration script failed: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
