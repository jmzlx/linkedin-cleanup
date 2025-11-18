"""
Configuration constants for LinkedIn cleanup project.
Centralized configuration for all modules.
"""
from pathlib import Path

# Find project root (directory containing pyproject.toml)
_PROJECT_ROOT = Path(__file__).parent.parent

# File paths (relative to project root)
COOKIES_FILE = str(_PROJECT_ROOT / "data" / "linkedin_cookies.json")
PROGRESS_FILE = str(_PROJECT_ROOT / "data" / "processed_connections.json")
OUTPUT_CSV = str(_PROJECT_ROOT / "data" / "urls_to_remove.csv")
DEFAULT_OUTPUT_CSV = str(_PROJECT_ROOT / "data" / "country_filtered_connections.csv")

# Default URLs
DEFAULT_SEARCH_URL = "https://www.linkedin.com/search/results/people/?origin=FACETED_SEARCH&network=%5B%22F%22%5D&geoUrn=%5B%22103121230%22%2C%22102713980%22%2C%22102264497%22%5D"
LINKEDIN_FEED_URL = "https://www.linkedin.com/feed"

# Timing delays - Extraction
EXTRACTION_DELAY_MIN = 2  # seconds between actions
EXTRACTION_DELAY_MAX = 4  # seconds between actions
PAGE_DELAY_MIN = 3  # seconds between pages
PAGE_DELAY_MAX = 6  # seconds between pages

# Timing delays - Removal
REMOVAL_DELAY_MIN = 5  # seconds between actions
REMOVAL_DELAY_MAX = 10  # seconds between actions
BATCH_DELAY_MIN = 120  # seconds between batches (2 minutes)
BATCH_DELAY_MAX = 180  # seconds between batches (3 minutes)

# Batch processing
BATCH_SIZE = 10

# Browser settings
BROWSER_HEADLESS = False
BROWSER_VIEWPORT_WIDTH = 1920
BROWSER_VIEWPORT_HEIGHT = 1080
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
BROWSER_LOCALE = "en-US"

# Timeouts
NAVIGATION_TIMEOUT = 60000  # milliseconds
SELECTOR_TIMEOUT = 10000  # milliseconds
SHORT_SELECTOR_TIMEOUT = 2000  # milliseconds
VERIFICATION_TIMEOUT = 3000  # milliseconds

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
    'section.artdeco-card button.artdeco-dropdown__trigger',  # In profile card
    'div.ph5 button.artdeco-dropdown__trigger:has-text("More")',  # In profile container
]
REMOVE_CONNECTION_SELECTOR = 'div[role="button"][aria-label*="Remove your connection"]'
DROPDOWN_CONTENT_SELECTOR = 'div.artdeco-dropdown__content'
CONNECT_BUTTON_SELECTOR = 'button:has-text("Connect")'

# Safety limits
MAX_PAGES = 100  # Maximum pages to extract (safety limit)

