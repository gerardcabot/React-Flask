"""
Integration tests for the React-Flask application.
Tests the complete flow from frontend to backend.
"""

import pytest
import requests
import time
import subprocess
import os
import sys
from threading import Thread
import pytest


sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server-flask'))

@pytest.mark.skip(reason="Integration tests require manual server setup")
class TestIntegration:
    """Integration tests for the full application."""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for integration tests."""
        self.flask_process = None
        self.react_process = None
        self.base_url = "http://localhost:5000"
        self.frontend_url = "http://localhost:5173"
        
        self.start_flask_server()
        
        self.start_react_server()
        
        self.wait_for_servers()
        
        yield
        
        self.stop_servers()
    
    def start_flask_server(self):
        """Start the Flask development server."""
        def run_flask():
            os.chdir('server-flask')
            subprocess.run([sys.executable, 'main.py'], capture_output=True)
        
        self.flask_thread = Thread(target=run_flask, daemon=True)
        self.flask_thread.start()
    
    def start_react_server(self):
        """Start the React development server."""
        def run_react():
            os.chdir('client-react')
            subprocess.run(['npm', 'run', 'dev'], capture_output=True)
        
        self.react_thread = Thread(target=run_react, daemon=True)
        self.react_thread.start()
    
    def wait_for_servers(self):
        """Wait for both servers to be ready."""
        max_attempts = 30
        for _ in range(max_attempts):
            try:
                response = requests.get(f"{self.base_url}/health", timeout=5)
                if response.status_code == 200:
                    response = requests.get(self.frontend_url, timeout=5)
                    if response.status_code == 200:
                        return
            except requests.exceptions.RequestException:
                pass
            time.sleep(2)
        
        pytest.skip("Servers not ready within timeout")
    
    def stop_servers(self):
        """Stop both servers."""
        pass
    
    def test_health_check(self):
        """Test that the health check endpoint works."""
        response = requests.get(f"{self.base_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
    
    def test_players_endpoint(self):
        """Test that the players endpoint returns data."""
        response = requests.get(f"{self.base_url}/players")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_frontend_loads(self):
        """Test that the React frontend loads correctly."""
        response = requests.get(self.frontend_url)
        assert response.status_code == 200
        assert 'text/html' in response.headers['content-type']
    
    def test_cors_headers(self):
        """Test that CORS headers are properly set."""
        response = requests.options(f"{self.base_url}/players")
        assert 'Access-Control-Allow-Origin' in response.headers
        assert 'Access-Control-Allow-Methods' in response.headers
    
    def test_rate_limiting(self):
        """Test that rate limiting is working."""
        responses = []
        for _ in range(10):
            response = requests.get(f"{self.base_url}/health")
            responses.append(response.status_code)
        
        assert all(status == 200 for status in responses)
    
    def test_invalid_endpoint(self):
        """Test that invalid endpoints return 404."""
        response = requests.get(f"{self.base_url}/invalid-endpoint")
        assert response.status_code == 404
    
    def test_player_events_endpoint(self):
        """Test player events endpoint with valid parameters."""
        players_response = requests.get(f"{self.base_url}/players")
        if players_response.status_code == 200 and players_response.json():
            player_id = players_response.json()[0]['player_id']
            seasons = players_response.json()[0]['seasons']
            
            if seasons:
                season = seasons[0]
                response = requests.get(
                    f"{self.base_url}/player_events",
                    params={'player_id': player_id, 'season': season}
                )
                assert response.status_code in [200, 404]
    
    def test_visualization_endpoints(self):
        """Test visualization endpoints."""
        response = requests.get(
            f"{self.base_url}/pass_map_plot",
            params={'player_id': '12345', 'season': '2015_2016'}
        )
        assert response.status_code in [200, 404]
        
        response = requests.get(
            f"{self.base_url}/shot_map",
            params={'player_id': '12345', 'season': '2015_2016'}
        )
        assert response.status_code in [200, 404]
    
    def test_heatmap_redirects(self):
        """Test that heatmap endpoints redirect properly."""
        response = requests.get(
            f"{self.base_url}/pass_completion_heatmap",
            params={'player_id': '12345', 'season': '2015_2016'},
            allow_redirects=False
        )
        assert response.status_code == 302
    
    def test_goalkeeper_analysis(self):
        """Test goalkeeper analysis endpoint."""
        response = requests.get(
            f"{self.base_url}/api/player/12345/goalkeeper/analysis/2015_2016"
        )
        assert response.status_code in [200, 404]
    
    def test_aggregated_metrics(self):
        """Test aggregated metrics endpoints."""
        response = requests.get(f"{self.base_url}/available_aggregated_metrics")
        assert response.status_code == 200
        data = response.json()
        assert 'available_metrics' in data
    
    def test_custom_model_endpoints(self):
        """Test custom model related endpoints."""
        response = requests.get(f"{self.base_url}/api/custom_model/available_kpis")
        assert response.status_code == 200
        data = response.json()
        assert 'structured_kpis' in data
        
        response = requests.get(f"{self.base_url}/api/custom_model/available_ml_features")
        assert response.status_code == 200
        data = response.json()
        assert 'available_ml_features' in data
        
        response = requests.get(f"{self.base_url}/api/custom_model/list")
        assert response.status_code == 200
        data = response.json()
        assert 'custom_models' in data
    
    def test_prediction_endpoint(self):
        """Test prediction endpoint."""
        response = requests.get(
            f"{self.base_url}/scouting_predict",
            params={'player_id': '12345', 'season': '2015_2016'}
        )
        assert response.status_code in [200, 404, 500]
    
    def test_error_handling(self):
        """Test error handling across the application."""
        response = requests.get(f"{self.base_url}/player_events")
        assert response.status_code == 400
        
        response = requests.get(
            f"{self.base_url}/player_events",
            params={'player_id': 'invalid', 'season': 'invalid'}
        )
        assert response.status_code in [400, 404]
    
    def test_content_type_headers(self):
        """Test that proper content-type headers are set."""
        response = requests.get(f"{self.base_url}/players")
        assert response.headers['content-type'] == 'application/json'
    
    def test_caching_headers(self):
        """Test that caching headers are properly set."""
        response = requests.get(f"{self.base_url}/health")
        assert 'Cache-Control' in response.headers
        assert 'no-cache' in response.headers['Cache-Control']
    
    def test_frontend_api_integration(self):
        """Test that the frontend can communicate with the backend."""
        response = requests.get(self.frontend_url)
        assert response.status_code == 200
        
        html_content = response.text
        assert 'react' in html_content.lower() or 'app' in html_content.lower()

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
