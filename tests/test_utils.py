"""
Tests for utility functions.
"""
from linkedin_cleanup import search_extractor


def test_normalize_linkedin_url():
    """Test URL normalization."""
    assert search_extractor.normalize_linkedin_url("/in/john-doe") == \
        "https://www.linkedin.com/in/john-doe"
    assert search_extractor.normalize_linkedin_url(
        "/in/jane-smith?param=value"
    ) == "https://www.linkedin.com/in/jane-smith"
    assert search_extractor.normalize_linkedin_url("/not-a-profile") is None


def test_clean_profile_name():
    """Test profile name cleaning."""
    assert search_extractor.clean_profile_name("John Doe") == "John Doe"
    assert search_extractor.clean_profile_name("John Doe • 1st") == "John Doe"
    assert search_extractor.clean_profile_name("John Doe\nEngineer") == "John Doe"
