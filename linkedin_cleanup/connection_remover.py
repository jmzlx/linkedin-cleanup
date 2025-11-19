"""
Connection Remover - Utilities for removing LinkedIn connections.
"""

import logging

from playwright.async_api import Locator
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from linkedin_cleanup import config
from linkedin_cleanup.constants import ConnectionStatus
from linkedin_cleanup.linkedin_client import LinkedInClient
from linkedin_cleanup.random_actions import random_delay

logger = logging.getLogger(__name__)


class ConnectionRemover:
    """Handles removal of LinkedIn connections."""

    def __init__(self, client: LinkedInClient):
        """Initialize with a LinkedIn client."""
        self.client = client

    async def _find_more_button(self) -> Locator | None:
        """Find the 'More' button (three dots) in the profile section."""
        page = self.client.page
        for selector in config.MORE_BUTTON_SELECTORS:
            try:
                button = page.locator(selector).first
                if await button.is_visible(timeout=config.SHORT_SELECTOR_TIMEOUT):
                    return button
            except (PlaywrightTimeoutError, AttributeError):
                continue
        return None

    async def _find_remove_connection_option(self) -> Locator | None:
        """Find the 'Remove connection' option in the dropdown menu."""
        page = self.client.page
        try:
            locator = page.locator(config.REMOVE_CONNECTION_SELECTOR)
            if await locator.count() > 0:
                return locator.first
        except (PlaywrightTimeoutError, AttributeError):
            pass
        return None

    async def process_connection_removal(
        self, url: str, dry_run: bool = False
    ) -> tuple[ConnectionStatus, bool, str]:
        """Process connection removal with single navigation. Returns (status, success, message)."""
        page = self.client.page
        try:
            await self.client.navigate_to(url)

            more_button = await self._find_more_button()
            if not more_button:
                try:
                    connect_button = page.locator(config.CONNECT_BUTTON_SELECTOR).first
                    if await connect_button.is_visible(timeout=config.SHORT_SELECTOR_TIMEOUT):
                        if "Connect" in await connect_button.inner_text():
                            return ConnectionStatus.NOT_CONNECTED, False, "Already not connected"
                except (PlaywrightTimeoutError, AttributeError):
                    pass
                return ConnectionStatus.UNKNOWN, False, "Could not determine connection status"

            await self.client.human_like_click(more_button)

            try:
                await page.wait_for_selector(
                    config.DROPDOWN_CONTENT_SELECTOR, timeout=config.VERIFICATION_TIMEOUT
                )
            except PlaywrightTimeoutError:
                pass

            await random_delay()

            remove_option = await self._find_remove_connection_option()
            if not remove_option:
                await page.keyboard.press("Escape")
                await random_delay()
                return ConnectionStatus.CONNECTED, False, "Could not find 'Remove connection' option"

            if dry_run:
                await page.keyboard.press("Escape")
                return ConnectionStatus.CONNECTED, True, "[DRY RUN] Successfully found all selectors - would remove connection"

            await remove_option.scroll_into_view_if_needed()

            try:
                await remove_option.click(force=True)
            except (PlaywrightTimeoutError, AttributeError):
                await page.evaluate("arguments[0].click();", await remove_option.element_handle())

            await random_delay()
            await self.client.close_new_tabs(keep_url_pattern="linkedin.com/in/")

            for selector in config.MORE_BUTTON_SELECTORS:
                try:
                    button = page.locator(selector).first
                    await button.wait_for(state="hidden", timeout=config.VERIFICATION_TIMEOUT)
                except PlaywrightTimeoutError:
                    pass

            connect_button = page.locator(config.CONNECT_BUTTON_SELECTOR).first
            if await connect_button.is_visible(timeout=config.VERIFICATION_TIMEOUT):
                try:
                    if "Connect" in await connect_button.inner_text():
                        return ConnectionStatus.CONNECTED, True, "Successfully removed"
                except (PlaywrightTimeoutError, AttributeError):
                    pass

            if not await self._find_more_button():
                return ConnectionStatus.CONNECTED, True, "Successfully removed"

            return ConnectionStatus.CONNECTED, False, "Removal verification failed"

        except Exception as e:
            logger.debug(f"Error processing connection removal: {e}")
            return ConnectionStatus.UNKNOWN, False, f"Error: {str(e)}"
