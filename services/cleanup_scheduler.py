"""Cleanup Scheduler Service for automated deletion of expired prescriptions"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logging.warning("APScheduler not installed. Cleanup scheduling will not be available.")

logger = logging.getLogger(__name__)


class CleanupScheduler:
    """Service for scheduling automated cleanup of deleted prescriptions"""
    
    def __init__(self, database_manager, storage_manager, retention_days: int = 30):
        """
        Initialize CleanupScheduler
        
        Args:
            database_manager: DatabaseManager instance
            storage_manager: StorageManager instance
            retention_days: Number of days to retain deleted prescriptions (default 30)
        """
        if not APSCHEDULER_AVAILABLE:
            raise ImportError("APScheduler is required for cleanup scheduling. Install with: pip install apscheduler")
        
        self.db = database_manager
        self.storage = storage_manager
        self.retention_days = retention_days
        self.scheduler = BackgroundScheduler()
        
        logger.info(f"CleanupScheduler initialized with {retention_days}-day retention")
    
    def start(self):
        """Start the cleanup scheduler (runs daily at 2 AM)"""
        try:
            # Schedule cleanup to run daily at 2 AM
            self.scheduler.add_job(
                self.run_cleanup,
                CronTrigger(hour=2, minute=0),
                id='prescription_cleanup',
                name='Daily Prescription Cleanup',
                replace_existing=True
            )
            
            self.scheduler.start()
            logger.info("Cleanup scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start cleanup scheduler: {str(e)}")
            raise
    
    def stop(self):
        """Stop the cleanup scheduler"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                logger.info("Cleanup scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping cleanup scheduler: {str(e)}")
    
    def run_cleanup(self) -> Dict[str, Any]:
        """
        Run cleanup of expired deleted prescriptions
        
        Returns:
            Dictionary with cleanup statistics
        """
        start_time = datetime.now()
        logger.info("Starting daily prescription cleanup")
        
        stats = {
            'start_time': start_time.isoformat(),
            'prescriptions_deleted': 0,
            'audio_files_deleted': 0,
            'pdf_files_deleted': 0,
            'errors': []
        }
        
        try:
            # Find expired prescriptions
            expired_prescriptions = self.find_expired_prescriptions()
            logger.info(f"Found {len(expired_prescriptions)} expired prescriptions")
            
            # Delete each prescription
            for prescription in expired_prescriptions:
                try:
                    success = self.permanently_delete_prescription(prescription)
                    if success:
                        stats['prescriptions_deleted'] += 1
                        
                        # Count deleted files
                        if prescription.get('s3_key'):
                            stats['pdf_files_deleted'] += 1
                        
                        # Count audio files (estimated from consultation)
                        if prescription.get('consultation_id'):
                            stats['audio_files_deleted'] += 1
                    
                except Exception as e:
                    error_msg = f"Failed to delete prescription {prescription.get('prescription_id')}: {str(e)}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            stats['end_time'] = end_time.isoformat()
            stats['duration_seconds'] = duration
            
            logger.info(f"Cleanup completed: {stats['prescriptions_deleted']} prescriptions deleted in {duration:.2f}s")
            
            return stats
            
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            stats['errors'].append(str(e))
            return stats
    
    def find_expired_prescriptions(self) -> List[Dict[str, Any]]:
        """
        Find prescriptions deleted more than retention_days ago
        
        Returns:
            List of expired prescription dictionaries
        """
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        query = """
        SELECT prescription_id, s3_key, consultation_id, patient_name, deleted_at
        FROM prescriptions
        WHERE state = 'Deleted' AND deleted_at < %s
        """
        
        try:
            results = self.db.execute_with_retry(query, (cutoff_date,))
            
            prescriptions = []
            if results:
                for row in results:
                    prescriptions.append({
                        'prescription_id': str(row[0]),
                        's3_key': row[1],
                        'consultation_id': row[2],
                        'patient_name': row[3],
                        'deleted_at': row[4]
                    })
            
            return prescriptions
            
        except Exception as e:
            logger.error(f"Failed to find expired prescriptions: {str(e)}")
            return []
    
    def permanently_delete_prescription(self, prescription: Dict[str, Any]) -> bool:
        """
        Permanently delete prescription and associated files
        
        Args:
            prescription: Prescription dictionary
            
        Returns:
            True if successful, False otherwise
        """
        prescription_id = prescription['prescription_id']
        
        try:
            # Delete S3 objects first
            s3_deleted = self.delete_s3_objects(prescription)
            
            # Delete database record
            query = "DELETE FROM prescriptions WHERE prescription_id = %s"
            self.db.execute_with_retry(query, (prescription_id,))
            
            logger.info(f"Permanently deleted prescription {prescription_id} (S3 cleanup: {s3_deleted})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to permanently delete prescription {prescription_id}: {str(e)}")
            return False
    
    def delete_s3_objects(self, prescription: Dict[str, Any]) -> bool:
        """
        Delete S3 objects associated with prescription
        
        Args:
            prescription: Prescription dictionary
            
        Returns:
            True if all deletions successful, False otherwise
        """
        all_success = True
        
        try:
            # Delete prescription PDF
            if prescription.get('s3_key'):
                try:
                    self.storage.delete_file(prescription['s3_key'])
                    logger.info(f"Deleted PDF: {prescription['s3_key']}")
                except Exception as e:
                    logger.warning(f"Failed to delete PDF {prescription['s3_key']}: {str(e)}")
                    all_success = False
            
            # Delete audio files from consultation
            consultation_id = prescription.get('consultation_id')
            if consultation_id:
                try:
                    audio_files = self._get_consultation_audio_files(consultation_id)
                    for audio_s3_key in audio_files:
                        try:
                            self.storage.delete_file(audio_s3_key)
                            logger.info(f"Deleted audio: {audio_s3_key}")
                        except Exception as e:
                            logger.warning(f"Failed to delete audio {audio_s3_key}: {str(e)}")
                            all_success = False
                except Exception as e:
                    logger.warning(f"Failed to get audio files for consultation {consultation_id}: {str(e)}")
                    all_success = False
            
            return all_success
            
        except Exception as e:
            logger.error(f"Error deleting S3 objects: {str(e)}")
            return False
    
    def _get_consultation_audio_files(self, consultation_id: str) -> List[str]:
        """
        Get audio file S3 keys for a consultation
        
        Args:
            consultation_id: Consultation ID
            
        Returns:
            List of S3 keys
        """
        query = """
        SELECT audio_s3_key
        FROM transcriptions
        WHERE consultation_id = %s AND audio_s3_key IS NOT NULL
        """
        
        try:
            results = self.db.execute_with_retry(query, (consultation_id,))
            
            if results:
                return [row[0] for row in results if row[0]]
            return []
            
        except Exception as e:
            logger.error(f"Failed to get audio files for consultation: {str(e)}")
            return []
    
    def run_cleanup_now(self) -> Dict[str, Any]:
        """
        Run cleanup immediately (for testing or manual trigger)
        
        Returns:
            Dictionary with cleanup statistics
        """
        logger.info("Running manual cleanup")
        return self.run_cleanup()
