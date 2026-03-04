"""
Consultation Session State Manager

Manages multi-clip consultation sessions for asynchronous push-to-talk transcription.
Tracks active consultation sessions, associates clips with consultation_id, maintains
clip ordering, and persists session state to database for recovery.

Requirements: 1.3, 7.1, 7.4
"""

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ClipMetadata:
    """Metadata for a single audio clip within a consultation"""
    clip_id: str
    clip_order: int
    job_id: str
    status: str  # 'recording', 'uploading', 'queued', 'transcribing', 'completed', 'failed'
    audio_s3_key: Optional[str] = None
    transcript_text: Optional[str] = None
    chunk_sequence: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None


@dataclass
class ConsultationSession:
    """State for a multi-clip consultation session"""
    consultation_id: str
    user_id: str
    status: str = 'IN_PROGRESS'  # 'IN_PROGRESS', 'COMPLETED'
    clips: Dict[str, ClipMetadata] = field(default_factory=dict)
    next_clip_order: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    
    def add_clip(self, clip_id: str, job_id: str) -> ClipMetadata:
        """
        Add a new clip to the consultation session
        
        Args:
            clip_id: Unique clip identifier
            job_id: Transcription job identifier
            
        Returns:
            ClipMetadata for the new clip
        """
        clip = ClipMetadata(
            clip_id=clip_id,
            clip_order=self.next_clip_order,
            job_id=job_id,
            status='recording'
        )
        self.clips[clip_id] = clip
        self.next_clip_order += 1
        self.last_activity = datetime.utcnow()
        return clip
    
    def get_clip(self, clip_id: str) -> Optional[ClipMetadata]:
        """Get clip metadata by clip_id"""
        return self.clips.get(clip_id)
    
    def update_clip_status(self, clip_id: str, status: str, 
                          audio_s3_key: Optional[str] = None,
                          transcript_text: Optional[str] = None,
                          error_message: Optional[str] = None) -> bool:
        """
        Update clip status and metadata
        
        Args:
            clip_id: Clip identifier
            status: New status
            audio_s3_key: S3 key for audio file (optional)
            transcript_text: Transcribed text (optional)
            error_message: Error message if failed (optional)
            
        Returns:
            True if clip was found and updated, False otherwise
        """
        clip = self.clips.get(clip_id)
        if not clip:
            return False
        
        clip.status = status
        clip.updated_at = datetime.utcnow()
        
        if audio_s3_key:
            clip.audio_s3_key = audio_s3_key
        if transcript_text:
            clip.transcript_text = transcript_text
        if error_message:
            clip.error_message = error_message
        
        self.last_activity = datetime.utcnow()
        return True
    
    def get_clips_ordered(self) -> List[ClipMetadata]:
        """Get all clips ordered by clip_order"""
        return sorted(self.clips.values(), key=lambda c: c.clip_order)
    
    def get_idle_seconds(self) -> float:
        """Get seconds since last activity"""
        return (datetime.utcnow() - self.last_activity).total_seconds()


