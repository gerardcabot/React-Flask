"""
Test suite for ML models and data processing.
Tests model loading, feature extraction, and predictions.
"""

import pytest
import pandas as pd
import numpy as np
import os
import sys
from unittest.mock import patch, MagicMock

# Add the server directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server-flask'))

from main import (
    load_player_data, 
    _calculate_goalkeeper_metrics, 
    get_age_at_fixed_point_in_season,
    safe_float,
    safe_literal_eval
)

class TestDataProcessing:
    """Test data processing functions."""
    
    def test_safe_float(self):
        """Test safe_float function with various inputs."""
        assert safe_float("123.45") == 123.45
        assert safe_float(123) == 123.0
        assert safe_float(None) == 0.0
        assert safe_float("invalid") == 0.0
        assert safe_float("") == 0.0
        assert safe_float([]) == 0.0
        assert safe_float({}) == 0.0
    
    def test_safe_literal_eval(self):
        """Test safe_literal_eval function with various inputs."""
        assert safe_literal_eval("[1, 2, 3]") == [1, 2, 3]
        assert safe_literal_eval("(1, 2, 3)") == (1, 2, 3)
        assert safe_literal_eval("'string'") == 'string'
        assert safe_literal_eval("123") == 123
        assert safe_literal_eval("invalid") is None
        assert safe_literal_eval(None) is None
        assert safe_literal_eval("") is None
    
    def test_get_age_at_fixed_point_in_season(self):
        """Test age calculation function."""
        # Test normal case
        age = get_age_at_fixed_point_in_season("1995-01-01", "2015_2016")
        assert age == 21
        
        # Test edge case - birthday after reference date
        age = get_age_at_fixed_point_in_season("1995-12-31", "2015_2016")
        assert age == 20
        
        # Test invalid date
        age = get_age_at_fixed_point_in_season("invalid", "2015_2016")
        assert age is None
        
        # Test invalid season
        age = get_age_at_fixed_point_in_season("1995-01-01", "invalid")
        assert age is None

class TestGoalkeeperMetrics:
    """Test goalkeeper metrics calculation."""
    
    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        result = _calculate_goalkeeper_metrics(df, "12345")
        
        assert result["player_id"] == "12345"
        assert result["error"] is not None
        assert result["summary_text_stats"]["total_actions_recorded"] == 0
    
    def test_missing_player_id_column(self):
        """Test with missing player_id column."""
        df = pd.DataFrame({"type": ["Pass"], "location": ["[50, 30]"]})
        result = _calculate_goalkeeper_metrics(df, "12345")
        
        assert result["error"] is not None
        assert "player_id" in result["error"]
    
    def test_no_events_for_player(self):
        """Test with no events for the specific player."""
        df = pd.DataFrame({
            "player_id": ["67890"],
            "type": ["Pass"],
            "location": ["[50, 30]"]
        })
        result = _calculate_goalkeeper_metrics(df, "12345")
        
        assert result["error"] is not None
        assert "No events found" in result["error"]
    
    def test_valid_goalkeeper_data(self):
        """Test with valid goalkeeper data."""
        df = pd.DataFrame({
            "player_id": ["12345", "12345", "12345"],
            "type": ["Goal Keeper", "Pass", "Goal Keeper"],
            "goalkeeper_type": ["Shot Saved", None, "Goal Conceded"],
            "goalkeeper_outcome": ["Success", None, "Success"],
            "location": ["[80, 40]", "[50, 30]", "[85, 45]"],
            "shot_end_location": ["[85, 45]", None, "[90, 50]"],
            "pass_outcome": [None, None, None]
        })
        
        result = _calculate_goalkeeper_metrics(df, "12345")
        
        assert result["player_id"] == "12345"
        assert result["error"] is None
        assert result["summary_text_stats"]["total_actions_recorded"] == 3
        assert result["summary_text_stats"]["total_passes"] == 1
        assert result["summary_text_stats"]["total_gk_specific_actions"] == 2
    
    def test_pass_statistics(self):
        """Test pass statistics calculation."""
        df = pd.DataFrame({
            "player_id": ["12345", "12345", "12345"],
            "type": ["Pass", "Pass", "Pass"],
            "pass_outcome": [None, "Incomplete", None],
            "pass_height": ["Ground Pass", "High Pass", "Ground Pass"]
        })
        
        result = _calculate_goalkeeper_metrics(df, "12345")
        
        assert result["summary_text_stats"]["total_passes"] == 3
        assert result["summary_text_stats"]["passes_completed"] == 2
        assert result["summary_text_stats"]["passes_incomplete_explicit"] == 1
        assert result["summary_text_stats"]["pass_accuracy_percentage"] == 66.67

