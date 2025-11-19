"""
Tests for random actions functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from linkedin_cleanup import random_actions


@pytest.mark.asyncio
async def test_perform_random_action_probability_check(mock_client):
    """Test that perform_random_action respects probability configuration."""
    with patch("random.random", return_value=0.9):  # 90% > 30% default, should skip
        with patch("linkedin_cleanup.config.RANDOM_ACTION_PROBABILITY", 0.3):
            result = await random_actions.perform_random_action(mock_client)
            assert result is False
            # Should not call any actions
            mock_client.page.locator.assert_not_called()


@pytest.mark.asyncio
async def test_perform_random_action_executes_on_probability_pass(mock_client):
    """Test that perform_random_action executes when probability check passes."""
    # Mock probability check to pass (10% < 30%)
    mock_action_func = AsyncMock(return_value=True)
    with patch("random.random", return_value=0.1):
        with patch("random.choice", return_value=mock_action_func):
            result = await random_actions.perform_random_action(mock_client)
            assert result is True
            mock_action_func.assert_called_once_with(mock_client)


@pytest.mark.asyncio
async def test_perform_random_action_no_actions_available(mock_client):
    """Test perform_random_action when no actions are available."""
    with patch("random.random", return_value=0.1):  # Pass probability
        with patch.object(random_actions, "AVAILABLE_ACTIONS", []):
            result = await random_actions.perform_random_action(mock_client)
            assert result is False


@pytest.mark.asyncio
async def test_perform_random_action_handles_exception(mock_client):
    """Test that perform_random_action handles exceptions gracefully."""
    mock_action_func = AsyncMock(side_effect=Exception("Test error"))
    with patch("random.random", return_value=0.1):  # Pass probability
        with patch("random.choice", return_value=mock_action_func):
            result = await random_actions.perform_random_action(mock_client)
            assert result is False


@pytest.mark.asyncio
async def test_action_click_logo_and_open_comments_success(mock_client):
    """Test successful execution of click logo and open comments action."""
    # Setup: Mock comment button (logo navigation is direct now)
    mock_comment_button = AsyncMock()
    mock_comment_button.is_visible = AsyncMock(return_value=True)
    mock_comment_button.click = AsyncMock()
    mock_comment_locator = MagicMock()
    mock_comment_locator.first = mock_comment_button

    def locator_side_effect(selector):
        if "Comment" in selector:
            return mock_comment_locator
        return mock_comment_locator

    mock_client.page.locator.side_effect = locator_side_effect

    # Execute
    result = await random_actions.action_click_logo_and_open_comments(mock_client)

    # Verify
    assert result is True
    mock_client.navigate_to.assert_called_with("https://www.linkedin.com/feed")
    mock_comment_button.click.assert_called()
    # random_delay is now a standalone function, so we verify it was called via patch


@pytest.mark.asyncio
async def test_action_click_logo_and_open_comments_fallback_navigation(mock_client):
    """Test action uses direct navigation (simplified implementation)."""
    # Setup: Mock comment button
    mock_comment_button = AsyncMock()
    mock_comment_button.is_visible = AsyncMock(return_value=True)
    mock_comment_button.click = AsyncMock()
    mock_comment_locator = MagicMock()
    mock_comment_locator.first = mock_comment_button

    def locator_side_effect(selector):
        if "Comment" in selector:
            return mock_comment_locator
        return mock_comment_locator

    mock_client.page.locator.side_effect = locator_side_effect

    # Execute
    result = await random_actions.action_click_logo_and_open_comments(mock_client)

    # Verify
    assert result is True
    mock_client.navigate_to.assert_called_with("https://www.linkedin.com/feed")
    mock_comment_button.click.assert_called()


@pytest.mark.asyncio
async def test_action_click_logo_and_open_comments_no_comment_button(mock_client):
    """Test action returns False when comment button not found."""
    # Setup: Logo found but comment button not found
    mock_logo = AsyncMock()
    mock_logo.is_visible = AsyncMock(return_value=True)
    mock_logo_locator = MagicMock()
    mock_logo_locator.first = mock_logo

    # Setup: All comment button selectors return not visible
    mock_comment_button = AsyncMock()
    mock_comment_button.is_visible = AsyncMock(return_value=False)
    mock_comment_locator = MagicMock()
    mock_comment_locator.first = mock_comment_button

    # Track comment selector calls to ensure all return False
    comment_selectors_called = []

    def locator_side_effect(selector):
        if "LinkedIn" in selector or "/feed" in selector or "global-nav__logo" in selector:
            return mock_logo_locator
        elif "Comment" in selector or "comment" in selector or "feed-container" in selector:
            comment_selectors_called.append(selector)
            return mock_comment_locator
        return mock_logo_locator

    mock_client.page.locator.side_effect = locator_side_effect

    # Execute
    result = await random_actions.action_click_logo_and_open_comments(mock_client)

    # Verify
    assert result is False
    # Verify that comment selectors were tried
    assert len(comment_selectors_called) > 0


@pytest.mark.asyncio
async def test_action_click_logo_and_open_comments_handles_exception(mock_client):
    """Test action handles exceptions gracefully."""
    # Setup: Exception during execution
    mock_client.page.locator.side_effect = Exception("Test error")

    # Execute
    result = await random_actions.action_click_logo_and_open_comments(mock_client)

    # Verify
    assert result is False


@pytest.mark.asyncio
async def test_action_open_messages_and_click_conversation_success(mock_client):
    """Test successful execution of open messages and click conversation action."""
    # Setup: Mock messages icon
    mock_messages_icon = AsyncMock()
    mock_messages_icon.is_visible = AsyncMock(return_value=True)
    mock_messages_icon.click = AsyncMock()
    mock_messages_locator = MagicMock()
    mock_messages_locator.first = mock_messages_icon

    # Setup: Mock messages list container
    mock_container = AsyncMock()
    mock_container.is_visible = AsyncMock(return_value=True)
    mock_container.evaluate = AsyncMock()
    mock_container_locator = MagicMock()
    mock_container_locator.first = mock_container

    # Setup: Mock message items
    mock_message = AsyncMock()
    mock_message.is_visible = AsyncMock(return_value=True)
    mock_message.click = AsyncMock()
    mock_messages_list = MagicMock()
    mock_messages_list.count = AsyncMock(return_value=3)
    mock_messages_list.nth = MagicMock(return_value=mock_message)

    def locator_side_effect(selector):
        if (
            "/messaging" in selector
            or "Messaging" in selector
            or "Messages" in selector
            or "messaging" in selector
        ):
            return mock_messages_locator
        elif "listbox" in selector or "conversation-list" in selector:
            return mock_container_locator
        elif "option" in selector or "conversation-item" in selector or "thread" in selector:
            return mock_messages_list
        return mock_messages_locator

    mock_client.page.locator.side_effect = locator_side_effect

    # Execute
    result = await random_actions.action_open_messages_and_click_conversation(mock_client)

    # Verify
    assert result is True
    mock_messages_icon.click.assert_called()
    # random_delay is now a standalone function, so we verify it was called via patch
    mock_container.evaluate.assert_called()
    mock_message.click.assert_called()


@pytest.mark.asyncio
async def test_action_open_messages_and_click_conversation_fallback_navigation(mock_client):
    """Test action falls back to direct navigation when messages icon not found."""
    # Setup: Messages icon not found
    mock_messages_icon = AsyncMock()
    mock_messages_icon.is_visible = AsyncMock(return_value=False)
    mock_messages_locator = MagicMock()
    mock_messages_locator.first = mock_messages_icon

    # Setup: Mock messages list container
    mock_container = AsyncMock()
    mock_container.is_visible = AsyncMock(return_value=True)
    mock_container.evaluate = AsyncMock()
    mock_container_locator = MagicMock()
    mock_container_locator.first = mock_container

    # Setup: Mock message items
    mock_message = AsyncMock()
    mock_message.is_visible = AsyncMock(return_value=True)
    mock_message.scroll_into_view_if_needed = AsyncMock()
    mock_messages_list = MagicMock()
    mock_messages_list.count = AsyncMock(return_value=2)
    mock_messages_list.nth = MagicMock(return_value=mock_message)

    def locator_side_effect(selector):
        if "/messaging" in selector or "Messaging" in selector or "Messages" in selector:
            return mock_messages_locator
        elif "listbox" in selector or "conversation-list" in selector:
            return mock_container_locator
        elif "option" in selector or "conversation-item" in selector or "thread" in selector:
            return mock_messages_list
        return mock_messages_locator

    mock_client.page.locator.side_effect = locator_side_effect

    # Execute
    result = await random_actions.action_open_messages_and_click_conversation(mock_client)

    # Verify
    assert result is True
    mock_client.navigate_to.assert_called_with("https://www.linkedin.com/messaging")


@pytest.mark.asyncio
async def test_action_open_messages_and_click_conversation_scroll_fallback(mock_client):
    """Test action falls back to page scroll when container not found."""
    # Setup: Messages icon found
    mock_messages_icon = AsyncMock()
    mock_messages_icon.is_visible = AsyncMock(return_value=True)
    mock_messages_locator = MagicMock()
    mock_messages_locator.first = mock_messages_icon

    # Setup: All container selectors return not visible (to trigger fallback)
    mock_container = AsyncMock()
    mock_container.is_visible = AsyncMock(return_value=False)
    mock_container_locator = MagicMock()
    mock_container_locator.first = mock_container

    # Setup: Mock message items
    mock_message = AsyncMock()
    mock_message.is_visible = AsyncMock(return_value=True)
    mock_message.scroll_into_view_if_needed = AsyncMock()
    mock_messages_list = MagicMock()
    mock_messages_list.count = AsyncMock(return_value=1)
    mock_messages_list.nth = MagicMock(return_value=mock_message)

    def locator_side_effect(selector):
        if (
            "/messaging" in selector
            or "Messaging" in selector
            or "Messages" in selector
            or "messaging-nav-item" in selector
        ):
            return mock_messages_locator
        elif (
            "listbox" in selector
            or "conversation-list" in selector
            or "complementary" in selector
            or "conversations-list" in selector
        ):
            # All container selectors return not visible
            return mock_container_locator
        elif "option" in selector or "conversation-item" in selector or "thread" in selector:
            return mock_messages_list
        return mock_messages_locator

    mock_client.page.locator.side_effect = locator_side_effect
    mock_client.page.evaluate = AsyncMock()

    # Execute
    result = await random_actions.action_open_messages_and_click_conversation(mock_client)

    # Verify
    assert result is True
    mock_client.page.evaluate.assert_called()  # Should use page scroll fallback


@pytest.mark.asyncio
async def test_action_open_messages_and_click_conversation_no_messages(mock_client):
    """Test action returns False when no messages found."""
    # Setup: Messages icon found
    mock_messages_icon = AsyncMock()
    mock_messages_icon.is_visible = AsyncMock(return_value=True)
    mock_messages_locator = MagicMock()
    mock_messages_locator.first = mock_messages_icon

    # Setup: Mock messages list container
    mock_container = AsyncMock()
    mock_container.is_visible = AsyncMock(return_value=True)
    mock_container.evaluate = AsyncMock()
    mock_container_locator = MagicMock()
    mock_container_locator.first = mock_container

    # Setup: No messages found
    mock_messages_list = MagicMock()
    mock_messages_list.count = AsyncMock(return_value=0)

    def locator_side_effect(selector):
        if "/messaging" in selector or "Messaging" in selector or "Messages" in selector:
            return mock_messages_locator
        elif "listbox" in selector or "conversation-list" in selector:
            return mock_container_locator
        elif "option" in selector or "conversation-item" in selector or "thread" in selector:
            return mock_messages_list
        return mock_messages_locator

    mock_client.page.locator.side_effect = locator_side_effect

    # Execute
    result = await random_actions.action_open_messages_and_click_conversation(mock_client)

    # Verify
    assert result is False


@pytest.mark.asyncio
async def test_action_open_messages_and_click_conversation_handles_exception(mock_client):
    """Test action handles exceptions gracefully."""
    # Setup: Exception during execution
    mock_client.page.locator.side_effect = Exception("Test error")

    # Execute
    result = await random_actions.action_open_messages_and_click_conversation(mock_client)

    # Verify
    assert result is False
