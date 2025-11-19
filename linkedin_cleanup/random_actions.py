"""Human-like behaviors to prevent automation detection."""

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from linkedin_cleanup import config

if TYPE_CHECKING:
    from linkedin_cleanup.linkedin_client import LinkedInClient

logger = logging.getLogger(__name__)


async def random_delay(min_sec: float | None = None, max_sec: float | None = None):
    """Random delay to mimic human behavior."""
    await asyncio.sleep(
        random.uniform(
            min_sec or config.EXTRACTION_DELAY_MIN, max_sec or config.EXTRACTION_DELAY_MAX
        )
    )


async def _try_click_element(page, selectors: list[str], timeout: int = 3000) -> bool:
    """Try to find and click an element using a list of selectors."""
    for selector in selectors:
        try:
            element = page.locator(selector).first
            if await element.is_visible(timeout=timeout):
                await element.click()
                return True
        except (PlaywrightTimeoutError, AttributeError) as e:
            logger.debug(f"Failed to click element with selector {selector}: {e}")
            continue
    return False


async def action_click_logo_and_open_comments(client: "LinkedInClient") -> bool:
    """Click LinkedIn logo to go to home page, then open comments for the first post."""
    page = client.page
    try:
        await client.navigate_to("https://www.linkedin.com/feed")
        await random_delay()

        comment_selectors = [
            'button[aria-label="Comment"]',
            'button[aria-label*="Comment"]:not([aria-label*="comments"])',
        ]

        if not await _try_click_element(page, comment_selectors, timeout=5000):
            return False

        await random_delay()
        return True

    except Exception as e:
        logger.debug(f"Error in action_click_logo_and_open_comments: {e}")
        return False


async def action_open_messages_and_click_conversation(client: "LinkedInClient") -> bool:
    """Click messages icon, scroll inbox, and click on a message."""
    page = client.page
    try:
        messages_selectors = ['a[href*="messaging"]', 'nav a[href*="messaging"]']
        if not await _try_click_element(page, messages_selectors, timeout=3000):
            await client.navigate_to("https://www.linkedin.com/messaging")

        await random_delay()

        scroll_selectors = ['div[role="listbox"]', 'div[class*="conversation-list"]']
        scroll_container = None
        for selector in scroll_selectors:
            try:
                container = page.locator(selector).first
                if await container.is_visible(timeout=3000):
                    scroll_container = container
                    break
            except (PlaywrightTimeoutError, AttributeError):
                continue

        scroll_amount = random.randint(200, 500)
        target = scroll_container if scroll_container else page
        await target.evaluate(f"element => element.scrollBy(0, {scroll_amount})")

        await random_delay()

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
                        await random_delay()
                        return True
            except (PlaywrightTimeoutError, AttributeError):
                continue

        return False

    except Exception as e:
        logger.debug(f"Error in action_open_messages_and_click_conversation: {e}")
        return False


async def action_click_jobs_and_open_first_job(client: "LinkedInClient") -> bool:
    """Click jobs menu item and open the first job by clicking on its title."""
    page = client.page
    try:
        jobs_selectors = ['a[href*="/jobs"]', 'nav a[href*="/jobs"]']
        if not await _try_click_element(page, jobs_selectors, timeout=3000):
            await client.navigate_to("https://www.linkedin.com/jobs")

        await random_delay()

        job_selectors = ['a[href*="/jobs/view/"]', 'a[href*="/jobs/collections/"]']
        for selector in job_selectors:
            try:
                job = page.locator(selector).first
                if await job.is_visible(timeout=3000):
                    await job.click()
                    await random_delay()
                    return True
            except (PlaywrightTimeoutError, AttributeError):
                continue

        return False

    except Exception as e:
        logger.debug(f"Error in action_click_jobs_and_open_first_job: {e}")
        return False


# List of available random actions
AVAILABLE_ACTIONS: list[Callable[["LinkedInClient"], Awaitable[bool]]] = [
    action_click_logo_and_open_comments,
    action_open_messages_and_click_conversation,
    action_click_jobs_and_open_first_job,
]


async def perform_random_action(client: "LinkedInClient", new_tab: bool = False) -> bool:
    """Perform a random action from the available actions list based on configured probability."""
    if random.random() > config.RANDOM_ACTION_PROBABILITY:
        return False

    if not AVAILABLE_ACTIONS:
        return False

    action = random.choice(AVAILABLE_ACTIONS)
    original_page = client.page if new_tab else None
    new_page = None

    try:
        if new_tab and client.context:
            new_page = await client.context.new_page()
            client.page = new_page

        return await action(client)

    except Exception as e:
        logger.debug(f"Error performing random action: {e}")
        return False
    finally:
        if new_tab and original_page:
            client.page = original_page
            if new_page and not new_page.is_closed():
                try:
                    await new_page.close()
                except Exception as e:
                    logger.debug(f"Error closing new page: {e}")
