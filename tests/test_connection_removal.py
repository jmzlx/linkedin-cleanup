"""
Tests for connection removal functionality.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from linkedin_cleanup.connection_remover import ConnectionRemover
from linkedin_cleanup.constants import ConnectionStatus


@pytest.mark.asyncio
async def test_check_connection_status_connected(mock_client):
    """Test checking connection status when connected (More button exists)."""
    # Setup: Profile is connected (More button exists)
    mock_more_button = AsyncMock()
    mock_more_button.is_visible = AsyncMock(return_value=True)
    mock_more_locator = MagicMock()
    mock_more_locator.first = mock_more_button

    def locator_side_effect(selector):
        if "More" in selector or "artdeco-dropdown__trigger" in selector:
            return mock_more_locator
        return mock_more_locator

    mock_client.page.locator.side_effect = locator_side_effect

    # Execute
    remover = ConnectionRemover(mock_client)
    status = await remover.check_connection_status("https://www.linkedin.com/in/test-profile")

    # Verify
    assert status == ConnectionStatus.CONNECTED
    mock_client.navigate_to.assert_called()


@pytest.mark.asyncio
async def test_check_connection_status_not_connected(mock_client):
    """Test checking connection status when not connected (Connect button exists)."""
    # Setup: Profile is not connected (More button doesn't exist, Connect button does)
    mock_more_button = AsyncMock()
    mock_more_button.is_visible = AsyncMock(return_value=False)
    mock_more_locator = MagicMock()
    mock_more_locator.first = mock_more_button

    mock_connect_button = AsyncMock()
    mock_connect_button.is_visible = AsyncMock(return_value=True)
    mock_connect_button.inner_text = AsyncMock(return_value="Connect")
    mock_connect_locator = MagicMock()
    mock_connect_locator.first = mock_connect_button

    def locator_side_effect(selector):
        if "More" in selector or "artdeco-dropdown__trigger" in selector:
            return mock_more_locator
        elif "Connect" in selector:
            return mock_connect_locator
        return mock_more_locator

    mock_client.page.locator.side_effect = locator_side_effect

    # Execute
    remover = ConnectionRemover(mock_client)
    status = await remover.check_connection_status("https://www.linkedin.com/in/test-profile")

    # Verify
    assert status == ConnectionStatus.NOT_CONNECTED
    mock_client.navigate_to.assert_called()


@pytest.mark.asyncio
async def test_check_connection_status_unknown(mock_client):
    """Test checking connection status when status is unknown."""
    # Setup: Neither More nor Connect button found
    mock_more_button = AsyncMock()
    mock_more_button.is_visible = AsyncMock(return_value=False)
    mock_more_locator = MagicMock()
    mock_more_locator.first = mock_more_button

    mock_connect_button = AsyncMock()
    mock_connect_button.is_visible = AsyncMock(return_value=False)
    mock_connect_locator = MagicMock()
    mock_connect_locator.first = mock_connect_button

    def locator_side_effect(selector):
        if "More" in selector or "artdeco-dropdown__trigger" in selector:
            return mock_more_locator
        elif "Connect" in selector:
            return mock_connect_locator
        return mock_more_locator

    mock_client.page.locator.side_effect = locator_side_effect

    # Execute
    remover = ConnectionRemover(mock_client)
    status = await remover.check_connection_status("https://www.linkedin.com/in/test-profile")

    # Verify
    assert status == ConnectionStatus.UNKNOWN
    mock_client.navigate_to.assert_called()


@pytest.mark.asyncio
async def test_disconnect_connection_dry_run(mock_client):
    """Test dry run disconnection - identifies More and Remove connection selectors."""
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
    mock_client.page.wait_for_selector = AsyncMock()
    mock_client.close_new_tabs = AsyncMock()

    # Execute
    remover = ConnectionRemover(mock_client)
    success, message = await remover.disconnect_connection(
        "https://www.linkedin.com/in/test-profile", dry_run=True
    )

    # Verify
    assert success is True
    assert "[DRY RUN]" in message
    assert "Successfully found all selectors" in message
    mock_client.navigate_to.assert_called()
    mock_client.human_like_click.assert_called()
    mock_client.page.keyboard.press.assert_called_with("Escape")


@pytest.mark.asyncio
async def test_find_more_button(mock_client):
    """Test finding the More button helper method."""
    # Setup: Profile is connected (More button exists)
    mock_more_button = AsyncMock()
    mock_more_button.is_visible = AsyncMock(return_value=True)
    mock_locator = MagicMock()
    mock_locator.first = mock_more_button
    mock_client.page.locator.return_value = mock_locator

    # Execute: Check if connected
    remover = ConnectionRemover(mock_client)
    result = await remover._find_more_button()
    assert result is not None  # Connected

    # Setup: Profile is not connected (More button doesn't exist)
    mock_more_button.is_visible = AsyncMock(return_value=False)

    # Execute: Check if connected
    result = await remover._find_more_button()
    assert result is None  # Not connected
