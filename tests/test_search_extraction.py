"""
Tests for search result extraction functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from linkedin_cleanup.search_extractor import SearchExtractor


@pytest.mark.asyncio
async def test_extract_profiles_from_search_page(mock_client):
    """Test traversing a search page and extracting profile URLs and names."""
    # Setup: Mock page.evaluate() to return profile data structure
    # The function now uses JavaScript evaluation to extract all profiles at once
    mock_profile_data = {
        "profiles": [
            {
                "url": "/in/john-doe",
                "name": "John Doe\nSoftware Engineer",
                "location": "New York, NY",
            },
            {
                "url": "https://www.linkedin.com/in/jane-smith",
                "name": "Jane Smith",
                "location": "London, UK",
            },
            {"url": "/in/alice-brown", "name": "Alice Brown • 1st", "location": "Paris, France"},
        ],
        "stats": {"totalContainers": 3, "finalCount": 3},
    }

    # Mock page methods
    # page.evaluate() is called multiple times - first for scrolling, then for extraction
    async def mock_evaluate(script):
        # If it's the JavaScript extraction script, return profile data
        # The extraction script looks for 'div[data-view-name="people-search-result"]'
        if "querySelector" in script and ("main" in script or "people-search-result" in script):
            return mock_profile_data
        # Otherwise it's a scroll command, return None
        return None

    mock_client.page.url = "https://www.linkedin.com/search/results/people/"
    mock_client.page.wait_for_selector = AsyncMock()
    mock_client.page.evaluate = AsyncMock(side_effect=mock_evaluate)

    # Execute
    with patch("linkedin_cleanup.search_extractor.random_delay", new_callable=AsyncMock):
        extractor = SearchExtractor(mock_client)
        profiles = await extractor.extract_profiles_from_page()

    # Verify
    assert len(profiles) == 3
    assert all(isinstance(p, tuple) and len(p) == 3 for p in profiles)  # (name, url, location)

    # Check URLs are normalized
    urls = [url for _, url, _ in profiles]
    assert any("john-doe" in url for url in urls)
    assert any("jane-smith" in url for url in urls)
    assert any("alice-brown" in url for url in urls)
    assert all(url.startswith("https://www.linkedin.com/in/") for url in urls)

    # Check names are extracted and cleaned
    names = [name for name, _, _ in profiles]
    assert any("John Doe" in name for name in names)
    assert any("Jane Smith" in name for name in names)
    assert any("Alice Brown" in name for name in names)  # Should remove "• 1st"

    # Check locations are included
    locations = [loc for _, _, loc in profiles]
    assert all(loc for loc in locations)  # All should have location


@pytest.mark.asyncio
async def test_pagination_next_page(mock_client):
    """Test using pagination to fetch next page in search results."""
    # Setup: Next button is enabled and clickable
    mock_next_button = AsyncMock()
    mock_next_button.count = AsyncMock(return_value=1)
    mock_next_button.is_enabled = AsyncMock(return_value=True)
    mock_next_button.scroll_into_view_if_needed = AsyncMock()
    mock_next_button.click = AsyncMock()

    mock_locator = MagicMock()
    mock_locator.first = mock_next_button
    mock_client.page.locator.return_value = mock_locator

    # Execute
    with patch(
        "linkedin_cleanup.search_extractor.random_delay", new_callable=AsyncMock
    ) as mock_delay:
        extractor = SearchExtractor(mock_client)
        result = await extractor.go_to_next_page()

    # Verify
    assert result is True
    mock_next_button.scroll_into_view_if_needed.assert_called()
    mock_next_button.click.assert_called()
    mock_delay.assert_called()
