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
- **Dry run removal**: Identifies More and Remove connection selectors without actually removing
- **Connection status check**: Determines if a profile is connected or not

### 2. Search Extraction (`test_search_extraction.py`)
- **Extract profiles from search page**: Traverses search results and extracts profile URLs and names
- **Pagination**: Uses pagination to fetch next page in search results

### 3. Utilities (`test_utils.py`)
- URL normalization
- Profile name cleaning

## Test Philosophy

These tests focus on the core functionality rather than exhaustive edge cases. Each test verifies a main use case with realistic scenarios.
