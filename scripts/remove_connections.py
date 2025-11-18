"""
LinkedIn Connection Cleanup Script
Removes connections from LinkedIn using Playwright automation.
"""
import argparse
import asyncio
import math
import random
from datetime import datetime
from typing import List

from linkedin_cleanup import config
from linkedin_cleanup.linkedin_client import LinkedInClient
from linkedin_cleanup import connection_remover
from linkedin_cleanup.db import get_pending_urls, update_connection_status, get_all_connections


def _print_banner(title: str):
    """Print a formatted banner."""
    print(f"\n{'='*80}")
    print(title)
    print(f"{'='*80}\n")




async def process_batch(
    client: LinkedInClient,
    urls: List[str],
    batch_num: int,
    total_batches: int,
    dry_run: bool
):
    """Process a batch of connections."""
    _print_banner(f"BATCH {batch_num}/{total_batches} - Processing {len(urls)} connections")
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for idx, url in enumerate(urls, 1):
        print(f"\n[{idx}/{len(urls)}] 🔄 Processing: {url}")
        if dry_run:
            print("    [DRY RUN MODE - will not actually remove]")
        
        # Check connection status first
        status = await connection_remover.check_connection_status(client, url)
        timestamp = datetime.now().isoformat()
        
        if status == "not_connected":
            # Already not connected, update DB and skip
            update_connection_status(url, "not_connected", "Already not connected", timestamp)
            skipped_count += 1
            print(f"    ⏭ Skipping: Already not connected")
            continue
        elif status == "unknown":
            # Could not determine status, mark as failed
            update_connection_status(url, "failed", "Could not determine connection status", timestamp)
            failed_count += 1
            print(f"    ❌ FAILED: Could not determine connection status")
            continue
        elif status == "connected":
            # Connected, proceed with disconnection
            if dry_run:
                print("    [DRY RUN] Would disconnect connection...")
            success, message = await connection_remover.disconnect_connection(
                client, url, dry_run=dry_run
            )
            
            # Update DB with result
            db_status = "success" if success else "failed"
            update_connection_status(url, db_status, message, timestamp)
            
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


async def run_cleanup(dry_run: bool = False):
    """Main execution function."""
    _print_banner("LINKEDIN CONNECTION CLEANUP")
    
    if dry_run:
        print("⚠️  DRY RUN MODE - No connections will actually be removed\n")
    
    # Load pending URLs from database
    print("📊 Loading pending URLs from database...")
    pending_urls = get_pending_urls()
    print(f"✓ Found {len(pending_urls)} pending URLs\n")
    
    if not pending_urls:
        print("✅ No pending URLs to process!")
        return
    
    # Limit to 5 profiles in dry-run mode
    if dry_run and len(pending_urls) > 5:
        print(f"📋 Pending URLs: {len(pending_urls)}")
        print(f"   ⚠️  DRY RUN: Limiting to first 5 profiles\n")
        remaining = pending_urls[:5]
    else:
        print(f"📋 Processing {len(pending_urls)} pending URLs\n")
        remaining = pending_urls
    
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
            
            await process_batch(client, batch_urls, batch_num, total_batches, dry_run)
            
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
        all_connections = get_all_connections()
        statuses = [conn['status'] for conn in all_connections]
        successful = statuses.count("success")
        failed = statuses.count("failed")
        not_connected = statuses.count("not_connected")
        print("📊 FINAL SUMMARY:")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   ⏭ Not Connected: {not_connected}")
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
            
            print("🚀 Starting connection status check...\n")
            status = await connection_remover.check_connection_status(client, args.url)
            print(f"\n📊 Connection Status: {status}\n")
            
            if status == "connected":
                print("🔄 Connection found. Starting disconnection process...\n")
                success, message = await connection_remover.disconnect_connection(
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
            elif status == "not_connected":
                print("ℹ️  Already not connected - no action needed.")
            else:
                print("⚠️  Could not determine connection status.")
        finally:
            print("\n🔒 Closing browser...")
            await client.close()
            print("✓ Browser closed")
    
    # Normal batch run
    else:
        await run_cleanup(dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