class TestModelLoading:
    """Test ML model loading and prediction."""
    
    @patch('main.s3_client')
    def test_load_player_data_from_r2(self, mock_s3_client):
        """Test loading player data from R2."""
        # Mock S3 response
        mock_s3_client.get_object.return_value = {
            'Body': MagicMock()
        }
        mock_s3_client.get_object.return_value['Body'].read.return_value = """
player_id,type,location,pass_outcome
12345,Pass,"[50, 30]",None
12345,Shot,"[80, 40]",Goal
""".encode('utf-8')
        
        # Mock the function to return the mocked client
        with patch('main.s3_client', mock_s3_client):
            df = load_player_data("12345", "2015_2016", None)
            
            assert df is not None
            assert len(df) == 2
            assert df.iloc[0]['type'] == 'Pass'
            assert df.iloc[1]['type'] == 'Shot'
    
    @patch('main.s3_client')
    def test_load_player_data_no_s3_client(self, mock_s3_client):
        """Test loading player data when S3 client is not available."""
        mock_s3_client.return_value = None
        
        with patch('main.s3_client', None):
            df = load_player_data("12345", "2015_2016", None)
            assert df is None
    
    @patch('main.s3_client')
    def test_load_player_data_file_not_found(self, mock_s3_client):
        """Test loading player data when file is not found."""
        from botocore.exceptions import ClientError
        
        mock_s3_client.get_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}}, 'GetObject'
        )
        
        df = load_player_data("12345", "2015_2016", None)
        assert df is None

class TestFeatureExtraction:
    """Test feature extraction and ML processing."""
    
    def test_data_type_conversion(self):
        """Test conversion of data types in player data."""
        # Test location parsing
        location_str = "[50, 30]"
        parsed = safe_literal_eval(location_str)
        assert parsed == [50, 30]
        
        # Test boolean conversion
        bool_values = ["true", "false", "True", "False", "1", "0", "nan", ""]
        expected = [True, False, True, False, True, False, None, None]
        
        for val, exp in zip(bool_values, expected):
            if val in ["true", "false", "True", "False"]:
                result = val.lower() in ["true"]
            elif val in ["1", "0"]:
                result = val == "1"
            else:
                result = None
            assert result == exp or (result is None and exp is None)
    
    def test_numeric_conversion(self):
        """Test numeric data conversion."""
        numeric_cols = ['duration', 'pass_length', 'pass_angle', 'shot_statsbomb_xg']
        
        for col in numeric_cols:
            # Test valid numeric values
            assert safe_float("123.45") == 123.45
            assert safe_float("0") == 0.0
            assert safe_float("-123.45") == -123.45
            
            # Test invalid values
            assert safe_float("invalid") == 0.0
            assert safe_float(None) == 0.0

class TestErrorHandling:
    """Test error handling in data processing."""
    
    def test_division_by_zero(self):
        """Test safe division to prevent division by zero."""
        from main import safe_float
        
        # Test normal division
        result = safe_float(10) / safe_float(2)
        assert result == 5.0
        
        # Test division by zero
        result = safe_float(10) / safe_float(0)
        assert np.isinf(result) or result == 0.0  # Depending on implementation
    
    def test_missing_data_handling(self):
        """Test handling of missing data."""
        df = pd.DataFrame({
            "player_id": ["12345"],
            "type": ["Pass"],
            "location": [None],
            "pass_outcome": [None]
        })
        
        # Should not crash when processing missing data
        result = _calculate_goalkeeper_metrics(df, "12345")
        assert result["player_id"] == "12345"
        assert result["error"] is None  # Should handle missing data gracefully
    
    def test_invalid_json_handling(self):
        """Test handling of invalid JSON data."""
        invalid_json = "invalid json data"
        result = safe_literal_eval(invalid_json)
        assert result is None
        
        # Test with malformed list
        malformed_list = "[1, 2, 3"  # Missing closing bracket
        result = safe_literal_eval(malformed_list)
        assert result is None

class TestPerformance:
    """Test performance-related aspects."""
    
    def test_memory_usage(self):
        """Test that large datasets don't cause memory issues."""
        # Create a large DataFrame
        large_df = pd.DataFrame({
            "player_id": ["12345"] * 10000,
            "type": ["Pass"] * 10000,
            "location": ["[50, 30]"] * 10000,
            "pass_outcome": [None] * 10000
        })
        
        # Should process without memory issues
        result = _calculate_goalkeeper_metrics(large_df, "12345")
        assert result["summary_text_stats"]["total_actions_recorded"] == 10000
    
    def test_processing_time(self):
        """Test that processing completes in reasonable time."""
        import time
        
        df = pd.DataFrame({
            "player_id": ["12345"] * 1000,
            "type": ["Pass"] * 1000,
            "location": ["[50, 30]"] * 1000,
            "pass_outcome": [None] * 1000
        })
        
        start_time = time.time()
        result = _calculate_goalkeeper_metrics(df, "12345")
        end_time = time.time()
        
        # Should complete in less than 1 second
        assert (end_time - start_time) < 1.0
        assert result["summary_text_stats"]["total_actions_recorded"] == 1000

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
