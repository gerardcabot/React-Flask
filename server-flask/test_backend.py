"""
Test suite for the Flask backend API.
Tests all endpoints, error handling, and data validation.
"""

import pytest
import json
import os
import sys
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

# Add the server directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app, load_player_data, _calculate_goalkeeper_metrics, get_age_at_fixed_point_in_season

@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_s3_client():
    """Mock S3 client for testing."""
    with patch('main.s3_client') as mock_s3:
        yield mock_s3

@pytest.fixture
def sample_player_data():
    """Sample player data for testing."""
    return {
        "player_id": "12345",
        "name": "Test Player",
        "seasons": ["2015_2016", "2016_2017"],
        "dob": "1995-01-01",
        "position": "Midfielder"
    }

@pytest.fixture
def sample_events_data():
    """Sample events data for testing."""
    return [
        {
            "player_id": "12345",
            "type": "Pass",
            "location": "[50, 30]",
            "pass_end_location": "[60, 40]",
            "pass_outcome": None,
            "pass_goal_assist": False
        },
        {
            "player_id": "12345", 
            "type": "Shot",
            "location": "[80, 40]",
            "shot_outcome": "Goal",
            "shot_statsbomb_xg": 0.5
        }
    ]

class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_check_success(self, client):
        """Test health check returns 200."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data

class TestPlayerEndpoints:
    """Test player-related endpoints."""
    
    def test_players_endpoint_success(self, client, mock_s3_client, sample_player_data):
        """Test /players endpoint returns player list."""
        # Mock the player index data
        mock_s3_client.get_object.return_value = {
            'Body': MagicMock()
        }
        mock_s3_client.get_object.return_value['Body'].read.return_value = json.dumps({
            "Test Player": sample_player_data
        }).encode('utf-8')
        
        response = client.get('/players')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['name'] == "Test Player"
    
    def test_player_seasons_endpoint_success(self, client, mock_s3_client, sample_player_data):
        """Test /player_seasons endpoint."""
        mock_s3_client.get_object.return_value = {
            'Body': MagicMock()
        }
        mock_s3_client.get_object.return_value['Body'].read.return_value = json.dumps({
            "Test Player": sample_player_data
        }).encode('utf-8')
        
        response = client.get('/player_seasons?player_id=12345')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['player_id'] == "12345"
        assert data['seasons'] == ["2015_2016", "2016_2017"]
    
    def test_player_seasons_missing_id(self, client):
        """Test /player_seasons with missing player_id."""
        response = client.get('/player_seasons')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

class TestPlayerEvents:
    """Test player events endpoint."""
    
    def test_player_events_success(self, client, mock_s3_client, sample_events_data):
        """Test /player_events endpoint."""
        # Mock the load_player_data function
        with patch('main.load_player_data') as mock_load:
            mock_df = pd.DataFrame(sample_events_data)
            mock_load.return_value = mock_df
            
            response = client.get('/player_events?player_id=12345&season=2015_2016')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data) == 2
            assert data[0]['type'] == "Pass"
    
    def test_player_events_missing_params(self, client):
        """Test /player_events with missing parameters."""
        response = client.get('/player_events?player_id=12345')
        assert response.status_code == 400
        
        response = client.get('/player_events?season=2015_2016')
        assert response.status_code == 400

class TestVisualizationEndpoints:
    """Test visualization endpoints."""
    
    def test_pass_map_plot_success(self, client, sample_events_data):
        """Test /pass_map_plot endpoint."""
        with patch('main.load_player_data') as mock_load:
            mock_df = pd.DataFrame(sample_events_data)
            mock_load.return_value = mock_df
            
            response = client.get('/pass_map_plot?player_id=12345&season=2015_2016')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'passes' in data
            assert len(data['passes']) == 1  # Only one pass in sample data
    
    def test_shot_map_success(self, client, sample_events_data):
        """Test /shot_map endpoint."""
        with patch('main.load_player_data') as mock_load:
            mock_df = pd.DataFrame(sample_events_data)
            mock_load.return_value = mock_df
            
            response = client.get('/shot_map?player_id=12345&season=2015_2016')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'shots' in data
            assert len(data['shots']) == 1  # Only one shot in sample data
    
    def test_heatmap_redirects(self, client):
        """Test heatmap endpoints redirect to R2."""
        response = client.get('/pass_completion_heatmap?player_id=12345&season=2015_2016')
        assert response.status_code == 302  # Redirect
        
        response = client.get('/position_heatmap?player_id=12345&season=2015_2016')
        assert response.status_code == 302  # Redirect
        
        response = client.get('/pressure_heatmap?player_id=12345&season=2015_2016')
        assert response.status_code == 302  # Redirect

class TestGoalkeeperAnalysis:
    """Test goalkeeper analysis endpoint."""
    
    def test_goalkeeper_analysis_success(self, client):
        """Test goalkeeper analysis endpoint."""
        # Create sample goalkeeper data
        gk_data = [
            {
                "player_id": "12345",
                "type": "Goal Keeper",
                "goalkeeper_type": "Shot Saved",
                "goalkeeper_outcome": "Success",
                "location": "[80, 40]",
                "shot_end_location": "[85, 45]"
            }
        ]
        
        with patch('main.load_player_data') as mock_load:
            mock_df = pd.DataFrame(gk_data)
            mock_load.return_value = mock_df
            
            response = client.get('/api/player/12345/goalkeeper/analysis/2015_2016')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'summary_text_stats' in data
            assert 'charts_data' in data

class TestPredictionEndpoint:
    """Test prediction endpoint."""
    
    def test_scouting_predict_success(self, client, mock_s3_client):
        """Test /scouting_predict endpoint."""
        # Mock all required data
        mock_s3_client.get_object.return_value = {
            'Body': MagicMock()
        }
        
        # Mock player index
        mock_s3_client.get_object.return_value['Body'].read.return_value = json.dumps({
            "Test Player": {
                "player_id": "12345",
                "seasons": ["2015_2016"],
                "dob": "1995-01-01",
                "position": "Midfielder"
            }
        }).encode('utf-8')
        
        # Mock model loading
        with patch('main.load_model_from_r2_cached') as mock_model:
            mock_model.return_value = (
                MagicMock(),  # model
                MagicMock(),  # scaler
                {"features_used_for_ml_model": ["feature1", "feature2"]}  # config
            )
            
            # Mock feature extraction
            with patch('main.trainer_extract_base_features') as mock_extract:
                mock_extract.return_value = pd.Series({"feature1": 1.0, "feature2": 2.0})
                
                with patch('main.trainer_construct_ml_features_for_player_season') as mock_construct:
                    mock_construct.return_value = pd.Series({"feature1": 1.0, "feature2": 2.0})
                    
                    response = client.get('/scouting_predict?player_id=12345&season=2015_2016')
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert 'predicted_potential_score' in data

class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_safe_float(self):
        """Test safe_float function."""
        from main import safe_float
        
        assert safe_float("123.45") == 123.45
        assert safe_float("invalid") == 0.0
        assert safe_float(None) == 0.0
        assert safe_float(123) == 123.0
    
    def test_safe_literal_eval(self):
        """Test safe_literal_eval function."""
        from main import safe_literal_eval
        
        assert safe_literal_eval("[1, 2, 3]") == [1, 2, 3]
        assert safe_literal_eval("invalid") is None
        assert safe_literal_eval(None) is None
    
    def test_get_age_at_fixed_point_in_season(self):
        """Test age calculation function."""
        age = get_age_at_fixed_point_in_season("1995-01-01", "2015_2016")
        assert age == 21
        
        age = get_age_at_fixed_point_in_season("1995-12-31", "2015_2016")
        assert age == 20
        
        age = get_age_at_fixed_point_in_season("invalid", "2015_2016")
        assert age is None

class TestErrorHandling:
    """Test error handling."""
    
    def test_invalid_json_request(self, client):
        """Test handling of invalid JSON requests."""
        response = client.post('/api/custom_model/trigger_github_training',
                             data="invalid json",
                             content_type='application/json')
        assert response.status_code == 400
    
    def test_missing_required_fields(self, client):
        """Test handling of missing required fields."""
        response = client.post('/api/custom_model/trigger_github_training',
                             json={})
        assert response.status_code == 400

class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limiting_applied(self, client):
        """Test that rate limiting is applied to endpoints."""
        # This would require more complex setup to test actual rate limiting
        # For now, just verify the limiter is configured
        from main import limiter
        assert limiter is not None

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
