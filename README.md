# LinkedIn Connection Cleanup

Automated tool to remove LinkedIn connections using Playwright. Processes connections individually with random delays to avoid bot detection.

## Setup

1. **Install dependencies:**
   ```bash
   uv sync
   # or
   pip install -r requirements.txt
   ```

2. **Install the package in editable mode:**
   ```bash
   uv pip install -e .
   # or
   pip install -e .
   ```

3. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   ```

## Usage

### Test Selectors First (Recommended)

Before running the full cleanup, test that selectors work on a single profile:

```bash
python scripts/remove_connections.py --dry-run --url "https://www.linkedin.com/in/USERNAME"
```

This will:
- Open a browser window
- Allow you to log in manually (first time)
- Navigate to the test profile
- Verify selectors work (without actually removing the connection)

### Run the Cleanup Script

```bash
# Dry run: Test on all connections without removing
python scripts/remove_connections.py --dry-run

# Live run: Actually remove connections
python scripts/remove_connections.py
```

The script will:
1. Load connections from `data/output.csv`
2. Check for saved cookies (if you've logged in before)
3. If no cookies, open browser for manual login
4. Process connections individually with random delays between them
5. Save progress after each connection

## Features

- **Manual Login**: First run requires manual login, then cookies are saved for future runs
- **Individual Profile Processing**: Processes connections one at a time with random delays
- **Progress Tracking**: Saves progress to `data/processed_connections.json` to allow resuming
- **Bot Detection Avoidance**:
  - Random delays between profiles (5-10 seconds)
  - Human-like mouse movements
  - Stealth browser settings
- **Error Handling**: Continues processing even if individual connections fail
- **Resume Capability**: Skips already successfully processed connections

## Project Structure

```
linkedin-cleanup/
├── linkedin_cleanup/          # Core library package
│   ├── __init__.py
│   ├── config.py              # Configuration constants
│   ├── linkedin_client.py      # Browser automation client
│   ├── search_extractor.py     # Search result extraction utilities
│   └── connection_remover.py   # Connection removal utilities
├── scripts/                    # Executable scripts
│   ├── extract_search_results.py  # Extract profiles from search results
│   └── remove_connections.py      # Remove LinkedIn connections
├── tests/                      # Test suite
│   ├── test_connection_removal.py
│   ├── test_db.py
│   ├── test_search_extraction.py
│   ├── test_random_actions.py
│   └── test_utils.py
├── notebooks/                 # Jupyter notebooks
│   └── identify_connections.ipynb
└── data/                      # Data files
    ├── linkedin_cookies.json      # Saved authentication cookies (gitignored)
    ├── processed_connections.json # Progress tracking (gitignored)
    └── output.csv                 # Input file with connections to remove
```

## Files

- `scripts/remove_connections.py` - Main automation script with built-in dry-run mode
- `scripts/extract_search_results.py` - Extract profile URLs from LinkedIn search results
- `data/linkedin_cookies.json` - Saved authentication cookies (gitignored)
- `data/processed_connections.json` - Progress tracking (gitignored)
- `data/output.csv` - Input file with connections to remove

## Configuration

You can modify configuration constants in `linkedin_cleanup/config.py`:

- `EXTRACTION_DELAY_MIN` / `EXTRACTION_DELAY_MAX`: Random delay between actions in seconds (default: 2-4)
- `REMOVAL_DELAY_MIN` / `REMOVAL_DELAY_MAX`: Random delay between profiles in seconds (default: 5-10)
- `PAGE_DELAY_MIN` / `PAGE_DELAY_MAX`: Random delay between pages in seconds (default: 3-6)
- `RANDOM_ACTION_PROBABILITY`: Probability of performing random actions (default: 0.3)

## Testing

The project includes comprehensive tests covering the main use cases.

### Running Tests

```bash
# Install dependencies first
uv sync

# Run all tests
pytest

# Run with verbose output
pytest -v
```

### Test Coverage

The test suite covers:

1. **Connection Removal** (`test_connection_removal.py`)
   - Check connection status (connected, not connected, unknown)
   - Disconnect connection (dry run mode)
   - Find More button functionality

2. **Database** (`test_db.py`)
   - Update and get connection status
   - Get pending URLs
   - Get all connections for summary stats
   - Status overwrite behavior
   - Non-existent URL handling

3. **Search Extraction** (`test_search_extraction.py`)
   - Extract profiles from search page
   - Pagination functionality

4. **Random Actions** (`test_random_actions.py`)
   - Probability-based action execution
   - Random action behaviors

5. **Utilities** (`test_utils.py`)
   - URL normalization
   - Profile name cleaning
   - Timeout behavior
   - Client setup error handling

### Test Philosophy

Tests focus on core functionality rather than exhaustive edge cases. Each test verifies a main use case with realistic scenarios.

## Notes

- The browser window will remain visible during execution
- If the script is interrupted, you can resume and it will skip already processed connections
- Failed connections are logged but don't stop the process
- Make sure you have a stable internet connection

## Troubleshooting

- **Can't find "More" button**: Run with `--dry-run --url` to verify selectors. If they fail, LinkedIn may have updated their UI
- **Login issues**: Delete `data/linkedin_cookies.json` and log in again
- **Connection already removed**: The script will detect this and skip it
- **Rate limiting**: If LinkedIn shows warnings, increase the delays in the configuration
- **Test before running**: Always use `--dry-run` first to verify everything works

## Tested Working Selectors

These selectors have been tested and confirmed working with the current LinkedIn interface:

- **More Button**: `button.artdeco-dropdown__trigger`
- **Remove Connection Option**: `div[role="button"][aria-label*="Remove your connection"]`

**Note**: LinkedIn updates their UI periodically. If selectors stop working, run `--dry-run --url` to verify and check for UI changes.

