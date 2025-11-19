"""
Tests for connection removal functionality.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from linkedin_cleanup.connection_remover import ConnectionRemover
from linkedin_cleanup.constants import ConnectionStatus


@pytest.mark.asyncio
async def test_process_connection_removal_connected_dry_run(mock_client):
    """Test processing connection removal when connected (dry run)."""
    mock_more_button = AsyncMock()
    mock_more_button.is_visible = AsyncMock(return_value=True)
    mock_more_locator = MagicMock()
    mock_more_locator.first = mock_more_button

    mock_remove_option = AsyncMock()
    mock_remove_locator = AsyncMock()
    mock_remove_locator.count = AsyncMock(return_value=1)
    mock_remove_locator.first = mock_remove_option

    def locator_side_effect(selector):
        if "More" in selector or "artdeco-dropdown__trigger" in selector:
            return mock_more_locator
        elif "Remove" in selector:
            return mock_remove_locator
        return mock_more_locator

    mock_client.page.locator.side_effect = locator_side_effect
    mock_client.page.wait_for_selector = AsyncMock()
    mock_client.close_new_tabs = AsyncMock()

    remover = ConnectionRemover(mock_client)
    status, success, message = await remover.process_connection_removal(
        "https://www.linkedin.com/in/test-profile", dry_run=True
    )

    assert status == ConnectionStatus.CONNECTED
    assert success is True
    assert "[DRY RUN]" in message
    mock_client.navigate_to.assert_called_once()
    mock_client.human_like_click.assert_called_once()
    mock_client.page.keyboard.press.assert_called_with("Escape")


@pytest.mark.asyncio
async def test_process_connection_removal_not_connected(mock_client):
    """Test processing connection removal when not connected."""
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

    remover = ConnectionRemover(mock_client)
    status, success, message = await remover.process_connection_removal(
        "https://www.linkedin.com/in/test-profile"
    )

    assert status == ConnectionStatus.NOT_CONNECTED
    assert success is False
    assert "Already not connected" in message
    mock_client.navigate_to.assert_called_once()


@pytest.mark.asyncio
async def test_process_connection_removal_unknown(mock_client):
    """Test processing connection removal when status is unknown."""
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

    remover = ConnectionRemover(mock_client)
    status, success, message = await remover.process_connection_removal(
        "https://www.linkedin.com/in/test-profile"
    )

    assert status == ConnectionStatus.UNKNOWN
    assert success is False
    assert "Could not determine connection status" in message
    mock_client.navigate_to.assert_called_once()


@pytest.mark.asyncio
async def test_process_connection_removal_no_remove_option(mock_client):
    """Test processing connection removal when Remove option is not found."""
    mock_more_button = AsyncMock()
    mock_more_button.is_visible = AsyncMock(return_value=True)
    mock_more_locator = MagicMock()
    mock_more_locator.first = mock_more_button

    mock_remove_locator = AsyncMock()
    mock_remove_locator.count = AsyncMock(return_value=0)

    def locator_side_effect(selector):
        if "More" in selector or "artdeco-dropdown__trigger" in selector:
            return mock_more_locator
        elif "Remove" in selector:
            return mock_remove_locator
        return mock_more_locator

    mock_client.page.locator.side_effect = locator_side_effect
    mock_client.page.wait_for_selector = AsyncMock()

    remover = ConnectionRemover(mock_client)
    status, success, message = await remover.process_connection_removal(
        "https://www.linkedin.com/in/test-profile"
    )

    assert status == ConnectionStatus.CONNECTED
    assert success is False
    assert "Could not find 'Remove connection' option" in message
    mock_client.page.keyboard.press.assert_called_with("Escape")
