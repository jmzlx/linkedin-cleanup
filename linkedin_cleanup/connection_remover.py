"""
Connection Remover - Utilities for removing LinkedIn connections.
"""
from typing import Optional, Tuple

from linkedin_cleanup import config
from linkedin_cleanup.linkedin_client import LinkedInClient
from linkedin_cleanup.random_actions import random_delay


class ConnectionRemover:
    """Handles removal of LinkedIn connections."""
    
    def __init__(self, client: LinkedInClient):
        """Initialize with a LinkedIn client."""
        self.client = client
    
    async def _find_more_button(self) -> Optional[object]:
        """Find the 'More' button (three dots) in the profile section."""
        page = self.client.page
        for selector in config.MORE_BUTTON_SELECTORS:
            try:
                button = page.locator(selector).first
                if await button.is_visible(timeout=config.SHORT_SELECTOR_TIMEOUT):
                    return button
            except Exception:
                continue
        return None
    
    async def _find_remove_connection_option(self) -> Optional[object]:
        """Find the 'Remove connection' option in the dropdown menu."""
        page = self.client.page
        try:
            locator = page.locator(config.REMOVE_CONNECTION_SELECTOR)
            if await locator.count() > 0:
                return locator.first
        except Exception:
            pass
        return None
    
    async def check_connection_status(self, url: str) -> str:
        """Check if we are connected to a profile. Returns: 'connected', 'not_connected', or 'unknown'."""
        page = self.client.page
        try:
            await self.client.navigate_to(url)
            
            if await self._find_more_button():
                return "connected"
            
            try:
                connect_button = page.locator(config.CONNECT_BUTTON_SELECTOR).first
                if await connect_button.is_visible(timeout=config.SHORT_SELECTOR_TIMEOUT):
                    if "Connect" in await connect_button.inner_text():
                        return "not_connected"
            except Exception:
                pass
            
            return "unknown"
        
        except Exception:
            return "unknown"
    
    async def disconnect_connection(
        self,
        url: str,
        dry_run: bool = False
    ) -> Tuple[bool, str]:
        """Disconnect from a LinkedIn connection. Returns (success, message)."""
        page = self.client.page
        try:
            await self.client.navigate_to(url)
            
            more_button = await self._find_more_button()
            if not more_button:
                return False, "Could not find 'More' button"
            
            await self.client.human_like_click(more_button)
            
            try:
                await page.wait_for_selector(
                    config.DROPDOWN_CONTENT_SELECTOR,
                    timeout=config.VERIFICATION_TIMEOUT
                )
            except Exception:
                pass
            
            await random_delay()
            
            remove_option = await self._find_remove_connection_option()
            if not remove_option:
                await page.keyboard.press("Escape")
                await random_delay()
                return False, "Could not find 'Remove connection' option"
            
            if dry_run:
                await page.keyboard.press("Escape")
                return True, "[DRY RUN] Successfully found all selectors - would remove connection"
            
            await remove_option.scroll_into_view_if_needed()
            
            try:
                await remove_option.click(force=True)
            except Exception:
                await page.evaluate(
                    "arguments[0].click();",
                    await remove_option.element_handle()
                )
            
            await random_delay()
            await self.client.close_new_tabs(keep_url_pattern="linkedin.com/in/")
            await self.client.navigate_to(url)
            
            connect_button = page.locator(config.CONNECT_BUTTON_SELECTOR).first
            connect_visible = await connect_button.is_visible(
                timeout=config.VERIFICATION_TIMEOUT
            )
            
            more_button_after = await self._find_more_button()
            
            if connect_visible:
                try:
                    if "Connect" in await connect_button.inner_text():
                        return True, "Successfully removed"
                except Exception:
                    pass
            
            if not more_button_after:
                return True, "Successfully removed"
            
            return False, "Removal verification failed"
        
        except Exception as e:
            return False, f"Error: {str(e)}"

