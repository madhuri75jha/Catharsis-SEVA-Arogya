"""Transcription Database Model"""
from datetime import datetime
from typing import Optional, Dict, Any, List


class Transcription:
    """Transcription model for storing audio transcription data"""
    
    def __init__(self, user_id: str, audio_s3_key: str, job_id: str,
                 transcription_id: Optional[str] = None, transcript_text: Optional[str] = None,
                 status: str = 'PENDING', medical_entities: Optional[List[Dict[str, Any]]] = None,
                 created_at: Optional[datetime] = None):
        """
        Initialize Transcription model
        
        Args:
            user_id: ID of the user who uploaded the audio
            audio_s3_key: S3 object key for the audio file
            job_id: AWS Transcribe job ID
            transcription_id: Unique transcription ID (auto-generated if None)
            transcript_text: Transcribed text (None until transcription completes)
            status: Transcription status (PENDING, IN_PROGRESS, COMPLETED, FAILED)
            medical_entities: Extracted medical entities from Comprehend Medical
            created_at: Creation timestamp (auto-generated if None)
        """
        self.transcription_id = transcription_id
        self.user_id = user_id
        self.audio_s3_key = audio_s3_key
        self.job_id = job_id
        self.transcript_text = transcript_text
        self.status = status
        self.medical_entities = medical_entities or []
        self.created_at = created_at or datetime.utcnow()
    
    @staticmethod
    def create_table_sql() -> str:
        """Return SQL to create transcriptions table"""
        return """
        CREATE TABLE IF NOT EXISTS transcriptions (
            transcription_id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            audio_s3_key VARCHAR(512) NOT NULL,
            job_id VARCHAR(255) NOT NULL UNIQUE,
            transcript_text TEXT,
            status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
            medical_entities JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_transcriptions_user_id ON transcriptions(user_id);
        CREATE INDEX IF NOT EXISTS idx_transcriptions_job_id ON transcriptions(job_id);
        CREATE INDEX IF NOT EXISTS idx_transcriptions_status ON transcriptions(status);
        """
    
    def save(self, db_manager) -> Optional[str]:
        """
        Save transcription to database
        
        Args:
            db_manager: DatabaseManager instance
            
        Returns:
            Transcription ID if successful, None otherwise
        """
        import json
        
        query = """
        INSERT INTO transcriptions (user_id, audio_s3_key, job_id, transcript_text, status, medical_entities, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING transcription_id
        """
        
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (
                        self.user_id,
                        self.audio_s3_key,
                        self.job_id,
                        self.transcript_text,
                        self.status,
                        json.dumps(self.medical_entities),
                        self.created_at
                    ))
                    conn.commit()
                    result = cursor.fetchone()
                    if result:
                        self.transcription_id = str(result[0])
                        return self.transcription_id
        except Exception as e:
            import logging
            logging.error(f"Failed to save transcription: {str(e)}")
            return None
    
    def update(self, db_manager) -> bool:
        """
        Update transcription in database
        
        Args:
            db_manager: DatabaseManager instance
            
        Returns:
            True if successful, False otherwise
        """
        import json
        
        query = """
        UPDATE transcriptions
        SET transcript_text = %s, status = %s, medical_entities = %s, updated_at = CURRENT_TIMESTAMP
        WHERE transcription_id = %s
        """
        
        try:
            db_manager.execute_with_retry(query, (
                self.transcript_text,
                self.status,
                json.dumps(self.medical_entities),
                self.transcription_id
            ))
            return True
        except Exception as e:
            import logging
            logging.error(f"Failed to update transcription: {str(e)}")
            return False
    
    @staticmethod
    def get_by_job_id(job_id: str, db_manager) -> Optional['Transcription']:
        """
        Retrieve transcription by job ID
        
        Args:
            job_id: AWS Transcribe job ID
            db_manager: DatabaseManager instance
            
        Returns:
            Transcription instance or None
        """
        import json
        
        query = """
        SELECT transcription_id, user_id, audio_s3_key, job_id, transcript_text, status, medical_entities, created_at
        FROM transcriptions
        WHERE job_id = %s
        """
        
        try:
            result = db_manager.execute_with_retry(query, (job_id,))
            if result and len(result) > 0:
                row = result[0]
                return Transcription(
                    transcription_id=str(row[0]),
                    user_id=row[1],
                    audio_s3_key=row[2],
                    job_id=row[3],
                    transcript_text=row[4],
                    status=row[5],
                    medical_entities=json.loads(row[6]) if row[6] and isinstance(row[6], str) else (row[6] or []),
                    created_at=row[7]
                )
        except Exception as e:
            import logging
            logging.error(f"Failed to retrieve transcription: {str(e)}")
            return None
    
    @staticmethod
    def get_by_user(user_id: str, db_manager, limit: int = 50) -> List['Transcription']:
        """
        Retrieve transcriptions for a user
        
        Args:
            user_id: User ID
            db_manager: DatabaseManager instance
            limit: Maximum number of transcriptions to retrieve
            
        Returns:
            List of Transcription instances
        """
        import json
        
        query = """
        SELECT transcription_id, user_id, audio_s3_key, job_id, transcript_text, status, medical_entities, created_at
        FROM transcriptions
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
        """
        
        try:
            results = db_manager.execute_with_retry(query, (user_id, limit))
            transcriptions = []
            if results:
                for row in results:
                    transcriptions.append(Transcription(
                        transcription_id=str(row[0]),
                        user_id=row[1],
                        audio_s3_key=row[2],
                        job_id=row[3],
                        transcript_text=row[4],
                        status=row[5],
                        medical_entities=json.loads(row[6]) if row[6] and isinstance(row[6], str) else (row[6] or []),
                        created_at=row[7]
                    ))
            return transcriptions
        except Exception as e:
            import logging
            logging.error(f"Failed to retrieve transcriptions for user: {str(e)}")
            return []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transcription to dictionary"""
        return {
            'transcription_id': self.transcription_id,
            'user_id': self.user_id,
            'audio_s3_key': self.audio_s3_key,
            'job_id': self.job_id,
            'transcript_text': self.transcript_text,
            'status': self.status,
            'medical_entities': self.medical_entities,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
