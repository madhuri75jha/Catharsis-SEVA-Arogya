"""Database Manager for PostgreSQL RDS"""
import logging
import time
from typing import Optional, Dict, Any, List
import psycopg2
from psycopg2 import pool, OperationalError, DatabaseError
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages PostgreSQL database connections with pooling and retry logic"""
    
    def __init__(self, db_config: Dict[str, Any]):
        """
        Initialize database manager with connection pooling
        
        Args:
            db_config: Database configuration (can be dict with connection params or database_url)
        """
        self.db_config = db_config
        self.connection_pool = None
        
        try:
            # Parse database URL if provided
            if 'database_url' in db_config:
                self._init_from_url(db_config['database_url'])
            else:
                self._init_from_params(db_config)
                
            logger.info("Database connection pool initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {str(e)}")
            raise
    
    def _init_from_url(self, database_url: str):
        """Initialize connection pool from database URL"""
        self.connection_pool = pool.SimpleConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=database_url,
            connect_timeout=5,
            options='-c statement_timeout=5000'
        )
    
    def _init_from_params(self, db_config: Dict[str, Any]):
        """Initialize connection pool from connection parameters"""
        self.connection_pool = pool.SimpleConnectionPool(
            minconn=2,
            maxconn=10,
            host=db_config.get('host', 'localhost'),
            port=db_config.get('port', 5432),
            database=db_config.get('database', 'seva_arogya'),
            user=db_config.get('username', 'postgres'),
            password=db_config.get('password', ''),
            connect_timeout=5,
            options='-c statement_timeout=5000'
        )
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections
        
        Yields:
            Database connection from pool
        """
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def execute_with_retry(self, query: str, params: tuple = None, max_retries: int = 3) -> Optional[List]:
        """
        Execute query with exponential backoff retry logic
        
        Args:
            query: SQL query to execute
            params: Query parameters
            max_retries: Maximum number of retry attempts
            
        Returns:
            Query results or None
        """
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(query, params)
                        
                        normalized = query.strip().upper()

                        # Commit if it's a write operation or DDL
                        if normalized.startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'TRUNCATE')):
                            conn.commit()
                            return None
                        
                        # Fetch results for SELECT queries
                        if normalized.startswith('SELECT'):
                            return cursor.fetchall()
                        return None
                        
            except (OperationalError, DatabaseError) as e:
                retry_count += 1
                last_error = e
                
                if retry_count < max_retries:
                    # Exponential backoff: 0.5s, 1s, 2s
                    wait_time = 0.5 * (2 ** (retry_count - 1))
                    logger.warning(f"Database query failed (attempt {retry_count}/{max_retries}), retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Database query failed after {max_retries} attempts: {str(e)}")
                    raise last_error
            
            except Exception as e:
                logger.error(f"Unexpected database error: {str(e)}")
                raise
        
        return None
    
    def health_check(self) -> bool:
        """
        Check database connection health
        
        Returns:
            True if database is accessible, False otherwise
        """
        try:
            result = self.execute_with_retry("SELECT 1", max_retries=1)
            return result is not None
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False
    
    def close_all_connections(self):
        """Close all connections in the pool gracefully"""
        if self.connection_pool:
            try:
                self.connection_pool.closeall()
                logger.info("All database connections closed successfully")
            except Exception as e:
                logger.error(f"Error closing database connections: {str(e)}")

    # Streaming transcription methods
    
    def create_streaming_transcription(self, user_id: str, session_id: str, 
                                       sample_rate: int, quality: str) -> Optional[str]:
        """
        Create streaming transcription record
        
        Args:
            user_id: User ID
            session_id: Session identifier
            sample_rate: Audio sample rate
            quality: Quality setting
            
        Returns:
            Transcription ID if successful, None otherwise
        """
        query = """
        INSERT INTO transcriptions 
        (user_id, audio_s3_key, job_id, status, session_id, streaming_job_id, 
         is_streaming, sample_rate, quality, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        RETURNING transcription_id
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (
                        user_id,
                        'pending',  # Will be updated on session end
                        session_id,  # Use session_id as job_id
                        'IN_PROGRESS',
                        session_id,
                        session_id,
                        True,
                        sample_rate,
                        quality
                    ))
                    conn.commit()
                    result = cursor.fetchone()
                    if result:
                        transcription_id = str(result[0])
                        logger.info(f"Streaming transcription created: {transcription_id}")
                        return transcription_id
        except Exception as e:
            logger.error(f"Failed to create streaming transcription: {str(e)}")
            return None
    
    def update_transcription_status(self, session_id: str, status: str, 
                                   audio_s3_key: Optional[str] = None,
                                   audio_duration: Optional[float] = None) -> bool:
        """
        Update transcription status and metadata
        
        Args:
            session_id: Session identifier
            status: New status ('COMPLETED', 'FAILED', etc.)
            audio_s3_key: S3 key for audio file (optional)
            audio_duration: Audio duration in seconds (optional)
            
        Returns:
            True if successful, False otherwise
        """
        # Build dynamic query based on provided parameters
        updates = ["status = %s", "updated_at = CURRENT_TIMESTAMP"]
        params = [status]
        
        if audio_s3_key:
            updates.append("audio_s3_key = %s")
            params.append(audio_s3_key)
        
        if audio_duration is not None:
            updates.append("audio_duration_seconds = %s")
            params.append(audio_duration)
        
        params.append(session_id)
        
        query = f"""
        UPDATE transcriptions
        SET {', '.join(updates)}
        WHERE session_id = %s
        """
        
        try:
            self.execute_with_retry(query, tuple(params))
            logger.info(f"Transcription status updated: session={session_id}, status={status}")
            return True
        except Exception as e:
            logger.error(f"Failed to update transcription status: {str(e)}")
            return False
    
    def append_transcript_text(self, session_id: str, text: str) -> bool:
        """
        Append text to transcript
        
        Args:
            session_id: Session identifier
            text: Text to append
            
        Returns:
            True if successful, False otherwise
        """
        query = """
        UPDATE transcriptions
        SET transcript_text = COALESCE(transcript_text, '') || %s || ' ',
            updated_at = CURRENT_TIMESTAMP
        WHERE session_id = %s
        """
        
        try:
            self.execute_with_retry(query, (text, session_id))
            return True
        except Exception as e:
            logger.error(f"Failed to append transcript text: {str(e)}")
            return False
    
    def get_transcription_by_session_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get transcription by session ID
        
        Args:
            session_id: Session identifier
            
        Returns:
            Transcription data as dictionary or None
        """
        query = """
        SELECT transcription_id, user_id, audio_s3_key, job_id, transcript_text, 
               status, session_id, streaming_job_id, is_streaming, 
               audio_duration_seconds, sample_rate, quality, created_at, updated_at
        FROM transcriptions
        WHERE session_id = %s
        """
        
        try:
            result = self.execute_with_retry(query, (session_id,))
            if result and len(result) > 0:
                row = result[0]
                return {
                    'transcription_id': str(row[0]),
                    'user_id': row[1],
                    'audio_s3_key': row[2],
                    'job_id': row[3],
                    'transcript_text': row[4],
                    'status': row[5],
                    'session_id': row[6],
                    'streaming_job_id': row[7],
                    'is_streaming': row[8],
                    'audio_duration_seconds': row[9],
                    'sample_rate': row[10],
                    'quality': row[11],
                    'created_at': row[12],
                    'updated_at': row[13]
                }
        except Exception as e:
            logger.error(f"Failed to get transcription by session ID: {str(e)}")
            return None
