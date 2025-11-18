"""
LinkedIn Connection Cleanup Script
Removes connections from LinkedIn using Playwright automation.
"""
import argparse
import asyncio
import json
import math
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from playwright.async_api import async_playwright, Page


# Configuration
COOKIES_FILE = "data/linkedin_cookies.json"
PROGRESS_FILE = "data/processed_connections.json"
OUTPUT_CSV = "data/output.csv"
BATCH_SIZE = 10
DELAY_MIN = 5  # seconds between actions
DELAY_MAX = 10  # seconds between actions
BATCH_DELAY_MIN = 120  # seconds between batches (2 minutes)
BATCH_DELAY_MAX = 180  # seconds between batches (3 minutes)


class LinkedInCleanup:
    """Main class for LinkedIn connection cleanup automation."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.processed: Dict[str, Dict] = self.load_progress()
        self.browser = None
        self.context = None
        self.page = None
    
    def load_progress(self) -> Dict[str, Dict]:
        """Load progress from JSON file."""
        path = Path(PROGRESS_FILE)
        return json.loads(path.read_text()) if path.exists() else {}
    
    def save_progress(self):
        """Save progress to JSON file."""
        path = Path(PROGRESS_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.processed, indent=2))
    
    def load_cookies(self) -> Optional[List[Dict]]:
        """Load saved cookies if they exist."""
        path = Path(COOKIES_FILE)
        return json.loads(path.read_text()) if path.exists() else None
    
    def save_cookies(self, cookies: List[Dict]):
        """Save cookies to file."""
        path = Path(COOKIES_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cookies, indent=2))
    
    async def random_delay(self, min_sec: float = DELAY_MIN, max_sec: float = DELAY_MAX):
        """Random delay to mimic human behavior."""
        await asyncio.sleep(random.uniform(min_sec, max_sec))
    
    async def human_like_click(self, element):
        """Perform a human-like click with mouse movement."""
        box = await element.bounding_box()
        if box:
            # Move to a random point near the element
            x = box["x"] + box["width"] / 2 + random.uniform(-5, 5)
            y = box["y"] + box["height"] / 2 + random.uniform(-5, 5)
            await self.page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
        await element.click()
    
    async def navigate_to(self, url: str):
        """Navigate to a URL with timeout handling."""
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except:
            pass  # Continue even if timeout
        await asyncio.sleep(3)
    
    def is_logged_in(self) -> bool:
        """Check if current page indicates logged in state."""
        return "linkedin.com/feed" in self.page.url or "linkedin.com/in/" in self.page.url
    
    def print_banner(self, title: str):
        """Print a formatted banner."""
        print(f"\n{'='*80}")
        print(title)
        print(f"{'='*80}\n")
    
    async def setup_browser(self):
        """Set up browser with stealth settings."""
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch(
            headless=False,  # Keep visible for manual intervention if needed
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
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
        await self.navigate_to("https://www.linkedin.com/feed")
        
        if self.is_logged_in():
            cookies = await self.context.cookies()
            self.save_cookies(cookies)
            return True
        
        # Not logged in, need manual login
        self.print_banner("MANUAL LOGIN REQUIRED")
        print("Please log in to LinkedIn in the browser window.")
        print("Press Enter once you're logged in and on your feed...")
        input()
        
        # Verify login
        await self.navigate_to("https://www.linkedin.com/feed")
        
        if self.is_logged_in():
            cookies = await self.context.cookies()
            self.save_cookies(cookies)
            print("Login successful! Cookies saved.")
            return True
        
        print("ERROR: Still not logged in. Please try again.")
        return False
    
    async def find_more_button(self) -> Optional[object]:
        """Find the 'More' button (three dots) in the profile section."""
        # Look for the More button specifically in the main profile area, not the nav
        selectors = [
            'main button.artdeco-dropdown__trigger:has-text("More")',  # Most specific: in main content
            'section.artdeco-card button.artdeco-dropdown__trigger',  # In profile card
            'div.ph5 button.artdeco-dropdown__trigger:has-text("More")',  # In profile container
        ]
        
        for selector in selectors:
            try:
                button = self.page.locator(selector).first
                if await button.is_visible(timeout=2000):
                    return button
            except:
                continue
        return None
    
    async def find_remove_connection_option(self) -> Optional[object]:
        """Find the 'Remove connection' option in the dropdown menu - tested and working selector."""
        selector = 'div[role="button"][aria-label*="Remove your connection"]'
        try:
            option = self.page.locator(selector).first
            # Check if element exists (don't rely on is_visible as these may not pass visibility check)
            count = await self.page.locator(selector).count()
            if count > 0:
                return option
        except:
            pass
        return None
    
    async def find_confirm_button(self) -> Optional[object]:
        """Find the confirm button in the removal modal."""
        selectors = [
            'button:has-text("Remove")',
            'button[aria-label*="Remove"]',
            'button[data-control-name*="remove"]',
            '//button[contains(text(), "Remove")]',
        ]
        
        for selector in selectors:
            try:
                button = self.page.locator(selector).first
                if await button.is_visible(timeout=2000):
                    # Make sure it's the confirm button, not the cancel
                    text = await button.inner_text()
                    if "cancel" not in text.lower() and "close" not in text.lower():
                        return button
            except:
                continue
        
        return None
    
    async def remove_connection(self, url: str) -> tuple[bool, str]:
        """Remove a single connection. Returns (success, message)."""
        try:
            # Navigate to profile
            await self.navigate_to(url)
            await self.random_delay(2, 4)  # Wait for page to fully load
            
            # Find and click "More" button
            more_button = await self.find_more_button()
            if not more_button:
                return False, "Could not find 'More' button"
            
            await self.human_like_click(more_button)
            
            # Wait for dropdown to appear
            try:
                await self.page.wait_for_selector('div.artdeco-dropdown__content', timeout=3000)
            except:
                pass  # Continue even if not found
            
            await self.random_delay(1, 2)
            
            # Find "Remove connection" option
            remove_option = await self.find_remove_connection_option()
            if not remove_option:
                # Try pressing Escape to close dropdown and retry
                await self.page.keyboard.press("Escape")
                await asyncio.sleep(1)
                return False, "Could not find 'Remove connection' option"
            
            # DRY RUN MODE: Stop here and report success
            if self.dry_run:
                aria_label = await remove_option.get_attribute("aria-label")
                print(f"\n  [DRY RUN] Found remove option with aria-label: {aria_label}")
                # Close dropdown
                await self.page.keyboard.press("Escape")
                return True, "[DRY RUN] Successfully found all selectors - would remove connection"
            
            # LIVE MODE: Actually remove the connection
            await self.human_like_click(remove_option)
            await self.random_delay(1, 2)
            
            # Find and click confirm button in modal
            confirm_button = await self.find_confirm_button()
            if not confirm_button:
                return False, "Could not find confirm button in modal"
            
            await self.human_like_click(confirm_button)
            await self.random_delay(2, 3)
            
            # Verify removal (check for Connect button or success message)
            connect_button = self.page.locator('button:has-text("Connect")').first
            if await connect_button.is_visible(timeout=3000):
                return True, "Successfully removed"
            
            # Alternative check: see if "More" button is gone
            more_button_after = await self.find_more_button()
            if not more_button_after:
                return True, "Successfully removed (More button no longer visible)"
            
            return True, "Removal completed (verification uncertain)"
            
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    async def process_batch(self, urls: List[str], batch_num: int, total_batches: int):
        """Process a batch of connections."""
        self.print_banner(f"BATCH {batch_num}/{total_batches} - Processing {len(urls)} connections")
        
        for idx, url in enumerate(urls, 1):
            if url in self.processed and self.processed[url].get("status") == "success":
                print(f"[{idx}/{len(urls)}] Skipping {url} (already processed)")
                continue
            
            print(f"[{idx}/{len(urls)}] Processing: {url}")
            
            success, message = await self.remove_connection(url)
            
            timestamp = datetime.now().isoformat()
            self.processed[url] = {
                "status": "success" if success else "failed",
                "message": message,
                "timestamp": timestamp,
            }
            
            self.save_progress()  # Save after each connection
            
            if success:
                print(f"  ✓ {message}")
            else:
                print(f"  ✗ {message}")
            
            # Delay before next connection (except for the last one)
            if idx < len(urls):
                await self.random_delay()
        
        print(f"\n✓ Batch {batch_num} complete!")
    
    async def run(self):
        """Main execution method."""
        self.print_banner("LINKEDIN CONNECTION CLEANUP")
        
        # Load connections from CSV
        print(f"Loading connections from {OUTPUT_CSV}...")
        df = pd.read_csv(OUTPUT_CSV)
        urls = df["URL"].tolist()
        print(f"Found {len(urls)} connections to process.")
        
        # Filter out already processed successful ones
        remaining = [url for url in urls if url not in self.processed or self.processed[url].get("status") != "success"]
        print(f"Remaining to process: {len(remaining)}")
        
        if not remaining:
            print("\nAll connections have already been processed successfully!")
            return
        
        # Setup browser
        print("\nSetting up browser...")
        await self.setup_browser()
        
        try:
            # Ensure logged in
            if not await self.ensure_logged_in():
                print("Failed to log in. Exiting.")
                return
            
            # Process in batches
            total_batches = math.ceil(len(remaining) / BATCH_SIZE)
            
            for batch_num in range(1, total_batches + 1):
                start_idx = (batch_num - 1) * BATCH_SIZE
                end_idx = min(start_idx + BATCH_SIZE, len(remaining))
                batch_urls = remaining[start_idx:end_idx]
                
                await self.process_batch(batch_urls, batch_num, total_batches)
                
                # Wait between batches (except after the last one)
                if batch_num < total_batches:
                    delay = random.uniform(BATCH_DELAY_MIN, BATCH_DELAY_MAX)
                    print(f"\nWaiting {delay:.0f} seconds before next batch...")
                    print("Press Enter to continue early, or wait for the delay...")
                    
                    # Wait with early exit option
                    try:
                        await asyncio.wait_for(
                            asyncio.to_thread(input),
                            timeout=delay
                        )
                        print("Continuing early...")
                    except (asyncio.TimeoutError, EOFError):
                        # TimeoutError: delay completed normally
                        # EOFError: no interactive terminal (automated mode)
                        print("Delay complete, continuing...")
            
            self.print_banner("ALL BATCHES COMPLETE!")
            
            # Summary
            statuses = [v.get("status") for v in self.processed.values()]
            successful = statuses.count("success")
            failed = statuses.count("failed")
            print("Summary:")
            print(f"  Successful: {successful}")
            print(f"  Failed: {failed}")
            print(f"  Progress saved to: {PROGRESS_FILE}")
        
        finally:
            print("\nClosing browser...")
            await self.browser.close()


async def main():
    """Entry point."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="LinkedIn Connection Cleanup - Remove connections using Playwright automation"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test mode - finds selectors but doesn't remove connections"
    )
    parser.add_argument(
        "--test-url",
        type=str,
        metavar="URL",
        help="Test on a specific profile URL (requires --dry-run)"
    )
    args = parser.parse_args()
    
    if args.test_url and not args.dry_run:
        parser.error("--test-url requires --dry-run mode")
    
    cleanup = LinkedInCleanup(dry_run=args.dry_run)
    
    # Handle dry-run with test URL
    if args.dry_run and args.test_url:
        cleanup.print_banner("DRY RUN MODE - Testing selectors")
        print(f"Test URL: {args.test_url}\n")
        
        await cleanup.setup_browser()
        try:
            if not await cleanup.ensure_logged_in():
                print("Failed to log in. Exiting.")
                return
            
            success, message = await cleanup.remove_connection(args.test_url)
            
            result = "✓ SUCCESS" if success else "✗ FAILED"
            cleanup.print_banner(f"Result: {result}")
            print(f"Message: {message}\n")
            
            if success:
                print("All selectors working correctly! ✓")
            else:
                print("Selectors need updating. Check the error message above.")
        finally:
            await cleanup.browser.close()
    
    # Normal run (or dry-run without test URL)
    else:
        if args.dry_run:
            cleanup.print_banner("DRY RUN MODE - Will test selectors but not remove connections")
        await cleanup.run()


if __name__ == "__main__":
    asyncio.run(main())

