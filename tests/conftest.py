"""
Pytest configuration and shared fixtures.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_page():
    """Create a mock Playwright page object."""
    page = AsyncMock()
    page.url = "https://www.linkedin.com/in/test-profile"
    
    # Mock locator
    locator = AsyncMock()
    page.locator = MagicMock(return_value=locator)
    
    # Mock keyboard
    page.keyboard = AsyncMock()
    page.keyboard.press = AsyncMock()
    
    # Mock mouse
    page.mouse = AsyncMock()
    page.mouse.move = AsyncMock()
    
    # Mock evaluate
    page.evaluate = AsyncMock()
    
    return page


@pytest.fixture
def mock_client(mock_page):
    """Create a mock LinkedInClient."""
    from linkedin_cleanup.linkedin_client import LinkedInClient
    
    client = LinkedInClient()
    client.page = mock_page
    client.context = AsyncMock()
    client.browser = AsyncMock()
    client.playwright = AsyncMock()
    
    # Mock methods
    client.navigate_to = AsyncMock()
    client.human_like_click = AsyncMock()
    
    return client

