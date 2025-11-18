# LinkedIn Connection Cleanup

Automated tool to remove LinkedIn connections using Playwright. Processes connections in batches with bot detection avoidance.

## Setup

1. **Install dependencies:**
   ```bash
   uv sync
   # or
   pip install -r requirements.txt
   ```

2. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   ```

## Usage

### Test Selectors First (Recommended)

Before running the full cleanup, test that selectors work on a single profile:

```bash
python linkedin_cleanup.py --dry-run --test-url "https://www.linkedin.com/in/USERNAME"
```

This will:
- Open a browser window
- Allow you to log in manually (first time)
- Navigate to the test profile
- Verify selectors work (without actually removing the connection)

### Run the Cleanup Script

```bash
# Dry run: Test on all connections without removing
python linkedin_cleanup.py --dry-run

# Live run: Actually remove connections
python linkedin_cleanup.py
```

The script will:
1. Load connections from `data/output.csv`
2. Check for saved cookies (if you've logged in before)
3. If no cookies, open browser for manual login
4. Process connections in batches of 10
5. Require confirmation between batches
6. Save progress after each connection

## Features

- **Manual Login**: First run requires manual login, then cookies are saved for future runs
- **Batch Processing**: Processes 10 connections at a time with breaks
- **Progress Tracking**: Saves progress to `data/processed_connections.json` to allow resuming
- **Bot Detection Avoidance**:
  - Random delays between actions (5-10 seconds)
  - Longer delays between batches (2-3 minutes)
  - Human-like mouse movements
  - Stealth browser settings
- **Error Handling**: Continues processing even if individual connections fail
- **Resume Capability**: Skips already successfully processed connections

## Files

- `linkedin_cleanup.py` - Main automation script with built-in dry-run mode
- `data/linkedin_cookies.json` - Saved authentication cookies (gitignored)
- `data/processed_connections.json` - Progress tracking (gitignored)
- `data/output.csv` - Input file with connections to remove

## Configuration

You can modify these constants in `linkedin_cleanup.py`:

- `BATCH_SIZE`: Number of connections per batch (default: 10)
- `DELAY_MIN` / `DELAY_MAX`: Random delay between actions in seconds (default: 5-10)
- `BATCH_DELAY_MIN` / `BATCH_DELAY_MAX`: Delay between batches in seconds (default: 120-180)

## Notes

- The browser window will remain visible during execution
- If the script is interrupted, you can resume and it will skip already processed connections
- Failed connections are logged but don't stop the process
- Make sure you have a stable internet connection

## Troubleshooting

- **Can't find "More" button**: Run with `--dry-run --test-url` to verify selectors. If they fail, LinkedIn may have updated their UI
- **Login issues**: Delete `data/linkedin_cookies.json` and log in again
- **Connection already removed**: The script will detect this and skip it
- **Rate limiting**: If LinkedIn shows warnings, increase the delays in the configuration
- **Test before running**: Always use `--dry-run` first to verify everything works

## Tested Working Selectors

These selectors have been tested and confirmed working with the current LinkedIn interface:

- **More Button**: `button.artdeco-dropdown__trigger`
- **Remove Connection Option**: `div[role="button"][aria-label*="Remove your connection"]`

**Note**: LinkedIn updates their UI periodically. If selectors stop working, run `--dry-run --test-url` to verify and check for UI changes.

