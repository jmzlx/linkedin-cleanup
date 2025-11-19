"""
Tests for configuration and environment variable support.
"""

import pytest

from linkedin_cleanup import config


def test_config_has_required_constants():
    """Test that config module has all required constants."""
    assert hasattr(config, "EXTRACTION_DELAY_MIN")
    assert hasattr(config, "EXTRACTION_DELAY_MAX")
    assert hasattr(config, "REMOVAL_DELAY_MIN")
    assert hasattr(config, "REMOVAL_DELAY_MAX")
    assert hasattr(config, "BROWSER_HEADLESS")
    assert hasattr(config, "MAX_PAGES")
    assert hasattr(config, "RANDOM_ACTION_PROBABILITY")


def test_config_delays_are_positive():
    """Test that delay values are positive."""
    assert config.EXTRACTION_DELAY_MIN > 0
    assert config.EXTRACTION_DELAY_MAX > 0
    assert config.REMOVAL_DELAY_MIN > 0
    assert config.REMOVAL_DELAY_MAX > 0
    assert config.PAGE_DELAY_MIN > 0
    assert config.PAGE_DELAY_MAX > 0


def test_config_min_max_relationships():
    """Test that min values are <= max values."""
    assert config.EXTRACTION_DELAY_MIN <= config.EXTRACTION_DELAY_MAX
    assert config.PAGE_DELAY_MIN <= config.PAGE_DELAY_MAX
    assert config.REMOVAL_DELAY_MIN <= config.REMOVAL_DELAY_MAX


def test_config_probability_range():
    """Test that random action probability is in valid range."""
    assert 0.0 <= config.RANDOM_ACTION_PROBABILITY <= 1.0


def test_config_timeouts_are_positive():
    """Test that timeout values are positive."""
    assert config.NAVIGATION_TIMEOUT > 0
    assert config.SELECTOR_TIMEOUT > 0
    assert config.SHORT_SELECTOR_TIMEOUT > 0
    assert config.VERIFICATION_TIMEOUT > 0


def test_config_file_paths_exist():
    """Test that file path constants are defined."""
    assert hasattr(config, "COOKIES_FILE")
    assert hasattr(config, "PROGRESS_FILE")
    assert hasattr(config, "OUTPUT_CSV")
    assert hasattr(config, "DEFAULT_OUTPUT_CSV")


def test_env_var_override_delay(monkeypatch):
    """Test that environment variables can override delay values."""
    # Note: This test may not work perfectly since config is imported at module level
    # But it verifies the helper functions work correctly
    from linkedin_cleanup.config import _get_env_float

    monkeypatch.setenv("TEST_DELAY", "5.5")
    value = _get_env_float("TEST_DELAY", 2.0, min_value=0.0)
    assert value == 5.5


def test_env_var_validation_rejects_negative(monkeypatch):
    """Test that environment variable validation rejects negative values."""
    from linkedin_cleanup.config import _get_env_float

    monkeypatch.setenv("TEST_DELAY", "-5.0")
    with pytest.raises(ValueError, match="must be >="):
        _get_env_float("TEST_DELAY", 2.0, min_value=0.0)


def test_env_var_validation_rejects_invalid_format(monkeypatch):
    """Test that environment variable validation rejects invalid formats."""
    from linkedin_cleanup.config import _get_env_float

    monkeypatch.setenv("TEST_DELAY", "not_a_number")
    with pytest.raises(ValueError):
        _get_env_float("TEST_DELAY", 2.0, min_value=0.0)
