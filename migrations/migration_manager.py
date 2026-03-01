"""
Migration Manager

Automatically runs database migrations on application startup.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages database schema migrations"""
    
    def __init__(self, database_manager, migrations_dir: str = 'migrations'):
        """
        Initialize migration manager
        
        Args:
            database_manager: DatabaseManager instance
            migrations_dir: Directory containing migration SQL files
        """
        self.db_manager = database_manager
        self.migrations_dir = Path(migrations_dir)
        
    def _ensure_migrations_table(self):
        """Create migrations tracking table if it doesn't exist"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id SERIAL PRIMARY KEY,
            migration_name VARCHAR(255) UNIQUE NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(create_table_sql)
                    conn.commit()
        except Exception as e:
            logger.error(f"Failed to create migrations table: {str(e)}")
            raise
    
    def _get_applied_migrations(self) -> List[str]:
        """Get list of already applied migrations"""
        query = "SELECT migration_name FROM schema_migrations ORDER BY migration_name"
        
        try:
            result = self.db_manager.execute_with_retry(query)
            return [row[0] for row in result] if result else []
        except Exception as e:
            logger.error(f"Failed to get applied migrations: {str(e)}")
            return []
    
    def _get_pending_migrations(self) -> List[Path]:
        """Get list of pending migration files"""
        # Get all .sql files in migrations directory
        all_migrations = sorted(self.migrations_dir.glob('*.sql'))
        
        # Filter out non-migration files
        migration_files = [
            f for f in all_migrations 
            if f.name.startswith(tuple('0123456789')) and not f.name.endswith('_rollback.sql')
        ]
        
        # Get already applied migrations
        applied = self._get_applied_migrations()
        
        # Return only pending migrations
        pending = [f for f in migration_files if f.name not in applied]
        
        return pending
    
    def _apply_migration(self, migration_file: Path) -> bool:
        """
        Apply a single migration file
        
        Args:
            migration_file: Path to migration SQL file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Applying migration: {migration_file.name}")
            
            # Read migration SQL
            with open(migration_file, 'r') as f:
                sql = f.read()
            
            # Execute migration
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Execute migration SQL
                    cursor.execute(sql)
                    
                    # Record migration as applied
                    cursor.execute(
                        "INSERT INTO schema_migrations (migration_name) VALUES (%s)",
                        (migration_file.name,)
                    )
                    
                    conn.commit()
            
            logger.info(f"Migration applied successfully: {migration_file.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply migration {migration_file.name}: {str(e)}")
            return False
    
    def run_migrations(self) -> bool:
        """
        Run all pending migrations
        
        Returns:
            True if all migrations successful, False otherwise
        """
        try:
            logger.info("Starting database migrations...")
            
            # Ensure migrations tracking table exists
            self._ensure_migrations_table()
            
            # Get pending migrations
            pending = self._get_pending_migrations()
            
            if not pending:
                logger.info("No pending migrations")
                return True
            
            logger.info(f"Found {len(pending)} pending migration(s)")
            
            # Apply each migration
            for migration_file in pending:
                success = self._apply_migration(migration_file)
                if not success:
                    logger.error(f"Migration failed: {migration_file.name}")
                    return False
            
            logger.info(f"All migrations completed successfully ({len(pending)} applied)")
            return True
            
        except Exception as e:
            logger.error(f"Migration process failed: {str(e)}")
            return False
    
    def get_migration_status(self) -> dict:
        """
        Get current migration status
        
        Returns:
            Dictionary with migration status information
        """
        try:
            self._ensure_migrations_table()
            
            applied = self._get_applied_migrations()
            pending = self._get_pending_migrations()
            
            return {
                'applied_count': len(applied),
                'pending_count': len(pending),
                'applied_migrations': applied,
                'pending_migrations': [f.name for f in pending],
                'status': 'up_to_date' if not pending else 'pending_migrations'
            }
        except Exception as e:
            logger.error(f"Failed to get migration status: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
