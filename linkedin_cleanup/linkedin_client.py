"""
LinkedIn Client - Core browser automation functionality.
Shared client for all LinkedIn automation tasks.
"""
import asyncio
import json
from pathlib import Path
from typing import List, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from linkedin_cleanup import config
from linkedin_cleanup.random_actions import random_delay
from linkedin_cleanup.utils import print_banner

# HTTP error messages mapping
HTTP_ERROR_MESSAGES = {
    403: " - Access forbidden (may be rate limited or blocked)",
    429: " - Rate limited (too many requests)",
    500: " - Server error",
    503: " - Service unavailable",
}


class LinkedInClient:
    """Core LinkedIn browser automation client."""
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    def load_cookies(self) -> Optional[List[dict]]:
        """Load saved cookies if they exist."""
        path = Path(config.COOKIES_FILE)
        if path.exists():
            return json.loads(path.read_text())
        return None
    
    def save_cookies(self, cookies: List[dict]):
        """Save cookies to file."""
        path = Path(config.COOKIES_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cookies, indent=2))
    
    async def human_like_click(self, element):
        """Perform a click. Playwright's click() already simulates human behavior."""
        await element.click()
    
    async def navigate_to(self, url: str):
        """Navigate to a URL with timeout handling."""
        try:
            response = await self.page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000
            )
            
            if response and response.status >= 400:
                error_msg = f"HTTP {response.status} error when accessing {url}"
                error_msg += HTTP_ERROR_MESSAGES.get(response.status, "")
                print(f"\n❌ {error_msg}")
                raise SystemExit(1)
        except SystemExit:
            raise
        except Exception:
            if "linkedin.com" not in self.page.url:
                print("⚠ Navigation timeout")
        
        try:
            await self.page.wait_for_load_state("load", timeout=15000)
        except Exception:
            pass
        
        await random_delay()
    
    async def is_logged_in(self) -> bool:
        """Check if we're logged in by looking for logged-in page indicators."""
        try:
            url = self.page.url
            if "linkedin.com/login" in url or "linkedin.com/uas/login" in url:
                return False
            
            indicators = [
                'nav[aria-label="Main navigation"]',
                'header[data-test-id="global-nav"]',
                'div[data-test-id="feed-container"]',
                'main[role="main"]',
            ]
            
            for selector in indicators:
                try:
                    if await self.page.locator(selector).first.count() > 0:
                        return True
                except Exception:
                    continue
            
            return (
                "linkedin.com/feed" in url
                or ("linkedin.com/in/" in url and "login" not in url)
                or "linkedin.com/search" in url
            )
        except Exception:
            return False
    
    async def _safe_close(self, resource, close_method):
        """Safely close a resource, ignoring any exceptions."""
        if resource and close_method:
            try:
                await close_method()
            except Exception:
                pass
    
    async def setup_browser(self):
        """Set up browser with stealth settings."""
        if self.browser and self.browser.is_connected():
            return
        
        if self.browser:
            await self._safe_close(self.browser, self.browser.close)
        if self.playwright:
            await self._safe_close(self.playwright, self.playwright.stop)
        
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(
            headless=config.BROWSER_HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={
                "width": config.BROWSER_VIEWPORT_WIDTH,
                "height": config.BROWSER_VIEWPORT_HEIGHT
            },
            user_agent=config.USER_AGENT,
            locale=config.BROWSER_LOCALE,
        )
        
        if cookies := self.load_cookies():
            await self.context.add_cookies(cookies)
        
        self.page = await self.context.new_page()
        
        async def handle_new_page(new_page):
            try:
                await new_page.wait_for_load_state("domcontentloaded", timeout=2000)
                if "linkedin.com/jobs" in new_page.url:
                    await new_page.close()
            except Exception:
                pass
        
        self.context.on("page", handle_new_page)
        
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
    
    async def ensure_logged_in(self) -> bool:
        """Check if we're logged in and handle login if needed."""
        await self.navigate_to(config.LINKEDIN_FEED_URL)
        
        if await self.is_logged_in():
            self.save_cookies(await self.context.cookies())
            return True
        
        print_banner("MANUAL LOGIN REQUIRED")
        print("Please log in to LinkedIn in the browser window.")
        print("Waiting for login (timeout: 5 minutes)...")
        
        max_wait_time = 300
        check_interval = 2
        elapsed = 0
        
        while elapsed < max_wait_time:
            await asyncio.sleep(check_interval)
            elapsed += check_interval
            
            if elapsed % 10 == 0:
                await self.navigate_to(config.LINKEDIN_FEED_URL)
            
            if await self.is_logged_in():
                self.save_cookies(await self.context.cookies())
                print(f"✓ Login successful ({elapsed}s)")
                return True
            
            if elapsed % 10 == 0:
                print(f"Waiting... ({elapsed}/{max_wait_time}s)")
        
        print(f"❌ Login timeout after {max_wait_time}s")
        return False
    
    async def close_new_tabs(self, keep_url_pattern: str = None):
        """Close any new tabs that were opened, keeping only the main page."""
        if not self.context or len(self.context.pages) <= 1:
            return
        
        main_page = self.page
        for page in self.context.pages:
            if page == main_page:
                continue
            if keep_url_pattern and keep_url_pattern in page.url:
                continue
            await page.close()
        
        if self.page.is_closed() and self.context.pages:
            self.page = self.context.pages[0]
    
    async def close(self):
        """Close browser and cleanup resources."""
        if self.browser:
            await self._safe_close(self.browser, self.browser.close)
        self.browser = None
        if self.playwright:
            await self._safe_close(self.playwright, self.playwright.stop)
        self.playwright = None
        self.context = None
        self.page = None

