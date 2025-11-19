"""
LinkedIn Connection Cleanup Script
Removes connections from LinkedIn using Playwright automation.
"""
import argparse
import asyncio
from datetime import datetime
from typing import Tuple

from linkedin_cleanup import config
from linkedin_cleanup.connection_remover import ConnectionRemover
from linkedin_cleanup.db import get_pending_urls, update_connection_status, get_all_connections
from linkedin_cleanup.random_actions import perform_random_action, random_delay
from linkedin_cleanup.utils import LinkedInClientError, print_banner, setup_linkedin_client, with_timeout

# Maximum time to spend on a single profile (20 seconds)
MAX_PROFILE_TIMEOUT = 20.0


async def process_single_profile(
    client,
    url: str,
    dry_run: bool,
    timestamp: str
) -> Tuple[str, str]:
    """Process a single profile connection removal."""
    remover = ConnectionRemover(client)
    status = await remover.check_connection_status(url)
    
    match status:
        case "not_connected":
            update_connection_status(url, "not_connected", "Already not connected", timestamp)
            return "skipped", "Already not connected"
        
        case "unknown":
            update_connection_status(url, "failed", "Could not determine connection status", timestamp)
            return "failed", "Could not determine connection status"
        
        case "connected":
            success, message = await remover.disconnect_connection(url, dry_run=dry_run)
            if not dry_run:
                db_status = "success" if success else "failed"
                update_connection_status(url, db_status, message, timestamp)
            return ("success" if success else "failed"), message
        
        case _:
            update_connection_status(url, "failed", f"Unknown status: {status}", timestamp)
            return "failed", f"Unknown status: {status}"


async def run_cleanup(dry_run: bool = False, num_profiles: int = None):
    """Main execution function."""
    print_banner("LINKEDIN CONNECTION CLEANUP")
    if dry_run:
        print("⚠️  DRY RUN MODE\n")
    
    pending_urls = get_pending_urls()
    print(f"Found {len(pending_urls)} pending URLs\n")
    
    if not pending_urls:
        print("✅ No pending URLs to process!")
        return
    
    remaining = pending_urls
    
    if dry_run and len(remaining) > 5:
        print(f"DRY RUN: Limiting to first 5 profiles\n")
        remaining = remaining[:5]
    
    if num_profiles is not None:
        if num_profiles < 1:
            print(f"❌ Error: Number of profiles must be at least 1.")
            return
        remaining = remaining[:num_profiles]
    
    try:
        async with setup_linkedin_client() as client:
            success_count = 0
            failed_count = 0
            skipped_count = 0
            
            for idx, url in enumerate(remaining, 1):
                print(f"[{idx}/{len(remaining)}] {url}")
                timestamp = datetime.now().isoformat()
                
                def on_timeout():
                    update_connection_status(url, "failed", f"Timeout after {MAX_PROFILE_TIMEOUT}s", timestamp)
                
                try:
                    result = await with_timeout(
                        process_single_profile(client, url, dry_run, timestamp),
                        MAX_PROFILE_TIMEOUT,
                        "Profile processing",
                        on_timeout=on_timeout
                    )
                    
                    if result is None:
                        print("\n🛑 Terminating script due to timeout.")
                        break
                    
                    result_status, message = result
                    if result_status == "skipped":
                        skipped_count += 1
                        print(f"  ⏭ {message}")
                    elif result_status == "success":
                        success_count += 1
                        print(f"  ✅ {message}")
                    else:
                        failed_count += 1
                        print(f"  ❌ {message}")
                        
                except Exception as e:
                    update_connection_status(url, "failed", f"Unexpected error: {str(e)}", timestamp)
                    failed_count += 1
                    print(f"  ❌ Error: {str(e)}")
                
                await perform_random_action(client)
                if idx < len(remaining):
                    await random_delay()
            
            print(f"\n{'='*60}")
            print(f"Successful: {success_count} | Failed: {failed_count} | Skipped: {skipped_count}")
            print(f"{'='*60}")
            
            all_connections = get_all_connections()
            successful = sum(1 for conn in all_connections if conn['status'] == "success")
            failed = sum(1 for conn in all_connections if conn['status'] == "failed")
            not_connected = sum(1 for conn in all_connections if conn['status'] == "not_connected")
            print(f"\nTotal: ✅ {successful} | ❌ {failed} | ⏭ {not_connected}")
            print(f"Progress saved to: {config.PROGRESS_FILE}")
    except LinkedInClientError as e:
        print(f"\n❌ {e}")
        return


async def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="LinkedIn Connection Cleanup")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--url", type=str, metavar="URL")
    parser.add_argument("--profiles", type=int, metavar="N")
    args = parser.parse_args()
    
    if args.url:
        mode = "DRY RUN" if args.dry_run else "LIVE"
        print_banner(f"{mode} MODE - Single profile")
        print(f"URL: {args.url}\n")
        
        try:
            async with setup_linkedin_client() as client:
                remover = ConnectionRemover(client)
                status = await remover.check_connection_status(args.url)
                print(f"Connection Status: {status}\n")
                
                if status == "connected":
                    success, message = await remover.disconnect_connection(args.url, args.dry_run)
                    result = "✅ SUCCESS" if success else "❌ FAILED"
                    print_banner(f"Result: {result}")
                    print(f"Message: {message}\n")
                    
                    if success and not args.dry_run:
                        print("✅ Connection successfully removed!")
                        print("Browser will stay open for 10 seconds for verification.")
                        await asyncio.sleep(10)
                    elif success and args.dry_run:
                        print("✅ All selectors working correctly!")
                elif status == "not_connected":
                    print("ℹ️  Already not connected - no action needed.")
                else:
                    print("⚠️  Could not determine connection status.")
        except LinkedInClientError as e:
            print(f"\n❌ {e}")
            return
    else:
        await run_cleanup(dry_run=args.dry_run, num_profiles=args.profiles)


if __name__ == "__main__":
    asyncio.run(main())
