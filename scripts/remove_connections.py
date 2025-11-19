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
from linkedin_cleanup import connection_remover
from linkedin_cleanup.db import get_pending_urls, update_connection_status, get_all_connections
from linkedin_cleanup.utils import LinkedInClientError, print_banner, setup_linkedin_client, with_timeout

# Maximum time to spend on a single profile (20 seconds)
MAX_PROFILE_TIMEOUT = 20.0


async def process_batch(
    client,  # LinkedInClient (avoid circular import)
    urls: List[str],
    batch_num: int,
    total_batches: int,
    dry_run: bool
) -> bool:
    """Process a batch of connections.
    
    Returns:
        True if script should terminate (single timeout), False otherwise.
    """
    print_banner(f"BATCH {batch_num}/{total_batches} - Processing {len(urls)} connections")
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for idx, url in enumerate(urls, 1):
        print(f"\n[{idx}/{len(urls)}] 🔄 Processing: {url}")
        if dry_run:
            print("    [DRY RUN MODE - will not actually remove]")
        
        timestamp = datetime.now().isoformat()
        
        def on_timeout():
            """Update DB on timeout."""
            error_msg = f"Profile processing timeout after {MAX_PROFILE_TIMEOUT}s"
            update_connection_status(url, "failed", error_msg, timestamp)
        
        # Wrap entire profile processing in a timeout to prevent hanging
        async def process_single_profile():
            # Check connection status first
            status = await connection_remover.check_connection_status(client, url)
            
            if status == "not_connected":
                # Already not connected, update DB and skip
                update_connection_status(url, "not_connected", "Already not connected", timestamp)
                return "skipped", "Already not connected"
            elif status == "unknown":
                # Could not determine status, mark as failed
                update_connection_status(url, "failed", "Could not determine connection status", timestamp)
                return "failed", "Could not determine connection status"
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
                
                return db_status, message
            else:
                return "failed", f"Unknown status: {status}"
        
        try:
            result = await with_timeout(
                process_single_profile(),
                MAX_PROFILE_TIMEOUT,
                "Profile processing",
                on_timeout=on_timeout
            )
            
            if result is None:
                # Timeout occurred - terminate immediately
                return True  # Signal that script should terminate
            
            result_status, message = result
            if result_status == "skipped":
                skipped_count += 1
                print(f"    ⏭ Skipping: {message}")
            elif result_status == "success":
                success_count += 1
                print(f"    ✅ SUCCESS: {message}")
            else:
                failed_count += 1
                print(f"    ❌ FAILED: {message}")
        except Exception as e:
            # Unexpected error - mark as failed and continue
            error_msg = f"Unexpected error: {str(e)}"
            update_connection_status(url, "failed", error_msg, timestamp)
            failed_count += 1
            print(f"    ❌ ERROR: {error_msg} - skipping to next profile")
        
        # Delay before next connection (except for the last one)
        if idx < len(urls):
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
    
    return False  # Normal completion, continue processing


async def run_cleanup(dry_run: bool = False, num_batches: int = None):
    """Main execution function.
    
    Args:
        dry_run: If True, don't actually remove connections
        num_batches: If specified, process only this many batches (starting from batch 1)
    """
    print_banner("LINKEDIN CONNECTION CLEANUP")
    
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
    
    try:
        async with setup_linkedin_client() as client:
            # Process in batches
            total_batches = math.ceil(len(remaining) / config.BATCH_SIZE)
            
            # If num_batches is specified, limit processing to that many batches
            if num_batches is not None:
                if num_batches < 1:
                    print(f"❌ Error: Number of batches must be at least 1.")
                    return
                batches_to_process = min(num_batches, total_batches)
                print(f"📦 Processing {batches_to_process} batch(es) of {total_batches} total (up to {config.BATCH_SIZE} connections each)\n")
            else:
                batches_to_process = total_batches
                print(f"📦 Processing in {total_batches} batch(es) of up to {config.BATCH_SIZE} connections each\n")
            
            for batch_num in range(1, batches_to_process + 1):
                start_idx = (batch_num - 1) * config.BATCH_SIZE
                end_idx = min(start_idx + config.BATCH_SIZE, len(remaining))
                batch_urls = remaining[start_idx:end_idx]
                
                should_terminate = await process_batch(client, batch_urls, batch_num, total_batches, dry_run)
                
                # Check if we should terminate due to timeout
                if should_terminate:
                    print("\n🛑 Terminating script due to timeout.")
                    break  # Exit the batch loop
                
                # Wait between batches (except after the last one)
                if batch_num < batches_to_process:
                    delay = random.uniform(config.BATCH_DELAY_MIN, config.BATCH_DELAY_MAX)
                    print(f"\n⏳ Waiting {delay:.0f} seconds before next batch...")
                    await asyncio.sleep(delay)
                    print("✓ Delay complete, continuing to next batch...\n")
                    
            # Summary
            all_connections = get_all_connections()
            successful = sum(1 for conn in all_connections if conn['status'] == "success")
            failed = sum(1 for conn in all_connections if conn['status'] == "failed")
            not_connected = sum(1 for conn in all_connections if conn['status'] == "not_connected")
            print("📊 FINAL SUMMARY:")
            print(f"   ✅ Successful: {successful}")
            print(f"   ❌ Failed: {failed}")
            print(f"   ⏭ Not Connected: {not_connected}")
            print(f"   📁 Progress saved to: {config.PROGRESS_FILE}")
    except LinkedInClientError as e:
        print(f"\n❌ {e}")
        return


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
        "--batches",
        type=int,
        metavar="N",
        help="Process only the first N batches (works with or without --dry-run)"
    )
    args = parser.parse_args()
    
    # Handle single profile with --url
    if args.url:
        mode = "DRY RUN" if args.dry_run else "LIVE"
        print_banner(f"{mode} MODE - Single profile")
        print(f"🔗 URL: {args.url}\n")
        
        if args.dry_run:
            print("⚠️  DRY RUN MODE - Will test selectors but not remove connection\n")
        
        try:
            async with setup_linkedin_client() as client:
                print("🚀 Starting connection status check...\n")
            status = await connection_remover.check_connection_status(client, args.url)
            print(f"\n📊 Connection Status: {status}\n")
            
            if status == "connected":
                print("🔄 Connection found. Starting disconnection process...\n")
                success, message = await connection_remover.disconnect_connection(
                    client, args.url, args.dry_run
                )
                
                result = "✅ SUCCESS" if success else "❌ FAILED"
                print_banner(f"Result: {result}")
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
        except LinkedInClientError as e:
            print(f"\n❌ {e}")
            return
    
    # Normal batch run
    else:
        await run_cleanup(dry_run=args.dry_run, num_batches=args.batches)


if __name__ == "__main__":
    asyncio.run(main())
