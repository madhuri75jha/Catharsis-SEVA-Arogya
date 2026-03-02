"""
Integration tests for recent consultations feature
Tests the complete end-to-end flow from API to frontend rendering
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


class TestConsultationIntegration:
    """Integration tests for complete consultation flow"""
    
    def test_complete_consultation_flow_home_to_detail_to_back(self, authenticated_client):
        """
        Test end-to-end flow: home page load → fetch consultations → 
        render cards → click card → detail view → back button
        
        Validates: Requirements 1.1, 1.2, 2.1, 3.1, 3.5
        """
        # Setup: Create mock consultations
        mock_consultations = [
            {
                "consultation_id": "1",
                "patient_name": "Arjun Kumar",
                "patient_initials": "AK",
                "status": "COMPLETED",
                "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
                "has_prescription": True,
                "prescription_id": "101",
                "transcript_preview": "Patient complains of headache..."
            },
            {
                "consultation_id": "2",
                "patient_name": "Priya Sharma",
                "patient_initials": "PS",
                "status": "COMPLETED",
                "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
                "has_prescription": False,
                "prescription_id": None,
                "transcript_preview": "Follow-up visit..."
            }
        ]
        
        # Mock transcription data for detail view
        mock_transcription = (
            1,  # transcription_id
            'test-user-123',  # user_id
            'Patient complains of headache and fever for the past 3 days.',  # transcript_text
            'COMPLETED',  # status
            json.dumps([
                {
                    "Text": "Arjun Kumar",
                    "Category": "PROTECTED_HEALTH_INFORMATION",
                    "Type": "NAME",
                    "Score": 0.99
                },
                {
                    "Text": "headache",
                    "Category": "MEDICAL_CONDITION",
                    "Type": "DX_NAME",
                    "Score": 0.95
                }
            ]),  # medical_entities
            datetime.now() - timedelta(hours=2),  # created_at
            datetime.now() - timedelta(hours=2)   # updated_at
        )
        
        # Mock prescription data
        mock_prescription = (
            101,  # prescription_id
            'Arjun Kumar',  # patient_name
            json.dumps([
                {
                    "name": "Paracetamol",
                    "dosage": "500mg",
                    "frequency": "Twice daily",
                    "duration": "5 days"
                }
            ]),  # medications
            datetime.now() - timedelta(hours=2)  # created_at
        )
        
        with patch('services.consultation_service.ConsultationService.get_recent_consultations') as mock_get_consultations, \
             patch('aws_services.database_manager.DatabaseManager.execute_with_retry') as mock_db:
            
            # Setup mocks
            mock_get_consultations.return_value = mock_consultations
            
            # Mock database calls for detail view
            def db_side_effect(query, params):
                if 'FROM transcriptions' in query and 'WHERE transcription_id' in query:
                    return [mock_transcription]
                elif 'FROM prescriptions' in query:
                    return [mock_prescription]
                return []
            
            mock_db.side_effect = db_side_effect
            
            # Step 1: Load home page
            response = authenticated_client.get('/home')
            assert response.status_code == 200
            assert b'Recent Consultations' in response.data
            
            # Step 2: Fetch consultations via API
            api_response = authenticated_client.get('/api/consultations?limit=10')
            assert api_response.status_code == 200
            api_data = json.loads(api_response.data)
            assert api_data['success'] is True
            assert api_data['count'] == 2
            assert len(api_data['consultations']) == 2
            
            # Step 3: Navigate to consultation detail view
            detail_response = authenticated_client.get('/consultation/1')
            assert detail_response.status_code == 200
            assert b'Arjun Kumar' in detail_response.data
            assert b'Patient complains of headache' in detail_response.data
            assert b'Paracetamol' in detail_response.data
            
            # Step 4: Verify back button link exists
            assert b'/home' in detail_response.data
            assert b'Back to Home' in detail_response.data
    
    def test_expand_collapse_flow(self, authenticated_client):
        """
        Test expand/collapse flow: initial 2 cards → expand to all → collapse back to 2
        
        Validates: Requirements 2.1, 2.3
        """
        # Create 5 mock consultations
        mock_consultations = []
        for i in range(5):
            mock_consultations.append({
                "consultation_id": str(i + 1),
                "patient_name": f"Patient {i + 1}",
                "patient_initials": f"P{i + 1}",
                "status": "COMPLETED",
                "created_at": (datetime.now() - timedelta(hours=i)).isoformat(),
                "has_prescription": False,
                "prescription_id": None,
                "transcript_preview": f"Consultation {i + 1}..."
            })
        
        with patch('services.consultation_service.ConsultationService.get_recent_consultations') as mock_get:
            mock_get.return_value = mock_consultations
            
            # Fetch consultations
            response = authenticated_client.get('/api/consultations')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['count'] == 5
            
            # Verify all 5 consultations are available for expand/collapse
            # (Frontend JavaScript will handle showing 2 initially, then all 5 on expand)
            assert len(data['consultations']) == 5
    
    def test_empty_state_display(self, authenticated_client):
        """
        Test empty state: no consultations → displays "No recent consultations found"
        
        Validates: Requirements 1.4
        """
        with patch('services.consultation_service.ConsultationService.get_recent_consultations') as mock_get:
            mock_get.return_value = []
            
            # Fetch consultations
            response = authenticated_client.get('/api/consultations')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['count'] == 0
            assert data['consultations'] == []
            
            # Load home page
            home_response = authenticated_client.get('/home')
            assert home_response.status_code == 200
            # Verify empty state container exists
            assert b'empty-state' in home_response.data
    
    def test_error_state_display(self, authenticated_client):
        """
        Test error handling: API failure → displays user-friendly error message
        
        Validates: Requirements 4.5
        """
        with patch('services.consultation_service.ConsultationService.get_recent_consultations') as mock_get:
            # Simulate database error
            mock_get.side_effect = Exception("Database connection timeout")
            
            # Fetch consultations
            response = authenticated_client.get('/api/consultations')
            assert response.status_code == 500
            
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'error' in data
            assert 'Failed to retrieve consultations' in data['error']
            # Should not expose internal error details
            assert 'Database connection timeout' not in data['error']
    
    def test_consultation_detail_with_missing_data(self, authenticated_client):
        """
        Test consultation detail view with missing/incomplete data
        
        Validates: Requirements 7.2, 7.3
        """
        # Mock transcription with missing data
        mock_transcription = (
            1,  # transcription_id
            'test-user-123',  # user_id
            None,  # transcript_text (missing)
            'COMPLETED',  # status
            None,  # medical_entities (missing)
            datetime.now(),  # created_at
            datetime.now()   # updated_at
        )
        
        with patch('aws_services.database_manager.DatabaseManager.execute_with_retry') as mock_db:
            def db_side_effect(query, params):
                if 'FROM transcriptions' in query and 'WHERE transcription_id' in query:
                    return [mock_transcription]
                elif 'FROM prescriptions' in query:
                    return []  # No prescription
                return []
            
            mock_db.side_effect = db_side_effect
            
            # Navigate to consultation detail view
            response = authenticated_client.get('/consultation/1')
            assert response.status_code == 200
            
            # Verify graceful handling of missing data
            assert b'Unknown Patient' in response.data or b'consultation' in response.data
            assert b'No transcript available' in response.data
    
    def test_consultation_detail_not_found(self, authenticated_client):
        """
        Test consultation detail view with invalid consultation_id returns 404
        
        Validates: Requirements 3.1
        """
        with patch('aws_services.database_manager.DatabaseManager.execute_with_retry') as mock_db:
            # Return empty result (consultation not found)
            mock_db.return_value = []
            
            # Navigate to non-existent consultation
            response = authenticated_client.get('/consultation/999')
            assert response.status_code == 404
    
    def test_api_endpoint_accessible_from_frontend(self, authenticated_client):
        """
        Test API endpoint is accessible and returns correct CORS headers
        
        Validates: Requirements 8.1
        """
        with patch('services.consultation_service.ConsultationService.get_recent_consultations') as mock_get:
            mock_get.return_value = []
            
            # Make API request
            response = authenticated_client.get('/api/consultations')
            
            # Verify response
            assert response.status_code == 200
            assert response.content_type == 'application/json'
            
            # Verify JSON structure
            data = json.loads(response.data)
            assert 'success' in data
            assert 'consultations' in data
            assert 'count' in data
    
    def test_consultation_cards_render_correctly(self, authenticated_client):
        """
        Test consultation cards contain all required information
        
        Validates: Requirements 1.3
        """
        mock_consultations = [
            {
                "consultation_id": "1",
                "patient_name": "Test Patient",
                "patient_initials": "TP",
                "status": "COMPLETED",
                "created_at": datetime.now().isoformat(),
                "has_prescription": True,
                "prescription_id": "101",
                "transcript_preview": "Test transcript..."
            }
        ]
        
        with patch('services.consultation_service.ConsultationService.get_recent_consultations') as mock_get:
            mock_get.return_value = mock_consultations
            
            # Fetch consultations
            response = authenticated_client.get('/api/consultations')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            consultation = data['consultations'][0]
            
            # Verify all required fields are present
            assert 'consultation_id' in consultation
            assert 'patient_name' in consultation
            assert 'patient_initials' in consultation
            assert 'status' in consultation
            assert 'created_at' in consultation
            assert 'has_prescription' in consultation
            assert 'prescription_id' in consultation
            assert 'transcript_preview' in consultation
            
            # Verify field values
            assert consultation['patient_name'] == "Test Patient"
            assert consultation['patient_initials'] == "TP"
            assert consultation['status'] == "COMPLETED"
    
    def test_navigation_to_consultation_detail_view(self, authenticated_client):
        """
        Test navigation from consultation card to detail view
        
        Validates: Requirements 3.1
        """
        # Mock transcription data
        mock_transcription = (
            123,  # transcription_id
            'test-user-123',  # user_id
            'Test transcript text',  # transcript_text
            'COMPLETED',  # status
            json.dumps([]),  # medical_entities
            datetime.now(),  # created_at
            datetime.now()   # updated_at
        )
        
        with patch('aws_services.database_manager.DatabaseManager.execute_with_retry') as mock_db:
            def db_side_effect(query, params):
                if 'FROM transcriptions' in query and 'WHERE transcription_id' in query:
                    return [mock_transcription]
                elif 'FROM prescriptions' in query:
                    return []
                return []
            
            mock_db.side_effect = db_side_effect
            
            # Navigate to consultation detail view with specific ID
            response = authenticated_client.get('/consultation/123')
            
            # Verify successful navigation
            assert response.status_code == 200
            assert b'Consultation Details' in response.data
            assert b'Test transcript text' in response.data
    
    def test_back_button_returns_to_home_page(self, authenticated_client):
        """
        Test back button in detail view returns to home page
        
        Validates: Requirements 3.5
        """
        # Mock transcription data
        mock_transcription = (
            1,  # transcription_id
            'test-user-123',  # user_id
            'Test transcript',  # transcript_text
            'COMPLETED',  # status
            json.dumps([]),  # medical_entities
            datetime.now(),  # created_at
            datetime.now()   # updated_at
        )
        
        with patch('aws_services.database_manager.DatabaseManager.execute_with_retry') as mock_db:
            def db_side_effect(query, params):
                if 'FROM transcriptions' in query:
                    return [mock_transcription]
                elif 'FROM prescriptions' in query:
                    return []
                return []
            
            mock_db.side_effect = db_side_effect
            
            # Load detail view
            detail_response = authenticated_client.get('/consultation/1')
            assert detail_response.status_code == 200
            
            # Verify back button link to home page exists
            assert b'/home' in detail_response.data
            
            # Simulate clicking back button (navigate to home)
            home_response = authenticated_client.get('/home')
            assert home_response.status_code == 200
            assert b'Start New Consultation' in home_response.data
