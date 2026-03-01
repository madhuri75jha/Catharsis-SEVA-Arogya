"""
Pytest configuration and fixtures for SEVA Arogya tests
"""
import pytest
import os
from hypothesis import settings, Verbosity
from unittest.mock import Mock, patch

# Configure Hypothesis for property-based testing
settings.register_profile("dev", max_examples=100, verbosity=Verbosity.normal)
settings.load_profile("dev")


@pytest.fixture
def app():
    """Create and configure a test Flask application instance"""
    # Mock the database manager to avoid connection timeout
    with patch('aws_services.database_manager.DatabaseManager') as mock_db:
        # Create a mock database manager instance
        mock_db_instance = Mock()
        mock_db.return_value = mock_db_instance
        
        # Import app after patching
        from app import app as flask_app
        
        flask_app.config.update({
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "WTF_CSRF_ENABLED": False,
        })
        
        yield flask_app


@pytest.fixture
def client(app):
    """Create a test client for the Flask application"""
    return app.test_client()


@pytest.fixture
def authenticated_client(client, app):
    """Create an authenticated test client with a logged-in session"""
    with client.session_transaction() as session:
        session['user_id'] = 'test-user-123'
        session['username'] = 'testuser'
        session['_fresh'] = True
    
    return client
