"""
Tests for connection removal functionality.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from linkedin_cleanup import connection_remover


@pytest.mark.asyncio
async def test_remove_connection_dry_run(mock_client):
    """Test dry run removal - identifies More and Remove connection selectors."""
    # Setup: Mock successful finding of More button and Remove option
    mock_more_button = AsyncMock()
    mock_more_button.is_visible = AsyncMock(return_value=True)
    mock_more_locator = MagicMock()
    mock_more_locator.first = mock_more_button
    
    # Mock Remove connection option
    mock_remove_option = AsyncMock()
    mock_remove_option.get_attribute = AsyncMock(return_value="Remove your connection")
    mock_remove_locator = AsyncMock()
    mock_remove_locator.count = AsyncMock(return_value=1)
    mock_remove_locator.first = mock_remove_option
    
    # Setup locator to return different mocks for different selectors
    def locator_side_effect(selector):
        if "More" in selector or "artdeco-dropdown__trigger" in selector:
            return mock_more_locator
        elif "Remove" in selector:
            return mock_remove_locator
        return mock_more_locator
    
    mock_client.page.locator.side_effect = locator_side_effect
    
    # Execute
    success, message = await connection_remover.remove_connection(
        mock_client, "https://www.linkedin.com/in/test-profile", dry_run=True
    )
    
    # Verify
    assert success is True
    assert "[DRY RUN]" in message
    assert "Successfully found all selectors" in message
    mock_client.navigate_to.assert_called()
    mock_client.human_like_click.assert_called()
    mock_client.page.keyboard.press.assert_called_with("Escape")


@pytest.mark.asyncio
async def test_check_profile_connection_status(mock_client):
    """Test checking if a profile is connected or not."""
    # Setup: Profile is connected (More button exists)
    mock_more_button = AsyncMock()
    mock_more_button.is_visible = AsyncMock(return_value=True)
    mock_locator = MagicMock()
    mock_locator.first = mock_more_button
    mock_client.page.locator.return_value = mock_locator
    
    # Execute: Check if connected
    result = await connection_remover.find_more_button(mock_client)
    assert result is not None  # Connected
    
    # Setup: Profile is not connected (More button doesn't exist)
    mock_more_button.is_visible = AsyncMock(return_value=False)
    
    # Execute: Check if connected
    result = await connection_remover.find_more_button(mock_client)
    assert result is None  # Not connected
