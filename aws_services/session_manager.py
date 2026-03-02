"""
Session Manager for WebSocket Streaming Sessions

Manages active WebSocket connections for real-time audio transcription streaming.
Tracks session state, enforces limits, and handles cleanup.
"""

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Session:
    """Data model for a streaming transcription session"""
    session_id: str
    user_id: str
    request_sid: str  # Socket.IO session ID
    job_id: Optional[str] = None
    audio_buffer: Optional[object] = None  # AudioBuffer instance
    transcribe_stream: Optional[object] = None  # TranscribeStream instance
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    quality: str = 'medium'
    sample_rate: int = 16000
    last_chunk_id: int = -1
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
    
    def get_idle_seconds(self) -> float:
        """Get seconds since last activity"""
        return (datetime.utcnow() - self.last_activity).total_seconds()


class SessionManager:
    """
    Manages active WebSocket streaming sessions
    
    Features:
    - Thread-safe session registry
    - Maximum concurrent session limit (100)
    - Idle session timeout (5 minutes)
    - Session lifecycle management
    """
    
    def __init__(self, max_sessions: int = 100, idle_timeout: int = 300):
        """
        Initialize SessionManager
        
        Args:
            max_sessions: Maximum number of concurrent sessions (default: 100)
            idle_timeout: Idle timeout in seconds (default: 300 = 5 minutes)
        """
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.Lock()
        self._max_sessions = max_sessions
        self._idle_timeout = idle_timeout
        
        logger.info(f"SessionManager initialized: max_sessions={max_sessions}, idle_timeout={idle_timeout}s")
    
    def create_session(self, session_id: str, user_id: str, request_sid: str,
                      quality: str = 'medium') -> Session:
        """
        Create a new session
        
        Args:
            session_id: Unique session identifier
            user_id: User ID
            request_sid: Socket.IO request session ID
            quality: Audio quality setting ('low', 'medium', 'high')
            
        Returns:
            Session instance
            
        Raises:
            RuntimeError: If session limit is reached or session already exists
        """
        with self._lock:
            # Check if session already exists
            if session_id in self._sessions:
                raise RuntimeError(f"Session already exists: {session_id}")
            
            # Check session limit
            if len(self._sessions) >= self._max_sessions:
                logger.warning(f"Session limit reached: {len(self._sessions)}/{self._max_sessions}")
                raise RuntimeError(f"Server at capacity. Maximum {self._max_sessions} concurrent sessions.")
            
            # Map quality to sample rate
            sample_rate_map = {
                'low': 8000,
                'medium': 16000,
                'high': 48000
            }
            sample_rate = sample_rate_map.get(quality, 16000)
            
            # Create session
            session = Session(
                session_id=session_id,
                user_id=user_id,
                request_sid=request_sid,
                quality=quality,
                sample_rate=sample_rate
            )
            
            self._sessions[session_id] = session
            
            logger.info(f"Session created: {session_id} (user={user_id}, quality={quality}, "
                       f"active_sessions={len(self._sessions)})")
            
            return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Retrieve session by ID
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session instance or None if not found
        """
        with self._lock:
            return self._sessions.get(session_id)
    
    def update_activity(self, session_id: str) -> None:
        """
        Update session last activity timestamp
        
        Args:
            session_id: Session identifier
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.update_activity()
    
    def remove_session(self, session_id: str) -> Optional[Session]:
        """
        Remove session and return it for cleanup
        
        Args:
            session_id: Session identifier
            
        Returns:
            Removed Session instance or None if not found
        """
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                logger.info(f"Session removed: {session_id} (active_sessions={len(self._sessions)})")
            return session
    
    def cleanup_idle_sessions(self) -> int:
        """
        Remove sessions that have been idle beyond timeout
        
        Returns:
            Number of sessions cleaned up
        """
        with self._lock:
            idle_sessions = []
            
            for session_id, session in self._sessions.items():
                if session.get_idle_seconds() > self._idle_timeout:
                    idle_sessions.append(session_id)
            
            # Remove idle sessions
            for session_id in idle_sessions:
                session = self._sessions.pop(session_id)
                logger.info(f"Idle session cleaned up: {session_id} "
                           f"(idle={session.get_idle_seconds():.1f}s)")
            
            if idle_sessions:
                logger.info(f"Cleaned up {len(idle_sessions)} idle sessions "
                           f"(active_sessions={len(self._sessions)})")
            
            return len(idle_sessions)
    
    def get_active_count(self) -> int:
        """
        Get count of active sessions
        
        Returns:
            Number of active sessions
        """
        with self._lock:
            return len(self._sessions)
    
    def get_all_sessions(self) -> Dict[str, Session]:
        """
        Get all active sessions (for graceful shutdown)
        
        Returns:
            Dictionary of session_id -> Session
        """
        with self._lock:
            return dict(self._sessions)
    
    def clear_all(self) -> int:
        """
        Clear all sessions (for graceful shutdown)
        
        Returns:
            Number of sessions cleared
        """
        with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
            logger.info(f"All sessions cleared: {count} sessions")
            return count
