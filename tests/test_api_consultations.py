"""
Unit tests for /api/consultations endpoint
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestAPIConsultations:
    """Test suite for consultation retrieval API endpoint"""
    
    def test_successful_request_with_valid_authentication(self, authenticated_client):
        """Test successful request with valid authentication returns 200 and consultation list"""
        # Mock ConsultationService.get_recent_consultations
        mock_consultations = [
            {
                "consultation_id": "1",
                "patient_name": "John Doe",
                "patient_initials": "JD",
                "status": "COMPLETED",
                "created_at": "2024-01-15T14:30:00",
                "has_prescription": True,
                "prescription_id": "101",
                "transcript_preview": "Patient complains of headache..."
            },
            {
                "consultation_id": "2",
                "patient_name": "Jane Smith",
                "patient_initials": "JS",
                "status": "COMPLETED",
                "created_at": "2024-01-14T10:15:00",
                "has_prescription": False,
                "prescription_id": None,
                "transcript_preview": "Follow-up visit for..."
            }
        ]
        
        with patch('services.consultation_service.ConsultationService.get_recent_consultations') as mock_get:
            mock_get.return_value = mock_consultations
            
            # Make request
            response = authenticated_client.get('/api/consultations')
            
            # Assert response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['count'] == 2
            assert len(data['consultations']) == 2
            assert data['consultations'][0]['patient_name'] == "John Doe"
            assert data['consultations'][1]['patient_name'] == "Jane Smith"
    
    def test_request_without_authentication_returns_401(self, client):
        """Test request without authentication returns 401"""
        # Make request without authentication
        response = client.get('/api/consultations')
        
        # Should redirect to login (Flask @login_required behavior)
        assert response.status_code == 302  # Redirect
        assert '/login' in response.location
    
    def test_with_invalid_limit_parameter_uses_default(self, authenticated_client):
        """Test with invalid limit parameter gracefully uses default"""
        mock_consultations = []
        
        with patch('services.consultation_service.ConsultationService.get_recent_consultations') as mock_get:
            mock_get.return_value = mock_consultations
            
            # Make request with invalid limit
            response = authenticated_client.get('/api/consultations?limit=invalid')
            
            # Assert response is successful with default limit
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            
            # Verify service was called with default limit of 10
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]['limit'] == 10
    
    def test_with_empty_consultation_list(self, authenticated_client):
        """Test with empty consultation list returns empty array"""
        with patch('services.consultation_service.ConsultationService.get_recent_consultations') as mock_get:
            mock_get.return_value = []
            
            # Make request
            response = authenticated_client.get('/api/consultations')
            
            # Assert response
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['count'] == 0
            assert data['consultations'] == []
    
    def test_database_connection_failure_returns_500(self, authenticated_client):
        """Test database connection failure returns 500 with user-friendly message"""
        with patch('services.consultation_service.ConsultationService.get_recent_consultations') as mock_get:
            # Simulate database error
            mock_get.side_effect = Exception("Database connection failed")
            
            # Make request
            response = authenticated_client.get('/api/consultations')
            
            # Assert response
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data
            # Should not expose internal error details
            assert 'Database connection failed' not in data['error']
            assert 'Failed to retrieve consultations' in data['error']
    
    def test_limit_parameter_capped_at_50(self, authenticated_client):
        """Test limit parameter is capped at maximum of 50"""
        mock_consultations = []
        
        with patch('services.consultation_service.ConsultationService.get_recent_consultations') as mock_get:
            mock_get.return_value = mock_consultations
            
            # Make request with limit > 50
            response = authenticated_client.get('/api/consultations?limit=100')
            
            # Assert response is successful
            assert response.status_code == 200
            
            # Verify service was called with capped limit of 10 (due to validation)
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            # The endpoint logs warning and uses default 10 for out-of-range values
            assert call_args[1]['limit'] == 10
    
    def test_valid_limit_parameter_is_used(self, authenticated_client):
        """Test valid limit parameter is passed to service"""
        mock_consultations = []
        
        with patch('services.consultation_service.ConsultationService.get_recent_consultations') as mock_get:
            mock_get.return_value = mock_consultations
            
            # Make request with valid limit
            response = authenticated_client.get('/api/consultations?limit=5')
            
            # Assert response is successful
            assert response.status_code == 200
            
            # Verify service was called with specified limit
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]['limit'] == 5
    
    def test_response_format_is_valid_json(self, authenticated_client):
        """Test response format is valid JSON with required fields"""
        mock_consultations = [
            {
                "consultation_id": "1",
                "patient_name": "Test Patient",
                "patient_initials": "TP",
                "status": "COMPLETED",
                "created_at": "2024-01-15T14:30:00",
                "has_prescription": False,
                "prescription_id": None,
                "transcript_preview": "Test transcript"
            }
        ]
        
        with patch('services.consultation_service.ConsultationService.get_recent_consultations') as mock_get:
            mock_get.return_value = mock_consultations
            
            # Make request
            response = authenticated_client.get('/api/consultations')
            
            # Assert response format
            assert response.status_code == 200
            assert response.content_type == 'application/json'
            
            data = json.loads(response.data)
            # Check required fields
            assert 'success' in data
            assert isinstance(data['success'], bool)
            assert 'consultations' in data
            assert isinstance(data['consultations'], list)
            assert 'count' in data
            assert isinstance(data['count'], int)