class ConsultationSessionManager:
    """
    Manages active consultation sessions with multiple clips
    
    Features:
    - Thread-safe session registry
    - Clip ordering within consultations
    - Database persistence for recovery
    - Session lifecycle management
    """
    
    def __init__(self, database_manager, idle_timeout: int = 3600):
        """
        Initialize ConsultationSessionManager
        
        Args:
            database_manager: DatabaseManager instance for persistence
            idle_timeout: Idle timeout in seconds (default: 3600 = 1 hour)
        """
        self._sessions: Dict[str, ConsultationSession] = {}
        self._lock = threading.Lock()
        self._database_manager = database_manager
        self._idle_timeout = idle_timeout
        
        logger.info(f"ConsultationSessionManager initialized: idle_timeout={idle_timeout}s")
    
    def create_session(self, consultation_id: str, user_id: str) -> ConsultationSession:
        """
        Create a new consultation session
        
        Args:
            consultation_id: Unique consultation identifier
            user_id: User ID
            
        Returns:
            ConsultationSession instance
            
        Raises:
            RuntimeError: If session already exists
        """
        with self._lock:
            # Check if session already exists
            if consultation_id in self._sessions:
                logger.warning(f"Consultation session already exists: {consultation_id}")
                return self._sessions[consultation_id]
            
            # Create session
            session = ConsultationSession(
                consultation_id=consultation_id,
                user_id=user_id
            )
            
            self._sessions[consultation_id] = session
            
            # Persist to database
            self._persist_session(session)
            
            logger.info(f"Consultation session created: {consultation_id} (user={user_id}, "
                       f"active_sessions={len(self._sessions)})")
            
            return session
    
    def get_session(self, consultation_id: str) -> Optional[ConsultationSession]:
        """
        Retrieve session by consultation_id
        
        Args:
            consultation_id: Consultation identifier
            
        Returns:
            ConsultationSession instance or None if not found
        """
        with self._lock:
            session = self._sessions.get(consultation_id)
            if session:
                return session
            
            # Try to load from database
            return self._load_session_from_db(consultation_id)
    
    def add_clip(self, consultation_id: str, clip_id: str, job_id: str) -> Optional[ClipMetadata]:
        """
        Add a new clip to a consultation session
        
        Args:
            consultation_id: Consultation identifier
            clip_id: Unique clip identifier
            job_id: Transcription job identifier
            
        Returns:
            ClipMetadata if successful, None if session not found
        """
        with self._lock:
            session = self._sessions.get(consultation_id)
            if not session:
                logger.error(f"Cannot add clip: consultation session not found: {consultation_id}")
                return None
            
            clip = session.add_clip(clip_id, job_id)
            
            # Persist clip to database
            self._persist_clip(session, clip)
            
            logger.info(f"Clip added to consultation: consultation_id={consultation_id}, "
                       f"clip_id={clip_id}, clip_order={clip.clip_order}")
            
            return clip
    
    def update_clip_status(self, consultation_id: str, clip_id: str, status: str,
                          audio_s3_key: Optional[str] = None,
                          transcript_text: Optional[str] = None,
                          error_message: Optional[str] = None) -> bool:
        """
        Update clip status and metadata
        
        Args:
            consultation_id: Consultation identifier
            clip_id: Clip identifier
            status: New status
            audio_s3_key: S3 key for audio file (optional)
            transcript_text: Transcribed text (optional)
            error_message: Error message if failed (optional)
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            session = self._sessions.get(consultation_id)
            if not session:
                logger.error(f"Cannot update clip: consultation session not found: {consultation_id}")
                return False
            
            if not session.update_clip_status(clip_id, status, audio_s3_key, 
                                             transcript_text, error_message):
                logger.error(f"Cannot update clip: clip not found: {clip_id}")
                return False
            
            # Persist update to database
            clip = session.get_clip(clip_id)
            if clip:
                self._update_clip_in_db(session, clip)
            
            logger.info(f"Clip status updated: consultation_id={consultation_id}, "
                       f"clip_id={clip_id}, status={status}")
            
            return True
    
    def complete_session(self, consultation_id: str) -> bool:
        """
        Mark a consultation session as completed
        
        Args:
            consultation_id: Consultation identifier
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            session = self._sessions.get(consultation_id)
            if not session:
                logger.error(f"Cannot complete session: consultation not found: {consultation_id}")
                return False
            
            session.status = 'COMPLETED'
            session.last_activity = datetime.utcnow()
            
            # Update database
            self._update_session_status(consultation_id, 'COMPLETED')
            
            logger.info(f"Consultation session completed: {consultation_id}")
            
            return True
    
    def remove_session(self, consultation_id: str) -> Optional[ConsultationSession]:
        """
        Remove session from active sessions (does not delete from database)
        
        Args:
            consultation_id: Consultation identifier
            
        Returns:
            Removed ConsultationSession instance or None if not found
        """
        with self._lock:
            session = self._sessions.pop(consultation_id, None)
            if session:
                logger.info(f"Consultation session removed from active sessions: {consultation_id} "
                           f"(active_sessions={len(self._sessions)})")
            return session
    
    def get_clips_ordered(self, consultation_id: str) -> List[ClipMetadata]:
        """
        Get all clips for a consultation ordered by clip_order
        
        Args:
            consultation_id: Consultation identifier
            
        Returns:
            List of ClipMetadata ordered by clip_order
        """
        with self._lock:
            session = self._sessions.get(consultation_id)
            if not session:
                return []
            return session.get_clips_ordered()
    
    def cleanup_idle_sessions(self) -> int:
        """
        Remove sessions that have been idle beyond timeout
        
        Returns:
            Number of sessions cleaned up
        """
        with self._lock:
            idle_sessions = []
            
            for consultation_id, session in self._sessions.items():
                if session.get_idle_seconds() > self._idle_timeout:
                    idle_sessions.append(consultation_id)
            
            # Remove idle sessions
            for consultation_id in idle_sessions:
                session = self._sessions.pop(consultation_id)
                logger.info(f"Idle consultation session cleaned up: {consultation_id} "
                           f"(idle={session.get_idle_seconds():.1f}s)")
            
            if idle_sessions:
                logger.info(f"Cleaned up {len(idle_sessions)} idle consultation sessions "
                           f"(active_sessions={len(self._sessions)})")
            
            return len(idle_sessions)
    
    def get_active_count(self) -> int:
        """
        Get count of active consultation sessions
        
        Returns:
            Number of active sessions
        """
        with self._lock:
            return len(self._sessions)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get consultation session statistics
        
        Returns:
            Dictionary with statistics
        """
        with self._lock:
            total_clips = sum(len(s.clips) for s in self._sessions.values())
            in_progress = sum(1 for s in self._sessions.values() if s.status == 'IN_PROGRESS')
            completed = sum(1 for s in self._sessions.values() if s.status == 'COMPLETED')
            
            return {
                'active_sessions': len(self._sessions),
                'in_progress': in_progress,
                'completed': completed,
                'total_clips': total_clips
            }
    
    # Database persistence methods
    
    def _persist_session(self, session: ConsultationSession) -> bool:
        """
        Persist consultation session to database
        
        Args:
            session: ConsultationSession to persist
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = """
            INSERT INTO consultations (consultation_id, user_id, status, merged_transcript_text)
            VALUES (%s, %s, %s, '')
            ON CONFLICT (consultation_id) DO UPDATE
            SET status = EXCLUDED.status, updated_at = CURRENT_TIMESTAMP
            """
            self._database_manager.execute_with_retry(
                query,
                (session.consultation_id, session.user_id, session.status)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to persist consultation session: {str(e)}")
            return False
    
    def _persist_clip(self, session: ConsultationSession, clip: ClipMetadata) -> bool:
        """
        Persist clip to database
        
        Args:
            session: ConsultationSession containing the clip
            clip: ClipMetadata to persist
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = """
            INSERT INTO transcriptions 
            (user_id, consultation_id, clip_order, job_id, status, audio_s3_key, 
             transcript_text, chunk_sequence, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (job_id) DO UPDATE
            SET status = EXCLUDED.status, 
                clip_order = EXCLUDED.clip_order,
                updated_at = CURRENT_TIMESTAMP
            """
            self._database_manager.execute_with_retry(
                query,
                (session.user_id, session.consultation_id, clip.clip_order, 
                 clip.job_id, clip.status, clip.audio_s3_key or 'pending',
                 clip.transcript_text or '', clip.chunk_sequence)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to persist clip: {str(e)}")
            return False
    
    def _update_clip_in_db(self, session: ConsultationSession, clip: ClipMetadata) -> bool:
        """
        Update clip in database
        
        Args:
            session: ConsultationSession containing the clip
            clip: ClipMetadata to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = """
            UPDATE transcriptions
            SET status = %s, 
                audio_s3_key = %s,
                transcript_text = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE job_id = %s AND user_id = %s
            """
            self._database_manager.execute_with_retry(
                query,
                (clip.status, clip.audio_s3_key or 'pending', 
                 clip.transcript_text or '', clip.job_id, session.user_id)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update clip in database: {str(e)}")
            return False
    
    def _update_session_status(self, consultation_id: str, status: str) -> bool:
        """
        Update consultation session status in database
        
        Args:
            consultation_id: Consultation identifier
            status: New status
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = """
            UPDATE consultations
            SET status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE consultation_id = %s
            """
            self._database_manager.execute_with_retry(query, (status, consultation_id))
            return True
        except Exception as e:
            logger.error(f"Failed to update consultation status: {str(e)}")
            return False
    
    def _load_session_from_db(self, consultation_id: str) -> Optional[ConsultationSession]:
        """
        Load consultation session from database
        
        Args:
            consultation_id: Consultation identifier
            
        Returns:
            ConsultationSession if found, None otherwise
        """
        try:
            # Load consultation
            query = """
            SELECT consultation_id, user_id, status, created_at, updated_at
            FROM consultations
            WHERE consultation_id = %s
            """
            result = self._database_manager.execute_with_retry(query, (consultation_id,))
            
            if not result or len(result) == 0:
                return None
            
            row = result[0]
            session = ConsultationSession(
                consultation_id=row[0],
                user_id=row[1],
                status=row[2],
                created_at=row[3],
                last_activity=row[4]
            )
            
            # Load clips
            clips_query = """
            SELECT job_id, clip_order, status, audio_s3_key, transcript_text, 
                   chunk_sequence, created_at, updated_at
            FROM transcriptions
            WHERE consultation_id = %s
            ORDER BY clip_order ASC
            """
            clips_result = self._database_manager.execute_with_retry(
                clips_query, (consultation_id,)
            )
            
            if clips_result:
                for clip_row in clips_result:
                    clip = ClipMetadata(
                        clip_id=clip_row[0],  # Using job_id as clip_id
                        clip_order=clip_row[1],
                        job_id=clip_row[0],
                        status=clip_row[2],
                        audio_s3_key=clip_row[3] if clip_row[3] != 'pending' else None,
                        transcript_text=clip_row[4] if clip_row[4] else None,
                        chunk_sequence=clip_row[5] or 0,
                        created_at=clip_row[6],
                        updated_at=clip_row[7]
                    )
                    session.clips[clip.clip_id] = clip
                    
                    # Update next_clip_order
                    if clip.clip_order >= session.next_clip_order:
                        session.next_clip_order = clip.clip_order + 1
            
            # Add to active sessions
            self._sessions[consultation_id] = session
            
            logger.info(f"Consultation session loaded from database: {consultation_id} "
                       f"(clips={len(session.clips)})")
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to load consultation session from database: {str(e)}")
            return None
