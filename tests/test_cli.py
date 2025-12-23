"""Unit tests for the CLI module."""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from m4b_splitter.cli import parse_duration


class TestParseDuration:
    """Tests for the parse_duration function."""
    
    # Hours formats
    def test_parse_hours_integer(self):
        """Test parsing integer hours."""
        assert parse_duration("8") == 8.0
        assert parse_duration("1") == 1.0
        assert parse_duration("24") == 24.0
    
    def test_parse_hours_float(self):
        """Test parsing float hours."""
        assert parse_duration("4.5") == 4.5
        assert parse_duration("2.25") == 2.25
        assert parse_duration("0.5") == 0.5
    
    def test_parse_hours_with_suffix(self):
        """Test parsing hours with 'h' suffix."""
        assert parse_duration("8h") == 8.0
        assert parse_duration("4.5h") == 4.5
        assert parse_duration("1h") == 1.0
    
    def test_parse_hours_uppercase(self):
        """Test parsing hours with uppercase 'H'."""
        assert parse_duration("8H") == 8.0
        assert parse_duration("4.5H") == 4.5
    
    # Minutes formats
    def test_parse_minutes(self):
        """Test parsing minutes."""
        assert parse_duration("60m") == 1.0
        assert parse_duration("90m") == 1.5
        assert parse_duration("120m") == 2.0
        assert parse_duration("30m") == 0.5
    
    def test_parse_minutes_uppercase(self):
        """Test parsing minutes with uppercase 'M'."""
        assert parse_duration("60M") == 1.0
        assert parse_duration("90M") == 1.5
    
    # Combined formats
    def test_parse_combined_hours_minutes(self):
        """Test parsing combined hours and minutes."""
        assert parse_duration("2h30m") == 2.5
        assert parse_duration("1h15m") == 1.25
        assert parse_duration("0h30m") == 0.5
        assert parse_duration("3h45m") == 3.75
    
    def test_parse_combined_uppercase(self):
        """Test parsing combined with uppercase."""
        assert parse_duration("2H30M") == 2.5
    
    def test_parse_combined_hours_zero_minutes(self):
        """Test parsing combined with zero minutes."""
        assert parse_duration("2h0m") == 2.0
    
    # Whitespace handling
    def test_parse_with_whitespace(self):
        """Test parsing with leading/trailing whitespace."""
        assert parse_duration("  8h  ") == 8.0
        assert parse_duration("\t90m\n") == 1.5
    
    # Invalid formats
    def test_parse_invalid_format(self):
        """Test parsing invalid formats raises ValueError."""
        with pytest.raises(ValueError):
            parse_duration("invalid")
    
    def test_parse_empty_string(self):
        """Test parsing empty string raises ValueError."""
        with pytest.raises(ValueError):
            parse_duration("")
    
    def test_parse_only_letters(self):
        """Test parsing only letters raises ValueError."""
        with pytest.raises(ValueError):
            parse_duration("abc")
    
    def test_parse_invalid_suffix(self):
        """Test parsing with invalid suffix raises ValueError."""
        with pytest.raises(ValueError):
            parse_duration("8x")
    
    def test_parse_negative(self):
        """Test that negative values are handled."""
        result = parse_duration("-8")
        assert result == -8.0


class TestCLIHelpers:
    """Additional CLI helper tests."""
    
    def test_parse_duration_real_world_examples(self):
        """Test parsing real-world duration examples."""
        # Common audiobook split durations
        assert parse_duration("8h") == 8.0      # Default
        assert parse_duration("4h") == 4.0      # Half
        assert parse_duration("2h") == 2.0      # CD length
        assert parse_duration("1h30m") == 1.5   # 90 minutes
        assert parse_duration("45m") == 0.75    # Short
    
    def test_parse_small_durations(self):
        """Test parsing small durations for testing."""
        assert parse_duration("1m") == pytest.approx(1/60, abs=0.001)
        assert parse_duration("5m") == pytest.approx(5/60, abs=0.001)
        assert parse_duration("0h5m") == pytest.approx(5/60, abs=0.001)


class TestCLIImports:
    """Test that CLI imports work correctly."""
    
    def test_rich_available_detection(self):
        """Test that RICH_AVAILABLE is properly set."""
        from m4b_splitter.cli import RICH_AVAILABLE
        # Should be boolean
        assert isinstance(RICH_AVAILABLE, bool)
    
    def test_app_exists(self):
        """Test that app is defined."""
        from m4b_splitter.cli import app
        assert app is not None
        assert callable(app)
