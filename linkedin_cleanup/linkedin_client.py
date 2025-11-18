"""
LinkedIn Client - Core browser automation functionality.
Shared client for all LinkedIn automation tasks.
"""
import asyncio
import json
import random
from pathlib import Path
from typing import List, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from linkedin_cleanup import config


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
    
    async def random_delay(self, min_sec: float = None, max_sec: float = None):
        """
        Random delay to mimic human behavior.
        Uses default delays from config if not specified.
        """
        if min_sec is None:
            min_sec = config.EXTRACTION_DELAY_MIN
        if max_sec is None:
            max_sec = config.EXTRACTION_DELAY_MAX
        await asyncio.sleep(random.uniform(min_sec, max_sec))
    
    async def human_like_click(self, element):
        """Perform a click. Playwright's click() already simulates human behavior."""
        await element.click()
    
    async def navigate_to(self, url: str):
        """Navigate to a URL with timeout handling."""
        # Use a shorter timeout to prevent getting stuck on pages that never load
        navigation_timeout = 30000  # 30 seconds instead of 60
        try:
            await self.page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=navigation_timeout
            )
        except Exception as e:
            # If navigation times out, check if we're at least on the right domain
            current_url = self.page.url
            if "linkedin.com" not in current_url:
                print(f"  Warning: Navigation timeout, but continuing anyway...")
            pass  # Continue even if timeout
        
        # Wait for page to finish loading (check tab loading state)
        # This prevents the script from getting stuck on pages that never finish loading
        # Use Playwright's wait_for_load_state with a timeout
        try:
            # Wait for "load" state (DOM and resources loaded) with a timeout
            # This handles the tab spinner issue - if the page is stuck loading,
            # this will timeout and we'll continue anyway
            await self.page.wait_for_load_state("load", timeout=15000)  # 15 second timeout
        except Exception:
            # If load times out, the page might be stuck - log and continue
            # LinkedIn pages sometimes have continuous network activity, so we don't
            # wait for networkidle which might never happen
            print(f"  Warning: Page load timeout, continuing anyway...")
        
        # Small random delay for page content to fully render
        await self.random_delay(1, 2)
    
    async def is_logged_in(self) -> bool:
        """Check if we're logged in by looking for logged-in page indicators."""
        try:
            # Check for common logged-in page elements
            # Feed page: has main feed content
            # Profile page: has profile content (not login page)
            # Search page: has search results
            
            # Quick URL check first (fast)
            url = self.page.url
            if "linkedin.com/login" in url or "linkedin.com/uas/login" in url:
                return False
            
            # Check for logged-in indicators on the page
            # Look for elements that only appear when logged in
            logged_in_indicators = [
                'nav[aria-label="Main navigation"]',  # Main nav bar
                'header[data-test-id="global-nav"]',  # Global nav header
                'div[data-test-id="feed-container"]',  # Feed container
                'main[role="main"]',  # Main content area (not login form)
            ]
            
            for selector in logged_in_indicators:
                try:
                    element = self.page.locator(selector).first
                    if await element.count() > 0:
                        return True
                except Exception:
                    continue
            
            # Fallback: check URL patterns (less reliable but better than nothing)
            return (
                "linkedin.com/feed" in url
                or ("linkedin.com/in/" in url and "login" not in url)
                or "linkedin.com/search" in url
            )
        except Exception:
            # If we can't determine, assume not logged in for safety
            return False
    
    def print_banner(self, title: str):
        """Print a formatted banner."""
        print(f"\n{'='*80}\n{title}\n{'='*80}\n")
    
    async def setup_browser(self):
        """Set up browser with stealth settings."""
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
        
        # Load saved cookies if available
        cookies = self.load_cookies()
        if cookies:
            await self.context.add_cookies(cookies)
            print("Loaded saved cookies.")
        
        self.page = await self.context.new_page()
        
        # Remove webdriver property
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
    
    async def ensure_logged_in(self) -> bool:
        """Check if we're logged in and handle login if needed."""
        await self.navigate_to(config.LINKEDIN_FEED_URL)
        
        if await self.is_logged_in():
            cookies = await self.context.cookies()
            self.save_cookies(cookies)
            return True
        
        # Not logged in, need manual login
        self.print_banner("MANUAL LOGIN REQUIRED")
        print("Please log in to LinkedIn in the browser window.")
        print("Waiting for login (checking every 2 seconds, timeout after 5 minutes)...")
        
        # Poll for login status instead of blocking on input
        max_wait_time = 300  # 5 minutes
        check_interval = 2  # Check every 2 seconds
        elapsed = 0
        
        while elapsed < max_wait_time:
            await asyncio.sleep(check_interval)
            elapsed += check_interval
            
            # Check if logged in (navigate to feed page periodically to verify)
            if elapsed % 10 == 0:  # Navigate every 10 seconds
                await self.navigate_to(config.LINKEDIN_FEED_URL)
            # Otherwise, just check current page status without navigation
            
            if await self.is_logged_in():
                cookies = await self.context.cookies()
                self.save_cookies(cookies)
                print(f"Login successful! Cookies saved. (Detected after {elapsed} seconds)")
                return True
            
            # Print progress every 10 seconds
            if elapsed % 10 == 0:
                print(f"Still waiting for login... ({elapsed}/{max_wait_time} seconds)")
        
        print(f"ERROR: Login timeout after {max_wait_time} seconds. Please ensure you're logged in and try again.")
        return False
    
    async def close(self):
        """Close browser and cleanup resources."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

