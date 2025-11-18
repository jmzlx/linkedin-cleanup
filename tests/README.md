# Tests

High-quality tests covering the main use cases.

## Running Tests

```bash
# Install dependencies first
uv sync

# Run all tests
pytest

# Run with verbose output
pytest -v
```

## Test Coverage

### 1. Connection Removal (`test_connection_removal.py`)
- **Check connection status**: Tests checking if a profile is connected, not connected, or unknown
- **Disconnect connection (dry run)**: Tests dry run disconnection - identifies More and Remove connection selectors without actually removing
- **Find More button**: Tests the helper function for finding the More button

### 2. Database (`test_db.py`)
- **Update and get connection status**: Tests updating and retrieving connection status from SQLite
- **Get pending URLs**: Tests querying for URLs with pending status
- **Get all connections**: Tests retrieving all connections for summary stats
- **Status overwrite**: Tests that updating a connection overwrites previous status
- **Non-existent URL**: Tests handling of non-existent URLs

### 3. Search Extraction (`test_search_extraction.py`)
- **Extract profiles from search page**: Traverses search results and extracts profile URLs and names
- **Pagination**: Uses pagination to fetch next page in search results

### 4. Utilities (`test_utils.py`)
- URL normalization
- Profile name cleaning

## Test Philosophy

These tests focus on the core functionality rather than exhaustive edge cases. Each test verifies a main use case with realistic scenarios.
