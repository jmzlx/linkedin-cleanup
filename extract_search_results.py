"""
LinkedIn Search Results Extractor
Extracts profile names and URLs from LinkedIn search results without accessing individual profiles.
"""
import argparse
import asyncio
import csv
import json
import random
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from playwright.async_api import async_playwright


# Configuration
COOKIES_FILE = "data/linkedin_cookies.json"
EXTRACTION_PROGRESS_FILE = "data/extraction_progress.json"
DEFAULT_SEARCH_URL = "https://www.linkedin.com/search/results/people/?origin=FACETED_SEARCH&network=%5B%22F%22%5D&geoUrn=%5B%22103121230%22%2C%22102713980%22%2C%22102264497%22%5D"
DELAY_MIN = 2  # seconds between actions
DELAY_MAX = 4  # seconds between actions
PAGE_DELAY_MIN = 3  # seconds between pages
PAGE_DELAY_MAX = 6  # seconds between pages


class LinkedInSearchExtractor:
    """Main class for extracting LinkedIn search results."""
    
    def __init__(self):
        self.extracted_profiles: Dict[str, Dict] = self.load_progress()
        self.browser = None
        self.context = None
        self.page = None
    
    def load_progress(self) -> Dict[str, Dict]:
        """Load extraction progress from JSON file."""
        path = Path(EXTRACTION_PROGRESS_FILE)
        return json.loads(path.read_text()) if path.exists() else {}
    
    def save_progress(self):
        """Save extraction progress to JSON file."""
        path = Path(EXTRACTION_PROGRESS_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.extracted_profiles, indent=2))
    
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
    
    async def navigate_to(self, url: str):
        """Navigate to a URL with timeout handling."""
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except:
            pass  # Continue even if timeout
        # Small random delay for page content to fully render
        await self.random_delay(1, 2)
    
    def is_logged_in(self) -> bool:
        """Check if current page indicates logged in state."""
        return "linkedin.com/feed" in self.page.url or "linkedin.com/in/" in self.page.url or "linkedin.com/search" in self.page.url
    
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
    
    async def extract_profiles_from_page(self) -> List[Tuple[str, str]]:
        """
        Extract profile names and URLs from the current search results page.
        Returns list of (name, url) tuples.
        """
        profiles = []
        seen_urls = set()
        
        try:
            # Wait for search results to load - try multiple selectors
            await self.page.wait_for_selector('a[href*="/in/"]', timeout=10000)
        except:
            # Continue even if timeout
            pass
        
        # Scroll down to load all content (LinkedIn may use lazy loading)
        try:
            # Scroll to bottom of page to trigger lazy loading
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self.random_delay(2, 3)
            # Scroll back up a bit
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.8)")
            await self.random_delay(1, 2)
        except:
            pass
        
        # Find all profile links directly (this selector works based on test)
        try:
            profile_links = await self.page.locator('a[href*="/in/"]').all()
        except:
            print("Warning: Could not find any profile links on this page.")
            return profiles
        
        print(f"Found {len(profile_links)} profile links on page")
        
        # Extract profile data from each link
        for link in profile_links:
            try:
                # Extract URL
                href = await link.get_attribute("href")
                if not href or "/in/" not in href:
                    continue
                
                # Clean up URL (remove query parameters, ensure full URL)
                if href.startswith("/"):
                    url = f"https://www.linkedin.com{href.split('?')[0]}"
                elif href.startswith("http"):
                    url = href.split("?")[0]
                else:
                    continue
                
                # Skip if we've already seen this URL
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                # Extract name from link text
                name = None
                try:
                    # Get the link text
                    link_text = await link.inner_text()
                    if link_text:
                        # Clean up the text - take first line, remove extra whitespace
                        name = link_text.split('\n')[0].strip()
                        # Remove common suffixes like "• 1st" or job titles
                        if '•' in name:
                            name = name.split('•')[0].strip()
                except:
                    pass
                
                # If name extraction failed, try to get from aria-label or title
                if not name or len(name) < 2:
                    try:
                        aria_label = await link.get_attribute("aria-label")
                        if aria_label:
                            name = aria_label.split('\n')[0].strip()
                            if '•' in name:
                                name = name.split('•')[0].strip()
                    except:
                        pass
                
                # If still no name, derive from URL
                if not name or len(name) < 2:
                    name = url.split("/in/")[-1].replace("-", " ").title()
                
                # Only add if we have a valid URL
                if url:
                    profiles.append((name, url))
            
            except Exception as e:
                print(f"  Error extracting profile from link: {e}")
                continue
        
        # Remove duplicates based on URL (in case same profile appears multiple times)
        unique_profiles = []
        seen = set()
        for name, url in profiles:
            if url not in seen:
                unique_profiles.append((name, url))
                seen.add(url)
        
        return unique_profiles
    
    async def has_next_page(self) -> bool:
        """Check if there's a next page available."""
        try:
            # Look for "Next" button with various selectors
            next_selectors = [
                'button[aria-label*="Next"]',
                'button[aria-label*="next"]',
                'button:has-text("Next")',
                'button[aria-label*="Next page"]',
                'li[data-test-pagination-page-btn] + li button',
                'button.pagination__button--next',
            ]
            
            for selector in next_selectors:
                try:
                    next_button = self.page.locator(selector).first
                    if await next_button.count() > 0:
                        # Check if button is disabled
                        is_disabled = await next_button.get_attribute("disabled")
                        aria_disabled = await next_button.get_attribute("aria-disabled")
                        classes = await next_button.get_attribute("class") or ""
                        # Check if button is disabled by class
                        if "disabled" in classes.lower():
                            continue
                        if not is_disabled and aria_disabled != "true":
                            return True
                except:
                    continue
            
            # Alternative: check for page numbers
            try:
                pagination_items = await self.page.locator('li[data-test-pagination-page-btn]').all()
                if len(pagination_items) > 0:
                    # Check if current page is not the last
                    current_page = self.page.locator('li[data-test-pagination-page-btn][aria-current="page"]')
                    if await current_page.count() > 0:
                        # Try to find a page number higher than current
                        current_text = await current_page.first.inner_text()
                        try:
                            current_num = int(current_text.strip())
                            # Look for next page number
                            for item in pagination_items:
                                item_text = await item.inner_text()
                                try:
                                    item_num = int(item_text.strip())
                                    if item_num > current_num:
                                        return True
                                except:
                                    continue
                        except:
                            pass
            except:
                pass
            
            # Check URL for page parameter
            current_url = self.page.url
            if "page=" in current_url:
                # If URL has page parameter, there might be more pages
                # We'll try to navigate and see if we get more results
                pass
            
            return False
        except:
            return False
    
    async def go_to_next_page(self) -> bool:
        """Navigate to the next page. Returns True if successful, False if no next page."""
        try:
            # Try clicking "Next" button with various selectors
            next_selectors = [
                'button[aria-label*="Next"]',
                'button[aria-label*="next"]',
                'button:has-text("Next")',
                'button[aria-label*="Next page"]',
                'button.pagination__button--next',
            ]
            
            for selector in next_selectors:
                try:
                    next_button = self.page.locator(selector).first
                    if await next_button.count() > 0:
                        is_disabled = await next_button.get_attribute("disabled")
                        aria_disabled = await next_button.get_attribute("aria-disabled")
                        classes = await next_button.get_attribute("class") or ""
                        if is_disabled or aria_disabled == "true" or "disabled" in classes.lower():
                            continue
                        
                        await next_button.scroll_into_view_if_needed()
                        await self.random_delay(0.5, 1)
                        await next_button.click()
                        await self.random_delay(PAGE_DELAY_MIN, PAGE_DELAY_MAX)
                        return True
                except:
                    continue
            
            # Alternative: click next page number
            try:
                pagination_items = await self.page.locator('li[data-test-pagination-page-btn]').all()
                if len(pagination_items) > 0:
                    current_page = self.page.locator('li[data-test-pagination-page-btn][aria-current="page"]')
                    if await current_page.count() > 0:
                        current_text = await current_page.first.inner_text()
                        try:
                            current_num = int(current_text.strip())
                            # Find and click next page number
                            for item in pagination_items:
                                item_text = await item.inner_text()
                                try:
                                    item_num = int(item_text.strip())
                                    if item_num == current_num + 1:
                                        await item.scroll_into_view_if_needed()
                                        await self.random_delay(0.5, 1)
                                        await item.click()
                                        await self.random_delay(PAGE_DELAY_MIN, PAGE_DELAY_MAX)
                                        return True
                                except:
                                    continue
                        except:
                            pass
            except:
                pass
            
            # Try URL-based pagination
            try:
                current_url = self.page.url
                if "page=" in current_url:
                    match = re.search(r'page=(\d+)', current_url)
                    if match:
                        current_page_num = int(match.group(1))
                        next_page_num = current_page_num + 1
                        next_url = re.sub(r'page=\d+', f'page={next_page_num}', current_url)
                        await self.navigate_to(next_url)
                        await self.random_delay(PAGE_DELAY_MIN, PAGE_DELAY_MAX)
                        return True
                else:
                    # Add page parameter
                    separator = "&" if "?" in current_url else "?"
                    next_url = f"{current_url}{separator}page=2"
                    await self.navigate_to(next_url)
                    await self.random_delay(PAGE_DELAY_MIN, PAGE_DELAY_MAX)
                    return True
            except:
                pass
            
            return False
        except Exception as e:
            print(f"Error navigating to next page: {e}")
            return False
    
    async def extract_all_profiles(self, search_url: str) -> List[Tuple[str, str]]:
        """Extract all profiles from search results, handling pagination."""
        all_profiles = []
        page_num = 1
        
        # Navigate to search URL
        print(f"Navigating to search results...")
        await self.navigate_to(search_url)
        
        # Wait a bit for page to load
        await self.random_delay(2, 3)
        
        while True:
            print(f"\nExtracting profiles from page {page_num}...")
            
            # Extract profiles from current page
            page_profiles = await self.extract_profiles_from_page()
            
            if not page_profiles:
                print(f"No profiles found on page {page_num}. Stopping.")
                break
            
            # Add new profiles (avoid duplicates)
            new_count = 0
            for name, url in page_profiles:
                if url not in self.extracted_profiles:
                    all_profiles.append((name, url))
                    self.extracted_profiles[url] = {
                        "name": name,
                        "url": url,
                        "page": page_num,
                    }
                    new_count += 1
            
            print(f"Found {len(page_profiles)} profiles on page {page_num} ({new_count} new)")
            
            # Save progress after each page
            self.save_progress()
            
            # Check for next page
            if not await self.has_next_page():
                print("No more pages available.")
                break
            
            # Go to next page
            if not await self.go_to_next_page():
                print("Could not navigate to next page. Stopping.")
                break
            
            page_num += 1
            
            # Safety limit (shouldn't be needed, but just in case)
            if page_num > 100:
                print("Reached page limit (100). Stopping.")
                break
        
        return all_profiles
    
    def save_to_csv(self, profiles: List[Tuple[str, str]], output_path: str):
        """Save extracted profiles to CSV file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Name', 'URL'])
            for name, url in profiles:
                writer.writerow([name, url])
        
        print(f"\nSaved {len(profiles)} profiles to {output_path}")
    
    async def run(self, search_url: str, output_csv: str):
        """Main execution method."""
        self.print_banner("LINKEDIN SEARCH RESULTS EXTRACTOR")
        
        # Setup browser
        print("Setting up browser...")
        await self.setup_browser()
        
        try:
            # Ensure logged in
            if not await self.ensure_logged_in():
                print("Failed to log in. Exiting.")
                return
            
            # Extract all profiles
            all_profiles = await self.extract_all_profiles(search_url)
            
            # Save to CSV
            self.save_to_csv(all_profiles, output_csv)
            
            self.print_banner("EXTRACTION COMPLETE!")
            print(f"Total profiles extracted: {len(all_profiles)}")
            print(f"Progress saved to: {EXTRACTION_PROGRESS_FILE}")
            print(f"CSV saved to: {output_csv}")
        
        finally:
            print("\nClosing browser...")
            await self.browser.close()


async def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="LinkedIn Search Results Extractor - Extract profile URLs from search results"
    )
    parser.add_argument(
        "--search-url",
        type=str,
        default=DEFAULT_SEARCH_URL,
        help=f"LinkedIn search results URL (default: {DEFAULT_SEARCH_URL})"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/country_filtered_connections.csv",
        help="Output CSV file path (default: data/country_filtered_connections.csv)"
    )
    args = parser.parse_args()
    
    extractor = LinkedInSearchExtractor()
    await extractor.run(args.search_url, args.output)


if __name__ == "__main__":
    asyncio.run(main())

