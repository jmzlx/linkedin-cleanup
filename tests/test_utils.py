"""
Tests for utility functions.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from linkedin_cleanup import search_extractor
from linkedin_cleanup.utils import LinkedInClientError, setup_linkedin_client, with_timeout


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


@pytest.mark.asyncio
async def test_with_timeout_terminates_on_timeout():
    """Test that with_timeout terminates script when operation times out."""
    async def slow_operation():
        await asyncio.sleep(2.0)
        return "success"
    
    result = await with_timeout(slow_operation(), timeout=0.1, operation_name="test")
    assert result is None  # Script should terminate on timeout


@pytest.mark.asyncio
async def test_setup_linkedin_client_handles_login_failure(mock_client):
    """Test that setup_linkedin_client raises error and cleans up on login failure."""
    with patch('linkedin_cleanup.linkedin_client.LinkedInClient') as mock_client_class:
        mock_client_class.return_value = mock_client
        mock_client.setup_browser = AsyncMock()
        mock_client.ensure_logged_in = AsyncMock(return_value=False)
        mock_client.close = AsyncMock()
        
        with pytest.raises(LinkedInClientError, match="Failed to log in"):
            async with setup_linkedin_client() as client:
                pass
        
        # Should cleanup browser even on failure
        mock_client.close.assert_called_once()
