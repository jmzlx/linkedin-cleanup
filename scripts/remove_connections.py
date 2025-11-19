"""
LinkedIn Connection Cleanup Script
Removes connections from LinkedIn using Playwright automation.
"""

import argparse
import asyncio
from datetime import datetime

from tqdm.asyncio import tqdm

from linkedin_cleanup import config
from linkedin_cleanup.connection_remover import ConnectionRemover
from linkedin_cleanup.constants import ConnectionStatus
from linkedin_cleanup.db import get_all_connections, get_pending_urls, update_connection_status
from linkedin_cleanup.logging_config import setup_logging
from linkedin_cleanup.random_actions import perform_random_action, random_delay
from linkedin_cleanup.utils import (
    LinkedInClientError,
    print_banner,
    setup_linkedin_client,
    with_timeout,
)

logger = setup_logging()

# Maximum time to spend on a single profile (20 seconds)
MAX_PROFILE_TIMEOUT = 20.0


async def process_single_profile(
    client, url: str, dry_run: bool, timestamp: str
) -> tuple[str, str]:
    """Process a single profile connection removal."""
    remover = ConnectionRemover(client)
    status, success, message = await remover.process_connection_removal(url, dry_run=dry_run)

    match status:
        case ConnectionStatus.NOT_CONNECTED:
            update_connection_status(
                url, ConnectionStatus.NOT_CONNECTED, message, timestamp
            )
            return "skipped", message

        case ConnectionStatus.UNKNOWN:
            update_connection_status(
                url, ConnectionStatus.FAILED, message, timestamp
            )
            return "failed", message

        case ConnectionStatus.CONNECTED:
            if not dry_run:
                db_status = ConnectionStatus.SUCCESS if success else ConnectionStatus.FAILED
                update_connection_status(url, db_status, message, timestamp)
            return ("success" if success else "failed"), message

        case _:
            update_connection_status(
                url, ConnectionStatus.FAILED, message, timestamp
            )
            return "failed", message


async def run_cleanup(dry_run: bool = False, num_profiles: int = None):
    """Main execution function."""
    print_banner("LINKEDIN CONNECTION CLEANUP")
    if dry_run:
        logger.warning("DRY RUN MODE")

    pending_urls = get_pending_urls()
    logger.info(f"Found {len(pending_urls)} pending URLs")

    if not pending_urls:
        logger.info("No pending URLs to process!")
        return

    remaining = pending_urls

    if dry_run and len(remaining) > 5:
        logger.info("DRY RUN: Limiting to first 5 profiles")
        remaining = remaining[:5]

    if num_profiles is not None:
        if num_profiles < 1:
            logger.error("Number of profiles must be at least 1")
            return
        remaining = remaining[:num_profiles]

    try:
        async with setup_linkedin_client() as client:
            success_count = 0
            failed_count = 0
            skipped_count = 0

            with tqdm(total=len(remaining), desc="Processing profiles", unit="profile") as pbar:
                for idx, url in enumerate(remaining, 1):
                    pbar.set_description(f"Processing {url[:50]}...")
                    timestamp = datetime.now().isoformat()

                    def on_timeout(url=url, timestamp=timestamp):
                        update_connection_status(
                            url,
                            ConnectionStatus.FAILED,
                            f"Timeout after {MAX_PROFILE_TIMEOUT}s",
                            timestamp,
                        )

                    try:
                        result = await with_timeout(
                            process_single_profile(client, url, dry_run, timestamp),
                            MAX_PROFILE_TIMEOUT,
                            "Profile processing",
                            on_timeout=on_timeout,
                        )

                        if result is None:
                            logger.error("Terminating script due to timeout")
                            break

                        result_status, message = result
                        if result_status == "skipped":
                            skipped_count += 1
                            pbar.set_postfix(
                                status="skipped", success=success_count, failed=failed_count
                            )
                            logger.info(f"  ⏭ {message}")
                        elif result_status == "success":
                            success_count += 1
                            pbar.set_postfix(
                                status="success", success=success_count, failed=failed_count
                            )
                            logger.info(f"  ✅ {message}")
                        else:
                            failed_count += 1
                            pbar.set_postfix(
                                status="failed", success=success_count, failed=failed_count
                            )
                            logger.error(f"  ❌ {message}")

                    except Exception as e:
                        update_connection_status(
                            url, ConnectionStatus.FAILED, f"Unexpected error: {str(e)}", timestamp
                        )
                        failed_count += 1
                        pbar.set_postfix(status="error", success=success_count, failed=failed_count)
                        logger.exception(f"Error processing {url}: {e}")

                    await perform_random_action(client)
                    if idx < len(remaining):
                        await random_delay()

                    pbar.update(1)

            logger.info(f"{'='*60}")
            logger.info(
                f"Successful: {success_count} | Failed: {failed_count} | Skipped: {skipped_count}"
            )
            logger.info(f"{'='*60}")

            all_connections = get_all_connections()
            successful = sum(
                1 for conn in all_connections if conn["status"] == ConnectionStatus.SUCCESS.value
            )
            failed = sum(
                1 for conn in all_connections if conn["status"] == ConnectionStatus.FAILED.value
            )
            not_connected = sum(
                1
                for conn in all_connections
                if conn["status"] == ConnectionStatus.NOT_CONNECTED.value
            )
            logger.info(f"Total: ✅ {successful} | ❌ {failed} | ⏭ {not_connected}")
            logger.info(f"Progress saved to: {config.PROGRESS_FILE}")
    except LinkedInClientError as e:
        logger.error(f"LinkedIn client error: {e}")
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
        logger.info(f"URL: {args.url}")

        try:
            async with setup_linkedin_client() as client:
                remover = ConnectionRemover(client)
                status, success, message = await remover.process_connection_removal(
                    args.url, dry_run=args.dry_run
                )
                logger.info(f"Connection Status: {status.value}")

                if status == ConnectionStatus.CONNECTED:
                    result = "✅ SUCCESS" if success else "❌ FAILED"
                    print_banner(f"Result: {result}")
                    logger.info(f"Message: {message}")

                    if success and not args.dry_run:
                        logger.info("Connection successfully removed!")
                        logger.info("Browser will stay open for 10 seconds for verification.")
                        await asyncio.sleep(10)
                    elif success and args.dry_run:
                        logger.info("All selectors working correctly!")
                elif status == ConnectionStatus.NOT_CONNECTED:
                    logger.info(message)
                else:
                    logger.warning(message)
        except LinkedInClientError as e:
            logger.error(f"LinkedIn client error: {e}")
            return
    else:
        await run_cleanup(dry_run=args.dry_run, num_profiles=args.profiles)


if __name__ == "__main__":
    asyncio.run(main())
