"""Prescription Database Model"""
from datetime import datetime
from typing import Optional, Dict, Any, List


class Prescription:
    """Prescription model for storing prescription data"""
    
    def __init__(self, user_id: str, patient_name: str, medications: List[Dict[str, Any]], 
                 s3_key: str, prescription_id: Optional[str] = None, created_at: Optional[datetime] = None):
        """
        Initialize Prescription model
        
        Args:
            user_id: ID of the healthcare provider who created the prescription
            patient_name: Name of the patient
            medications: List of medication dictionaries with name, dosage, frequency
            s3_key: S3 object key for the prescription PDF
            prescription_id: Unique prescription ID (auto-generated if None)
            created_at: Creation timestamp (auto-generated if None)
        """
        self.prescription_id = prescription_id
        self.user_id = user_id
        self.patient_name = patient_name
        self.medications = medications
        self.s3_key = s3_key
        self.created_at = created_at or datetime.utcnow()
    
    @staticmethod
    def create_table_sql() -> str:
        """Return SQL to create prescriptions table"""
        return """
        CREATE TABLE IF NOT EXISTS prescriptions (
            prescription_id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            patient_name VARCHAR(255) NOT NULL,
            medications JSONB NOT NULL,
            s3_key VARCHAR(512) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_prescriptions_user_id ON prescriptions(user_id);
        CREATE INDEX IF NOT EXISTS idx_prescriptions_created_at ON prescriptions(created_at);
        """
    
    def save(self, db_manager) -> Optional[str]:
        """
        Save prescription to database
        
        Args:
            db_manager: DatabaseManager instance
            
        Returns:
            Prescription ID if successful, None otherwise
        """
        import json
        
        query = """
        INSERT INTO prescriptions (user_id, patient_name, medications, s3_key, created_at)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING prescription_id
        """
        
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (
                        self.user_id,
                        self.patient_name,
                        json.dumps(self.medications),
                        self.s3_key,
                        self.created_at
                    ))
                    conn.commit()
                    result = cursor.fetchone()
                    if result:
                        self.prescription_id = str(result[0])
                        return self.prescription_id
        except Exception as e:
            import logging
            logging.error(f"Failed to save prescription: {str(e)}")
            return None
    
    @staticmethod
    def get_by_id(prescription_id: str, db_manager) -> Optional['Prescription']:
        """
        Retrieve prescription by ID
        
        Args:
            prescription_id: Prescription ID
            db_manager: DatabaseManager instance
            
        Returns:
            Prescription instance or None
        """
        import json
        
        query = """
        SELECT prescription_id, user_id, patient_name, medications, s3_key, created_at
        FROM prescriptions
        WHERE prescription_id = %s
        """
        
        try:
            result = db_manager.execute_with_retry(query, (prescription_id,))
            if result and len(result) > 0:
                row = result[0]
                return Prescription(
                    prescription_id=str(row[0]),
                    user_id=row[1],
                    patient_name=row[2],
                    medications=json.loads(row[3]) if isinstance(row[3], str) else row[3],
                    s3_key=row[4],
                    created_at=row[5]
                )
        except Exception as e:
            import logging
            logging.error(f"Failed to retrieve prescription: {str(e)}")
            return None
    
    @staticmethod
    def get_by_user(user_id: str, db_manager, limit: int = 50) -> List['Prescription']:
        """
        Retrieve prescriptions for a user
        
        Args:
            user_id: User ID
            db_manager: DatabaseManager instance
            limit: Maximum number of prescriptions to retrieve
            
        Returns:
            List of Prescription instances
        """
        import json
        
        query = """
        SELECT prescription_id, user_id, patient_name, medications, s3_key, created_at
        FROM prescriptions
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
        """
        
        try:
            results = db_manager.execute_with_retry(query, (user_id, limit))
            prescriptions = []
            if results:
                for row in results:
                    prescriptions.append(Prescription(
                        prescription_id=str(row[0]),
                        user_id=row[1],
                        patient_name=row[2],
                        medications=json.loads(row[3]) if isinstance(row[3], str) else row[3],
                        s3_key=row[4],
                        created_at=row[5]
                    ))
            return prescriptions
        except Exception as e:
            import logging
            logging.error(f"Failed to retrieve prescriptions for user: {str(e)}")
            return []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert prescription to dictionary"""
        return {
            'prescription_id': self.prescription_id,
            'user_id': self.user_id,
            'patient_name': self.patient_name,
            'medications': self.medications,
            's3_key': self.s3_key,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def update(self, db_manager) -> bool:
        """
        Update prescription in database
        
        Args:
            db_manager: DatabaseManager instance
            
        Returns:
            True if successful, False otherwise
        """
        import json
        
        query = """
        UPDATE prescriptions
        SET patient_name = %s, medications = %s, s3_key = %s
        WHERE prescription_id = %s
        """
        
        try:
            db_manager.execute_with_retry(query, (
                self.patient_name,
                json.dumps(self.medications),
                self.s3_key,
                self.prescription_id
            ))
            return True
        except Exception as e:
            import logging
            logging.error(f"Failed to update prescription: {str(e)}")
            return False
