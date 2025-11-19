"""
Random Actions - Human-like behaviors to prevent automation detection.

This module provides generic random actions that can be called from anywhere in the project
to help prevent automation detection. Actions are executed based on a configurable probability,
making it safe to call frequently without performance concerns.

Usage:
    from linkedin_cleanup.random_actions import perform_random_action
    
    # After any LinkedIn operation
    await perform_random_action(client)
"""
import random
from typing import Awaitable, Callable, List

from linkedin_cleanup import config
from linkedin_cleanup.linkedin_client import LinkedInClient


async def _try_click_element(page, selectors: List[str], timeout: int = 3000) -> bool:
    """Try to find and click an element using a list of selectors."""
    for selector in selectors:
        try:
            element = page.locator(selector).first
            if await element.is_visible(timeout=timeout):
                await element.click()
                return True
        except Exception:
            continue
    return False


async def action_click_logo_and_open_comments(client: LinkedInClient) -> bool:
    """Click LinkedIn logo to go to home page, then open comments for the first post."""
    page = client.page
    try:
        # Navigate to feed (logo selector rarely works, so just navigate directly)
        await client.navigate_to("https://www.linkedin.com/feed")
        await client.random_delay(2, 4)
        
        # Find and click comment button
        comment_selectors = [
            'button[aria-label="Comment"]',
            'button[aria-label*="Comment"]:not([aria-label*="comments"])',
        ]
        
        if not await _try_click_element(page, comment_selectors, timeout=5000):
            return False
        
        await client.random_delay(1, 2)
        return True
        
    except Exception as e:
        print(f"    ⚠ [Random Action] Error: {str(e)}")
        return False


async def action_open_messages_and_click_conversation(client: LinkedInClient) -> bool:
    """Click messages icon, scroll inbox, and click on a message."""
    page = client.page
    try:
        # Navigate to messages
        messages_selectors = ['a[href*="messaging"]', 'nav a[href*="messaging"]']
        if not await _try_click_element(page, messages_selectors, timeout=3000):
            await client.navigate_to("https://www.linkedin.com/messaging")
        
        await client.random_delay(2, 3)
        
        # Scroll messages list
        scroll_selectors = ['div[role="listbox"]', 'div[class*="conversation-list"]']
        scroll_container = None
        for selector in scroll_selectors:
            try:
                container = page.locator(selector).first
                if await container.is_visible(timeout=3000):
                    scroll_container = container
                    break
            except Exception:
                continue
        
        scroll_amount = random.randint(200, 500)
        if scroll_container:
            await scroll_container.evaluate(f"element => element.scrollBy(0, {scroll_amount})")
        else:
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        
        await client.random_delay(1, 2)
        
        # Click on a random message
        message_selectors = ['div[role="option"]', 'a[href*="/messaging/thread/"]']
        for selector in message_selectors:
            try:
                messages = page.locator(selector)
                count = await messages.count()
                if count > 0:
                    message_index = random.randint(0, min(count - 1, 4))
                    message = messages.nth(message_index)
                    if await message.is_visible(timeout=3000):
                        await message.click()
                        await client.random_delay(1, 2)
                        return True
            except Exception:
                continue
        
        return False
        
    except Exception as e:
        print(f"    ⚠ [Random Action] Error: {str(e)}")
        return False


# List of available random actions
AVAILABLE_ACTIONS: List[Callable[[LinkedInClient], Awaitable[bool]]] = [
    action_click_logo_and_open_comments,
    action_open_messages_and_click_conversation,
]


async def perform_random_action(client: LinkedInClient, new_tab: bool = False) -> bool:
    """
    Perform a random action from the available actions list based on configured probability.
    This function decides internally whether to execute an action based on RANDOM_ACTION_PROBABILITY,
    so it can be called from anywhere in the project without external tracking.
    
    The function will silently return False if the probability check fails (no action executed),
    making it safe to call frequently without performance concerns.
    
    Args:
        client: LinkedInClient instance (must be initialized and logged in)
        new_tab: If True, execute action in a new tab and close it afterward (preserves current page)
        
    Returns:
        True if action was executed and completed successfully, 
        False if no action was executed (probability check failed) or action failed
    """
    # Check probability first - if random check fails, don't execute
    if random.random() > config.RANDOM_ACTION_PROBABILITY:
        return False  # No action this time
    
    if not AVAILABLE_ACTIONS:
        if not new_tab:  # Only print warning in current tab mode
            print("    ⚠ No random actions available")
        return False
    
    # Select a random action
    action = random.choice(AVAILABLE_ACTIONS)
    
    # Store original page if using new tab
    original_page = client.page if new_tab else None
    new_page = None
    
    try:
        # Create new tab if requested
        if new_tab and client.context:
            new_page = await client.context.new_page()
            client.page = new_page
        
        # Execute the action
        return await action(client)
        
    except Exception as e:
        if new_tab:
            print(f"    ⚠ Error executing random action in new tab: {str(e)}")
        else:
            print(f"    ⚠ Error executing random action: {str(e)}")
        return False
    finally:
        # Restore original page and close new tab if needed
        if new_tab and original_page:
            client.page = original_page
            if new_page and not new_page.is_closed():
                try:
                    await new_page.close()
                except Exception:
                    pass

