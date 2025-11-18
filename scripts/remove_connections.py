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

from linkedin_cleanup import config
from linkedin_cleanup.linkedin_client import LinkedInClient
from linkedin_cleanup import connection_remover


def _print_banner(title: str):
    """Print a formatted banner."""
    print(f"\n{'='*80}")
    print(title)
    print(f"{'='*80}\n")


def _load_progress() -> Dict[str, Dict]:
    """Load progress from JSON file."""
    path = Path(config.PROGRESS_FILE)
    return json.loads(path.read_text()) if path.exists() else {}


def _save_progress(processed: Dict[str, Dict]):
    """Save progress to JSON file."""
    path = Path(config.PROGRESS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(processed, indent=2))


async def process_batch(
    client: LinkedInClient,
    urls: List[str],
    batch_num: int,
    total_batches: int,
    dry_run: bool,
    processed: Dict[str, Dict]
):
    """Process a batch of connections."""
    _print_banner(f"BATCH {batch_num}/{total_batches} - Processing {len(urls)} connections")
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for idx, url in enumerate(urls, 1):
        if url in processed and processed[url].get("status") == "success":
            print(f"\n[{idx}/{len(urls)}] ⏭ Skipping {url}")
            print(f"    (already processed successfully)")
            skipped_count += 1
            continue
        
        print(f"\n[{idx}/{len(urls)}] 🔄 Processing: {url}")
        if dry_run:
            print("    [DRY RUN MODE - will not actually remove]")
        
        success, message = await connection_remover.remove_connection(
            client, url, dry_run
        )
        
        timestamp = datetime.now().isoformat()
        processed[url] = {
            "status": "success" if success else "failed",
            "message": message,
            "timestamp": timestamp,
        }
        
        _save_progress(processed)  # Save after each connection
        
        if success:
            success_count += 1
            print(f"    ✅ SUCCESS: {message}")
        else:
            failed_count += 1
            print(f"    ❌ FAILED: {message}")
        
        # Delay before next connection (except for the last one)
        if idx < len(urls):
            delay = random.uniform(config.REMOVAL_DELAY_MIN, config.REMOVAL_DELAY_MAX)
            print(f"    ⏳ Waiting {delay:.1f}s before next connection...")
            await client.random_delay(
                config.REMOVAL_DELAY_MIN,
                config.REMOVAL_DELAY_MAX
            )
    
    print(f"\n{'='*60}")
    print(f"✓ Batch {batch_num} complete!")
    print(f"  • Successful: {success_count}")
    print(f"  • Failed: {failed_count}")
    print(f"  • Skipped: {skipped_count}")
    print(f"{'='*60}")


async def run_cleanup(input_csv: Optional[str] = None, dry_run: bool = False):
    """Main execution function."""
    _print_banner("LINKEDIN CONNECTION CLEANUP")
    
    if dry_run:
        print("⚠️  DRY RUN MODE - No connections will actually be removed\n")
    
    # Load connections from CSV
    csv_path = input_csv or config.OUTPUT_CSV
    print(f"📂 Loading connections from: {csv_path}")
    df = pd.read_csv(csv_path)
    urls = df["URL"].tolist()
    print(f"✓ Found {len(urls)} total connections in CSV\n")
    
    # Load progress
    print("📊 Loading progress from previous runs...")
    processed = _load_progress()
    already_processed = sum(1 for v in processed.values() if v.get("status") == "success")
    print(f"✓ Found {already_processed} already processed connections\n")
    
    # Filter out already processed/skipped ones
    remaining = [
        url for url in urls
        if url not in processed
        or processed[url].get("status") not in ("success", "skipped")
    ]
    print(f"📋 Remaining to process: {len(remaining)}")
    print(f"   (Skipping {len(urls) - len(remaining)} already processed)\n")
    
    if not remaining:
        print("✅ All connections have already been processed successfully!")
        return
    
    client = LinkedInClient()
    
    # Setup browser
    print("🌐 Setting up browser...")
    await client.setup_browser()
    print("✓ Browser ready\n")
    
    try:
        # Ensure logged in
        print("🔐 Checking login status...")
        if not await client.ensure_logged_in():
            print("✗ Failed to log in. Exiting.")
            return
        print("✓ Logged in successfully\n")
        
        # Process in batches
        total_batches = math.ceil(len(remaining) / config.BATCH_SIZE)
        print(f"📦 Processing in {total_batches} batch(es) of up to {config.BATCH_SIZE} connections each\n")
        
        for batch_num in range(1, total_batches + 1):
            start_idx = (batch_num - 1) * config.BATCH_SIZE
            end_idx = min(start_idx + config.BATCH_SIZE, len(remaining))
            batch_urls = remaining[start_idx:end_idx]
            
            await process_batch(client, batch_urls, batch_num, total_batches, dry_run, processed)
            
            # Wait between batches (except after the last one)
            if batch_num < total_batches:
                delay = random.uniform(
                    config.BATCH_DELAY_MIN,
                    config.BATCH_DELAY_MAX
                )
                print(f"\n⏳ Waiting {delay:.0f} seconds before next batch...")
                await asyncio.sleep(delay)
                print("✓ Delay complete, continuing to next batch...\n")
        
        _print_banner("ALL BATCHES COMPLETE!")
        
        # Summary
        statuses = [v.get("status") for v in processed.values()]
        successful = statuses.count("success")
        failed = statuses.count("failed")
        print("📊 FINAL SUMMARY:")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📁 Progress saved to: {config.PROGRESS_FILE}")
    
    finally:
        print("\n🔒 Closing browser...")
        await client.close()
        print("✓ Browser closed")


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
        "--url",
        type=str,
        metavar="URL",
        help="Process a specific profile URL (works with or without --dry-run)"
    )
    parser.add_argument(
        "--input-csv",
        type=str,
        metavar="CSV",
        help=f"Input CSV file with connections to remove (default: {config.OUTPUT_CSV})"
    )
    args = parser.parse_args()
    
    # Handle single profile with --url
    if args.url:
        mode = "DRY RUN" if args.dry_run else "LIVE"
        _print_banner(f"{mode} MODE - Single profile")
        print(f"🔗 URL: {args.url}\n")
        
        if args.dry_run:
            print("⚠️  DRY RUN MODE - Will test selectors but not remove connection\n")
        
        client = LinkedInClient()
        print("🌐 Setting up browser...")
        await client.setup_browser()
        print("✓ Browser ready\n")
        
        try:
            print("🔐 Checking login status...")
            if not await client.ensure_logged_in():
                print("✗ Failed to log in. Exiting.")
                return
            print("✓ Logged in successfully\n")
            
            print("🚀 Starting connection removal process...\n")
            success, message = await connection_remover.remove_connection(
                client, args.url, args.dry_run
            )
            
            result = "✅ SUCCESS" if success else "❌ FAILED"
            _print_banner(f"Result: {result}")
            print(f"📝 Message: {message}\n")
            
            if success and not args.dry_run:
                print("✅ Connection successfully removed!")
                print("\n⏳ Browser will stay open for 10 seconds so you can verify the removal.")
                print("   Check that the 'Connect' button is visible on the profile page.")
                await asyncio.sleep(10)
            elif success and args.dry_run:
                print("✅ All selectors working correctly!")
                print("   The connection would be removed in LIVE mode.")
            else:
                print("❌ Failed. Check the error message above.")
        finally:
            print("\n🔒 Closing browser...")
            await client.close()
            print("✓ Browser closed")
    
    # Normal batch run
    else:
        await run_cleanup(input_csv=args.input_csv, dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
