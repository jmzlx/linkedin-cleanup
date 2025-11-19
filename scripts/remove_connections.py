"""
LinkedIn Connection Cleanup Script
Removes connections from LinkedIn using Playwright automation.
"""
import argparse
import asyncio
from datetime import datetime
from typing import Tuple

from linkedin_cleanup import config
from linkedin_cleanup import connection_remover
from linkedin_cleanup.db import get_pending_urls, update_connection_status, get_all_connections
from linkedin_cleanup.random_actions import perform_random_action
from linkedin_cleanup.utils import LinkedInClientError, print_banner, setup_linkedin_client, with_timeout

# Maximum time to spend on a single profile (20 seconds)
MAX_PROFILE_TIMEOUT = 20.0


async def process_single_profile(
    client,
    url: str,
    dry_run: bool,
    timestamp: str
) -> Tuple[str, str]:
    """Process a single profile connection removal.
    
    Returns:
        Tuple of (status, message) where status is 'success', 'failed', or 'skipped'
    """
    # Check connection status first
    status = await connection_remover.check_connection_status(client, url)
    
    if status == "not_connected":
        update_connection_status(url, "not_connected", "Already not connected", timestamp)
        return "skipped", "Already not connected"
    
    if status == "unknown":
        update_connection_status(url, "failed", "Could not determine connection status", timestamp)
        return "failed", "Could not determine connection status"
    
    if status == "connected":
        success, message = await connection_remover.disconnect_connection(
            client, url, dry_run=dry_run
        )
        
        db_status = "success" if success else "failed"
        update_connection_status(url, db_status, message, timestamp)
        return db_status, message
    
    # Fallback for unexpected status
    update_connection_status(url, "failed", f"Unknown status: {status}", timestamp)
    return "failed", f"Unknown status: {status}"


async def run_cleanup(dry_run: bool = False, num_profiles: int = None):
    """Main execution function.
    
    Args:
        dry_run: If True, don't actually remove connections
        num_profiles: If specified, process only this many profiles (starting from the first)
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
    
    # Determine which profiles to process
    remaining = pending_urls
    
    # Limit to 5 profiles in dry-run mode
    if dry_run and len(remaining) > 5:
        print(f"📋 Pending URLs: {len(pending_urls)}")
        print(f"   ⚠️  DRY RUN: Limiting to first 5 profiles\n")
        remaining = remaining[:5]
    else:
        print(f"📋 Processing {len(pending_urls)} pending URLs\n")
    
    # Limit to num_profiles if specified
    if num_profiles is not None:
        if num_profiles < 1:
            print(f"❌ Error: Number of profiles must be at least 1.")
            return
        remaining = remaining[:num_profiles]
        print(f"📦 Processing first {len(remaining)} profile(s)\n")
    
    try:
        async with setup_linkedin_client() as client:
            success_count = 0
            failed_count = 0
            skipped_count = 0
            
            for idx, url in enumerate(remaining, 1):
                print(f"\n[{idx}/{len(remaining)}] 🔄 Processing: {url}")
                timestamp = datetime.now().isoformat()
                
                def on_timeout():
                    """Update DB on timeout."""
                    error_msg = f"Profile processing timeout after {MAX_PROFILE_TIMEOUT}s"
                    update_connection_status(url, "failed", error_msg, timestamp)
                
                try:
                    result = await with_timeout(
                        process_single_profile(client, url, dry_run, timestamp),
                        MAX_PROFILE_TIMEOUT,
                        "Profile processing",
                        on_timeout=on_timeout
                    )
                    
                    if result is None:
                        # Timeout occurred - terminate immediately
                        print("\n🛑 Terminating script due to timeout.")
                        break
                    
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
                
                # Attempt random action (function decides internally based on probability)
                await perform_random_action(client)
                
                # Delay before next connection (except for the last one)
                if idx < len(remaining):
                    await client.random_delay(
                        config.REMOVAL_DELAY_MIN,
                        config.REMOVAL_DELAY_MAX
                    )
            
            # Summary
            print(f"\n{'='*60}")
            print("✓ Processing complete!")
            print(f"  • Successful: {success_count}")
            print(f"  • Failed: {failed_count}")
            print(f"  • Skipped: {skipped_count}")
            print(f"{'='*60}")
            
            all_connections = get_all_connections()
            successful = sum(1 for conn in all_connections if conn['status'] == "success")
            failed = sum(1 for conn in all_connections if conn['status'] == "failed")
            not_connected = sum(1 for conn in all_connections if conn['status'] == "not_connected")
            print("\n📊 FINAL SUMMARY:")
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
        "--profiles",
        type=int,
        metavar="N",
        help="Process only the first N profiles (works with or without --dry-run)"
    )
    args = parser.parse_args()
    
    # Handle single profile with --url
    if args.url:
        mode = "DRY RUN" if args.dry_run else "LIVE"
        print_banner(f"{mode} MODE - Single profile")
        print(f"🔗 URL: {args.url}\n")
        
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
    
    # Normal profile processing run
    else:
        await run_cleanup(dry_run=args.dry_run, num_profiles=args.profiles)


if __name__ == "__main__":
    asyncio.run(main())
