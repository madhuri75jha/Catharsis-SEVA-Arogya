"""
Unit tests for ConsultationSessionManager

Tests session state management for multi-clip consultations including:
- Session creation and retrieval
- Clip addition and ordering
- Status updates
- Database persistence and recovery
- Idle session cleanup
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from aws_services.consultation_session_manager import (
    ConsultationSessionManager,
    ConsultationSession,
    ClipMetadata
)


@pytest.fixture
def mock_database_manager():
    """Create a mock database manager"""
    mock_db = Mock()
    mock_db.execute_with_retry = Mock(return_value=None)
    return mock_db


@pytest.fixture
def session_manager(mock_database_manager):
    """Create a ConsultationSessionManager instance with mocked database"""
    return ConsultationSessionManager(
        database_manager=mock_database_manager,
        idle_timeout=3600
    )


class TestConsultationSessionCreation:
    """Test consultation session creation"""
    
    def test_create_new_session(self, session_manager, mock_database_manager):
        """Test creating a new consultation session"""
        consultation_id = "consult-123"
        user_id = "user-456"
        
        session = session_manager.create_session(consultation_id, user_id)
        
        assert session is not None
        assert session.consultation_id == consultation_id
        assert session.user_id == user_id
        assert session.status == 'IN_PROGRESS'
        assert len(session.clips) == 0
        assert session.next_clip_order == 1
        
        # Verify database persistence was called
        mock_database_manager.execute_with_retry.assert_called()
    
    def test_create_duplicate_session_returns_existing(self, session_manager):
        """Test creating a session with duplicate ID returns existing session"""
        consultation_id = "consult-123"
        user_id = "user-456"
        
        session1 = session_manager.create_session(consultation_id, user_id)
        session2 = session_manager.create_session(consultation_id, user_id)
        
        assert session1 is session2
    
    def test_get_existing_session(self, session_manager):
        """Test retrieving an existing session"""
        consultation_id = "consult-123"
        user_id = "user-456"
        
        created_session = session_manager.create_session(consultation_id, user_id)
        retrieved_session = session_manager.get_session(consultation_id)
        
        assert retrieved_session is created_session
    
    def test_get_nonexistent_session_loads_from_db(self, session_manager, mock_database_manager):
        """Test retrieving a non-existent session attempts to load from database"""
        consultation_id = "consult-999"
        
        # Mock database to return no results
        mock_database_manager.execute_with_retry.return_value = []
        
        session = session_manager.get_session(consultation_id)
        
        assert session is None
        # Verify database query was attempted
        mock_database_manager.execute_with_retry.assert_called()


class TestClipManagement:
    """Test clip addition and management within consultations"""
    
    def test_add_clip_to_session(self, session_manager):
        """Test adding a clip to a consultation session"""
        consultation_id = "consult-123"
        user_id = "user-456"
        clip_id = "clip-1"
        job_id = "job-1"
        
        session_manager.create_session(consultation_id, user_id)
        clip = session_manager.add_clip(consultation_id, clip_id, job_id)
        
        assert clip is not None
        assert clip.clip_id == clip_id
        assert clip.job_id == job_id
        assert clip.clip_order == 1
        assert clip.status == 'recording'
    
    def test_add_multiple_clips_maintains_order(self, session_manager):
        """Test adding multiple clips maintains correct ordering"""
        consultation_id = "consult-123"
        user_id = "user-456"
        
        session_manager.create_session(consultation_id, user_id)
        
        clip1 = session_manager.add_clip(consultation_id, "clip-1", "job-1")
        clip2 = session_manager.add_clip(consultation_id, "clip-2", "job-2")
        clip3 = session_manager.add_clip(consultation_id, "clip-3", "job-3")
        
        assert clip1.clip_order == 1
        assert clip2.clip_order == 2
        assert clip3.clip_order == 3
        
        # Verify clips are returned in order
        clips = session_manager.get_clips_ordered(consultation_id)
        assert len(clips) == 3
        assert clips[0].clip_id == "clip-1"
        assert clips[1].clip_id == "clip-2"
        assert clips[2].clip_id == "clip-3"
    
    def test_add_clip_to_nonexistent_session(self, session_manager):
        """Test adding a clip to a non-existent session returns None"""
        clip = session_manager.add_clip("nonexistent", "clip-1", "job-1")
        assert clip is None
    
    def test_get_clips_ordered_empty_session(self, session_manager):
        """Test getting clips from a session with no clips"""
        consultation_id = "consult-123"
        user_id = "user-456"
        
        session_manager.create_session(consultation_id, user_id)
        clips = session_manager.get_clips_ordered(consultation_id)
        
        assert clips == []
    
    def test_get_clips_ordered_nonexistent_session(self, session_manager):
        """Test getting clips from a non-existent session returns empty list"""
        clips = session_manager.get_clips_ordered("nonexistent")
        assert clips == []


class TestClipStatusUpdates:
    """Test clip status updates"""
    
    def test_update_clip_status(self, session_manager):
        """Test updating clip status"""
        consultation_id = "consult-123"
        user_id = "user-456"
        clip_id = "clip-1"
        
        session_manager.create_session(consultation_id, user_id)
        session_manager.add_clip(consultation_id, clip_id, "job-1")
        
        success = session_manager.update_clip_status(
            consultation_id, clip_id, 'uploading'
        )
        
        assert success is True
        
        session = session_manager.get_session(consultation_id)
        clip = session.get_clip(clip_id)
        assert clip.status == 'uploading'
    
    def test_update_clip_with_audio_key(self, session_manager):
        """Test updating clip with audio S3 key"""
        consultation_id = "consult-123"
        user_id = "user-456"
        clip_id = "clip-1"
        
        session_manager.create_session(consultation_id, user_id)
        session_manager.add_clip(consultation_id, clip_id, "job-1")
        
        success = session_manager.update_clip_status(
            consultation_id, clip_id, 'completed',
            audio_s3_key='s3://bucket/audio.mp3'
        )
        
        assert success is True
        
        session = session_manager.get_session(consultation_id)
        clip = session.get_clip(clip_id)
        assert clip.audio_s3_key == 's3://bucket/audio.mp3'
    
    def test_update_clip_with_transcript(self, session_manager):
        """Test updating clip with transcript text"""
        consultation_id = "consult-123"
        user_id = "user-456"
        clip_id = "clip-1"
        
        session_manager.create_session(consultation_id, user_id)
        session_manager.add_clip(consultation_id, clip_id, "job-1")
        
        transcript = "Patient reports headache"
        success = session_manager.update_clip_status(
            consultation_id, clip_id, 'completed',
            transcript_text=transcript
        )
        
        assert success is True
        
        session = session_manager.get_session(consultation_id)
        clip = session.get_clip(clip_id)
        assert clip.transcript_text == transcript
    
    def test_update_clip_with_error(self, session_manager):
        """Test updating clip with error message"""
        consultation_id = "consult-123"
        user_id = "user-456"
        clip_id = "clip-1"
        
        session_manager.create_session(consultation_id, user_id)
        session_manager.add_clip(consultation_id, clip_id, "job-1")
        
        error_msg = "Transcription failed"
        success = session_manager.update_clip_status(
            consultation_id, clip_id, 'failed',
            error_message=error_msg
        )
        
        assert success is True
        
        session = session_manager.get_session(consultation_id)
        clip = session.get_clip(clip_id)
        assert clip.status == 'failed'
        assert clip.error_message == error_msg
    
    def test_update_nonexistent_clip(self, session_manager):
        """Test updating a non-existent clip returns False"""
        consultation_id = "consult-123"
        user_id = "user-456"
        
        session_manager.create_session(consultation_id, user_id)
        
        success = session_manager.update_clip_status(
            consultation_id, "nonexistent-clip", 'completed'
        )
        
        assert success is False
    
    def test_update_clip_in_nonexistent_session(self, session_manager):
        """Test updating a clip in non-existent session returns False"""
        success = session_manager.update_clip_status(
            "nonexistent", "clip-1", 'completed'
        )
        
        assert success is False


class TestSessionCompletion:
    """Test consultation session completion"""
    
    def test_complete_session(self, session_manager):
        """Test marking a session as completed"""
        consultation_id = "consult-123"
        user_id = "user-456"
        
        session_manager.create_session(consultation_id, user_id)
        success = session_manager.complete_session(consultation_id)
        
        assert success is True
        
        session = session_manager.get_session(consultation_id)
        assert session.status == 'COMPLETED'
    
    def test_complete_nonexistent_session(self, session_manager):
        """Test completing a non-existent session returns False"""
        success = session_manager.complete_session("nonexistent")
        assert success is False


class TestSessionRemoval:
    """Test session removal from active sessions"""
    
    def test_remove_session(self, session_manager):
        """Test removing a session from active sessions"""
        consultation_id = "consult-123"
        user_id = "user-456"
        
        session_manager.create_session(consultation_id, user_id)
        assert session_manager.get_active_count() == 1
        
        removed_session = session_manager.remove_session(consultation_id)
        
        assert removed_session is not None
        assert removed_session.consultation_id == consultation_id
        assert session_manager.get_active_count() == 0
    
    def test_remove_nonexistent_session(self, session_manager):
        """Test removing a non-existent session returns None"""
        removed_session = session_manager.remove_session("nonexistent")
        assert removed_session is None


class TestIdleSessionCleanup:
    """Test idle session cleanup"""
    
    def test_cleanup_idle_sessions(self, session_manager):
        """Test cleanup of idle sessions"""
        # Create session manager with short timeout for testing
        short_timeout_manager = ConsultationSessionManager(
            database_manager=Mock(),
            idle_timeout=1  # 1 second timeout
        )
        
        consultation_id = "consult-123"
        user_id = "user-456"
        
        short_timeout_manager.create_session(consultation_id, user_id)
        assert short_timeout_manager.get_active_count() == 1
        
        # Wait for session to become idle
        time.sleep(1.5)
        
        cleaned = short_timeout_manager.cleanup_idle_sessions()
        
        assert cleaned == 1
        assert short_timeout_manager.get_active_count() == 0
    
    def test_cleanup_does_not_remove_active_sessions(self, session_manager):
        """Test cleanup does not remove active sessions"""
        consultation_id = "consult-123"
        user_id = "user-456"
        
        session_manager.create_session(consultation_id, user_id)
        
        cleaned = session_manager.cleanup_idle_sessions()
        
        assert cleaned == 0
        assert session_manager.get_active_count() == 1


class TestStatistics:
    """Test session statistics"""
    
    def test_get_statistics(self, session_manager):
        """Test getting session statistics"""
        # Create multiple sessions with clips
        session_manager.create_session("consult-1", "user-1")
        session_manager.add_clip("consult-1", "clip-1", "job-1")
        session_manager.add_clip("consult-1", "clip-2", "job-2")
        
        session_manager.create_session("consult-2", "user-2")
        session_manager.add_clip("consult-2", "clip-3", "job-3")
        
        session_manager.complete_session("consult-2")
        
        stats = session_manager.get_statistics()
        
        assert stats['active_sessions'] == 2
        assert stats['in_progress'] == 1
        assert stats['completed'] == 1
        assert stats['total_clips'] == 3
    
    def test_get_active_count(self, session_manager):
        """Test getting active session count"""
        assert session_manager.get_active_count() == 0
        
        session_manager.create_session("consult-1", "user-1")
        assert session_manager.get_active_count() == 1
        
        session_manager.create_session("consult-2", "user-2")
        assert session_manager.get_active_count() == 2
        
        session_manager.remove_session("consult-1")
        assert session_manager.get_active_count() == 1


class TestDatabasePersistence:
    """Test database persistence operations"""
    
    def test_session_persisted_on_creation(self, session_manager, mock_database_manager):
        """Test that session is persisted to database on creation"""
        consultation_id = "consult-123"
        user_id = "user-456"
        
        session_manager.create_session(consultation_id, user_id)
        
        # Verify database insert was called
        calls = mock_database_manager.execute_with_retry.call_args_list
        assert len(calls) > 0
        
        # Check that INSERT INTO consultations was called
        insert_call = calls[0]
        query = insert_call[0][0]
        params = insert_call[0][1]
        
        assert 'INSERT INTO consultations' in query
        assert params[0] == consultation_id
        assert params[1] == user_id
    
    def test_clip_persisted_on_addition(self, session_manager, mock_database_manager):
        """Test that clip is persisted to database when added"""
        consultation_id = "consult-123"
        user_id = "user-456"
        clip_id = "clip-1"
        job_id = "job-1"
        
        session_manager.create_session(consultation_id, user_id)
        mock_database_manager.execute_with_retry.reset_mock()
        
        session_manager.add_clip(consultation_id, clip_id, job_id)
        
        # Verify database insert was called
        calls = mock_database_manager.execute_with_retry.call_args_list
        assert len(calls) > 0
        
        # Check that INSERT INTO transcriptions was called
        insert_call = calls[0]
        query = insert_call[0][0]
        params = insert_call[0][1]
        
        assert 'INSERT INTO transcriptions' in query
        assert params[0] == user_id
        assert params[1] == consultation_id
    
    def test_clip_updated_in_database(self, session_manager, mock_database_manager):
        """Test that clip updates are persisted to database"""
        consultation_id = "consult-123"
        user_id = "user-456"
        clip_id = "clip-1"
        
        session_manager.create_session(consultation_id, user_id)
        session_manager.add_clip(consultation_id, clip_id, "job-1")
        mock_database_manager.execute_with_retry.reset_mock()
        
        session_manager.update_clip_status(
            consultation_id, clip_id, 'completed',
            audio_s3_key='s3://bucket/audio.mp3'
        )
        
        # Verify database update was called
        calls = mock_database_manager.execute_with_retry.call_args_list
        assert len(calls) > 0
        
        # Check that UPDATE transcriptions was called
        update_call = calls[0]
        query = update_call[0][0]
        
        assert 'UPDATE transcriptions' in query
    
    def test_session_status_updated_in_database(self, session_manager, mock_database_manager):
        """Test that session status updates are persisted to database"""
        consultation_id = "consult-123"
        user_id = "user-456"
        
        session_manager.create_session(consultation_id, user_id)
        mock_database_manager.execute_with_retry.reset_mock()
        
        session_manager.complete_session(consultation_id)
        
        # Verify database update was called
        calls = mock_database_manager.execute_with_retry.call_args_list
        assert len(calls) > 0
        
        # Check that UPDATE consultations was called
        update_call = calls[0]
        query = update_call[0][0]
        params = update_call[0][1]
        
        assert 'UPDATE consultations' in query
        assert params[0] == 'COMPLETED'


class TestThreadSafety:
    """Test thread safety of session manager"""
    
    def test_concurrent_session_creation(self, session_manager):
        """Test that concurrent session creation is thread-safe"""
        import threading
        
        results = []
        errors = []
        
        def create_session(consultation_id, user_id):
            try:
                session = session_manager.create_session(consultation_id, user_id)
                results.append(session)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(10):
            thread = threading.Thread(
                target=create_session,
                args=(f"consult-{i}", f"user-{i}")
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(results) == 10
        assert session_manager.get_active_count() == 10
    
    def test_concurrent_clip_addition(self, session_manager):
        """Test that concurrent clip addition is thread-safe"""
        import threading
        
        consultation_id = "consult-123"
        user_id = "user-456"
        
        session_manager.create_session(consultation_id, user_id)
        
        results = []
        errors = []
        
        def add_clip(clip_id, job_id):
            try:
                clip = session_manager.add_clip(consultation_id, clip_id, job_id)
                results.append(clip)
            except Exception as e:
                errors.append(e)
        
        threads = []
        for i in range(10):
            thread = threading.Thread(
                target=add_clip,
                args=(f"clip-{i}", f"job-{i}")
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0
        assert len(results) == 10
        
        clips = session_manager.get_clips_ordered(consultation_id)
        assert len(clips) == 10
        
        # Verify clip orders are sequential and unique
        clip_orders = [clip.clip_order for clip in clips]
        assert clip_orders == list(range(1, 11))


class TestConsultationSessionDataModel:
    """Test ConsultationSession data model"""
    
    def test_session_add_clip(self):
        """Test adding clip to session"""
        session = ConsultationSession(
            consultation_id="consult-123",
            user_id="user-456"
        )
        
        clip = session.add_clip("clip-1", "job-1")
        
        assert clip.clip_id == "clip-1"
        assert clip.clip_order == 1
        assert session.next_clip_order == 2
    
    def test_session_get_clips_ordered(self):
        """Test getting clips in order"""
        session = ConsultationSession(
            consultation_id="consult-123",
            user_id="user-456"
        )
        
        session.add_clip("clip-3", "job-3")
        session.add_clip("clip-1", "job-1")
        session.add_clip("clip-2", "job-2")
        
        clips = session.get_clips_ordered()
        
        assert len(clips) == 3
        assert clips[0].clip_order == 1
        assert clips[1].clip_order == 2
        assert clips[2].clip_order == 3
    
    def test_session_idle_seconds(self):
        """Test calculating idle seconds"""
        session = ConsultationSession(
            consultation_id="consult-123",
            user_id="user-456"
        )
        
        # Manually set last_activity to 2 seconds ago
        session.last_activity = datetime.utcnow() - timedelta(seconds=2)
        
        idle_seconds = session.get_idle_seconds()
        
        assert idle_seconds >= 2.0
        assert idle_seconds < 3.0  # Allow some margin
