"""
Configuration constants for LinkedIn cleanup project.
Centralized configuration for all modules.
Supports environment variable overrides.
"""

import os
from pathlib import Path


def _get_env_float(key: str, default: float, min_value: float = 0.0) -> float:
    """Get float from environment variable with validation."""
    if (value := os.getenv(key)) is None:
        return default
    try:
        float_value = float(value)
        if float_value < min_value:
            raise ValueError(f"{key} must be >= {min_value}")
        return float_value
    except ValueError as e:
        raise ValueError(f"Invalid value for {key}: {e}") from e


def _get_env_int(key: str, default: int, min_value: int = 0) -> int:
    """Get int from environment variable with validation."""
    if (value := os.getenv(key)) is None:
        return default
    try:
        int_value = int(value)
        if int_value < min_value:
            raise ValueError(f"{key} must be >= {min_value}")
        return int_value
    except ValueError as e:
        raise ValueError(f"Invalid value for {key}: {e}") from e


def _get_env_bool(key: str, default: bool) -> bool:
    """Get bool from environment variable."""
    if (value := os.getenv(key)) is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


# Find project root (directory containing pyproject.toml)
_PROJECT_ROOT = Path(__file__).parent.parent

# File paths (relative to project root)
COOKIES_FILE = str(_PROJECT_ROOT / "data" / "linkedin_cookies.json")
PROGRESS_FILE = str(_PROJECT_ROOT / "data" / "processed_connections.db")
OUTPUT_CSV = str(_PROJECT_ROOT / "data" / "urls_to_remove.csv")
DEFAULT_OUTPUT_CSV = str(_PROJECT_ROOT / "data" / "country_filtered_connections.csv")

# Default URLs
DEFAULT_SEARCH_URL = "https://www.linkedin.com/search/results/people/?origin=FACETED_SEARCH&network=%5B%22F%22%5D&geoUrn=%5B%22103121230%22%2C%22102713980%22%2C%22102264497%22%5D"
LINKEDIN_FEED_URL = "https://www.linkedin.com/feed"

# Timing delays - Extraction (can be overridden via environment variables)
EXTRACTION_DELAY_MIN = _get_env_float("LINKEDIN_EXTRACTION_DELAY_MIN", 2.0, min_value=0.0)
EXTRACTION_DELAY_MAX = _get_env_float("LINKEDIN_EXTRACTION_DELAY_MAX", 4.0, min_value=0.0)
PAGE_DELAY_MIN = _get_env_float("LINKEDIN_PAGE_DELAY_MIN", 3.0, min_value=0.0)
PAGE_DELAY_MAX = _get_env_float("LINKEDIN_PAGE_DELAY_MAX", 6.0, min_value=0.0)

# Timing delays - Removal (can be overridden via environment variables)
REMOVAL_DELAY_MIN = _get_env_float("LINKEDIN_REMOVAL_DELAY_MIN", 5.0, min_value=0.0)
REMOVAL_DELAY_MAX = _get_env_float("LINKEDIN_REMOVAL_DELAY_MAX", 10.0, min_value=0.0)

# Browser settings (can be overridden via environment variables)
BROWSER_HEADLESS = _get_env_bool("LINKEDIN_BROWSER_HEADLESS", False)
BROWSER_VIEWPORT_WIDTH = _get_env_int("LINKEDIN_BROWSER_VIEWPORT_WIDTH", 1920, min_value=1)
BROWSER_VIEWPORT_HEIGHT = _get_env_int("LINKEDIN_BROWSER_VIEWPORT_HEIGHT", 1080, min_value=1)
USER_AGENT = os.getenv(
    "LINKEDIN_USER_AGENT",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
)
BROWSER_LOCALE = os.getenv("LINKEDIN_BROWSER_LOCALE", "en-US")

# Timeouts (can be overridden via environment variables, in milliseconds)
NAVIGATION_TIMEOUT = _get_env_int("LINKEDIN_NAVIGATION_TIMEOUT", 60000, min_value=1000)
SELECTOR_TIMEOUT = _get_env_int("LINKEDIN_SELECTOR_TIMEOUT", 10000, min_value=1000)
SHORT_SELECTOR_TIMEOUT = _get_env_int("LINKEDIN_SHORT_SELECTOR_TIMEOUT", 2000, min_value=500)
VERIFICATION_TIMEOUT = _get_env_int("LINKEDIN_VERIFICATION_TIMEOUT", 3000, min_value=500)

# Selectors - Search extraction
PROFILE_LINK_SELECTOR = 'a[href*="/in/"]'

# Selectors - Pagination
NEXT_BUTTON_SELECTORS = [
    'button[aria-label*="Next"]',
    'button[aria-label*="next"]',
    'button:has-text("Next")',
    'button[aria-label*="Next page"]',
]

# Selectors - Connection removal
MORE_BUTTON_SELECTORS = [
    'main button.artdeco-dropdown__trigger:has-text("More")',  # Most specific: in main content
    'div.ph5 button.artdeco-dropdown__trigger:has-text("More")',  # In profile container
    # Note: Removed generic 'section.artdeco-card' selector to avoid matching nav buttons
]
REMOVE_CONNECTION_SELECTOR = 'div[role="button"][aria-label*="Remove your connection"]'
DROPDOWN_CONTENT_SELECTOR = "div.artdeco-dropdown__content"
CONNECT_BUTTON_SELECTOR = 'button:has-text("Connect")'

# Safety limits (can be overridden via environment variables)
MAX_PAGES = _get_env_int("LINKEDIN_MAX_PAGES", 100, min_value=1)

# Random actions - Anti-detection (can be overridden via environment variables)
RANDOM_ACTION_PROBABILITY = _get_env_float("LINKEDIN_RANDOM_ACTION_PROBABILITY", 0.3, min_value=0.0)

# Validate that min delays are <= max delays
if EXTRACTION_DELAY_MIN > EXTRACTION_DELAY_MAX:
    raise ValueError("EXTRACTION_DELAY_MIN must be <= EXTRACTION_DELAY_MAX")
if PAGE_DELAY_MIN > PAGE_DELAY_MAX:
    raise ValueError("PAGE_DELAY_MIN must be <= PAGE_DELAY_MAX")
if REMOVAL_DELAY_MIN > REMOVAL_DELAY_MAX:
    raise ValueError("REMOVAL_DELAY_MIN must be <= REMOVAL_DELAY_MAX")
if not (0.0 <= RANDOM_ACTION_PROBABILITY <= 1.0):
    raise ValueError("RANDOM_ACTION_PROBABILITY must be between 0.0 and 1.0")
