"""
Search Extractor - Utilities for extracting profiles from LinkedIn search results.
"""

import logging
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from linkedin_cleanup import config
from linkedin_cleanup.linkedin_client import LinkedInClient
from linkedin_cleanup.random_actions import random_delay

logger = logging.getLogger(__name__)

# Load JavaScript extractor code
_JS_EXTRACTOR_PATH = Path(__file__).parent / "js_extractors" / "profile_extractor.js"
_PROFILE_EXTRACTOR_JS = _JS_EXTRACTOR_PATH.read_text() if _JS_EXTRACTOR_PATH.exists() else None


def normalize_linkedin_url(href: str) -> str | None:
    """
    Normalize a LinkedIn profile URL.
    Returns the normalized URL or None if invalid.
    """
    if not href or "/in/" not in href:
        return None

    # Clean up URL (remove query parameters, ensure full URL)
    if href.startswith("/"):
        return f"https://www.linkedin.com{href.split('?')[0]}"
    elif href.startswith("http"):
        return href.split("?")[0]
    else:
        return None


def clean_profile_name(text: str) -> str:
    """
    Clean and extract profile name from text.
    Removes common suffixes like "• 1st" or job titles.
    """
    if not text:
        return ""

    # Take first line, remove extra whitespace
    name = text.split("\n")[0].strip()
    # Remove common suffixes like "• 1st" or job titles
    if "•" in name:
        name = name.split("•")[0].strip()
    return name


class SearchExtractor:
    """Handles extraction of profiles from LinkedIn search results."""

    def __init__(self, client: LinkedInClient):
        """Initialize with a LinkedIn client."""
        self.client = client

    async def extract_profiles_from_page(self) -> list[tuple[str, str, str]]:
        """
        Extract profile names, URLs, and locations from the current search results page.

        Uses JavaScript evaluation (from js_extractors/profile_extractor.js) to extract
        profile data from DOM. Returns list of (name, url, location) tuples.
        """
        page = self.client.page
        profiles = []
        seen_urls = set()

        try:
            await page.wait_for_selector(
                'div[data-view-name="people-search-result"]', timeout=config.SELECTOR_TIMEOUT
            )
        except PlaywrightTimeoutError:
            logger.debug("Timeout waiting for search results")
        except Exception as e:
            logger.debug(f"Error waiting for search results: {e}")

        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await random_delay()
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.8)")
            await random_delay()
        except Exception as e:
            logger.debug(f"Error scrolling page: {e}")

        try:
            # Use extracted JavaScript code if available, otherwise fallback to inline
            js_code = (
                _PROFILE_EXTRACTOR_JS
                if _PROFILE_EXTRACTOR_JS
                else """
            () => {
                let main = document.querySelector('main');
                if (!main) return {error: 'No main element', stats: {}};
                return {profiles: [], stats: {}};
            }
            """
            )
            profile_data = await page.evaluate(js_code)

            if not isinstance(profile_data, dict) or "profiles" not in profile_data:
                return profiles

            if "error" in profile_data:
                return profiles

            profile_list = profile_data["profiles"]
            if not profile_list:
                return profiles

            for profile in profile_list:
                try:
                    url = normalize_linkedin_url(profile["url"])
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    profiles.append(
                        (clean_profile_name(profile["name"]), url, profile["location"] or "Unknown")
                    )
                except Exception as e:
                    logger.debug(f"Error processing profile: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Error extracting profiles: {e}")
            return profiles

        return profiles

    async def has_next_page(self) -> bool:
        """Check if there's a next page available by looking for enabled Next button."""
        page = self.client.page
        try:
            for selector in config.NEXT_BUTTON_SELECTORS:
                try:
                    next_button = page.locator(selector).first
                    if await next_button.count() > 0 and await next_button.is_enabled():
                        return True
                except (PlaywrightTimeoutError, AttributeError):
                    continue
            return False
        except Exception as e:
            logger.debug(f"Error checking for next page: {e}")
            return False

    async def go_to_next_page(self) -> bool:
        """Navigate to the next page by clicking the Next button. Returns True if successful."""
        page = self.client.page
        try:
            for selector in config.NEXT_BUTTON_SELECTORS:
                try:
                    next_button = page.locator(selector).first
                    if await next_button.count() > 0 and await next_button.is_enabled():
                        await next_button.scroll_into_view_if_needed()
                        await random_delay()
                        await next_button.click()
                        await random_delay()
                        return True
                except (PlaywrightTimeoutError, AttributeError):
                    continue
            return False
        except Exception as e:
            logger.debug(f"Error navigating to next page: {e}")
            return False
