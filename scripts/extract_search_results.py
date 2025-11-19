"""
LinkedIn Search Results Extractor
Extracts profile names and URLs from LinkedIn search results without accessing individual profiles.
"""

import argparse
import asyncio
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from linkedin_cleanup import config
from linkedin_cleanup.logging_config import setup_logging
from linkedin_cleanup.random_actions import perform_random_action, random_delay
from linkedin_cleanup.search_extractor import SearchExtractor
from linkedin_cleanup.utils import (
    LinkedInClientError,
    print_banner,
    setup_linkedin_client,
    with_timeout,
)

logger = setup_logging()

# Maximum time to spend on a single page (30 seconds)
MAX_PAGE_TIMEOUT = 30.0


async def extract_all_profiles(
    client, search_url: str, max_pages: int = None
) -> list[tuple[str, str, str]]:
    """Extract all profiles from search results, handling pagination."""
    all_profiles = []
    seen_urls: set[str] = set()
    page_num = 1
    page_limit = max_pages if max_pages is not None else config.MAX_PAGES

    await client.navigate_to(search_url)
    await random_delay()

    extractor = SearchExtractor(client)

    with tqdm(desc="Extracting profiles", unit="page", initial=0) as pbar:
        while True:
            pbar.set_description(f"Page {page_num}")

            page_profiles = await with_timeout(
                extractor.extract_profiles_from_page(), MAX_PAGE_TIMEOUT, "Page extraction"
            )
            if page_profiles is None or not page_profiles:
                break

            new_count = sum(1 for _, url, _ in page_profiles if url not in seen_urls)
            for name, url, location in page_profiles:
                if url not in seen_urls:
                    all_profiles.append((name, url, location))
                    seen_urls.add(url)

            pbar.set_postfix(profiles=len(all_profiles), new=new_count)
            logger.info(f"Page {page_num}: {new_count} new profiles (total: {len(all_profiles)})")

            if page_num >= page_limit:
                break

            success = await with_timeout(
                extractor.go_to_next_page(), MAX_PAGE_TIMEOUT, "Next page navigation"
            )
            if success is None or not success:
                break

            await perform_random_action(client, new_tab=True)
            page_num += 1
            pbar.update(1)

    return all_profiles


async def run_extraction(
    search_url: str, output_csv: str = None, dry_run: bool = False, max_pages: int = None
):
    """Main execution function."""
    print_banner("LINKEDIN SEARCH RESULTS EXTRACTOR")
    logger.info(f"Search URL: {search_url}")
    if max_pages:
        logger.info(f"Max pages: {max_pages}")

    try:
        async with setup_linkedin_client() as client:
            all_profiles = await extract_all_profiles(client, search_url, max_pages=max_pages)

            logger.info(f"{'='*80}")
            logger.info(f"Extracted {len(all_profiles)} profiles")
            logger.info(f"{'='*80}")
            for idx, (name, url, location) in enumerate(all_profiles, 1):
                logger.info(f"{idx:4d}. {name:40s} | {location:30s} | {url}")
            logger.info(f"{'='*80}")

            if not dry_run:
                df = pd.DataFrame(all_profiles, columns=["Name", "URL", "Location"])
                output_path = Path(output_csv)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                df.to_csv(output_path, index=False)
                logger.info(f"Saved to: {output_csv}")

            print_banner("EXTRACTION COMPLETE!")
    except LinkedInClientError as e:
        logger.error(f"LinkedIn client error: {e}")
        return


async def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="LinkedIn Search Results Extractor")
    parser.add_argument("--search-url", type=str, default=config.DEFAULT_SEARCH_URL)
    parser.add_argument("--output", type=str, default=config.DEFAULT_OUTPUT_CSV)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-pages", type=int, default=None)
    args = parser.parse_args()

    max_pages = args.max_pages
    if args.dry_run and max_pages is None:
        max_pages = 2

    await run_extraction(
        args.search_url,
        args.output if not args.dry_run else None,
        dry_run=args.dry_run,
        max_pages=max_pages,
    )


if __name__ == "__main__":
    asyncio.run(main())
