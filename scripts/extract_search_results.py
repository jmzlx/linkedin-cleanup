"""
LinkedIn Search Results Extractor
Extracts profile names and URLs from LinkedIn search results without accessing individual profiles.
"""
import argparse
import asyncio
from pathlib import Path
from typing import List, Set, Tuple

import pandas as pd

from linkedin_cleanup import config
from linkedin_cleanup import search_extractor
from linkedin_cleanup.utils import LinkedInClientError, print_banner, setup_linkedin_client, with_timeout

# Maximum time to spend on a single page (30 seconds)
MAX_PAGE_TIMEOUT = 30.0


async def extract_all_profiles(client, search_url: str, max_pages: int = None) -> List[Tuple[str, str, str]]:
    # client: LinkedInClient (avoid circular import)
    """Extract all profiles from search results, handling pagination.
    Returns list of (name, url, location) tuples.
    Deduplicates within a single run by URL.
    
    Args:
        client: LinkedIn client instance
        search_url: URL to search results page
        max_pages: Maximum number of pages to extract (None = no limit except config.MAX_PAGES)
    """
    all_profiles = []
    seen_urls: Set[str] = set()
    page_num = 1
    page_limit = max_pages if max_pages is not None else config.MAX_PAGES
    
    # Navigate to search URL
    print(f"\n📍 Navigating to search URL: {search_url}")
    await client.navigate_to(search_url)
    
    # Wait a bit for page to load
    print("⏳ Waiting for page to load...")
    await client.random_delay(2, 3)
    print("✓ Page loaded\n")
    
    while True:
        print(f"\n{'='*60}")
        print(f"📄 PAGE {page_num}")
        print(f"{'='*60}")
        
        # Extract profiles from current page with timeout
        page_profiles = await with_timeout(
            search_extractor.extract_profiles_from_page(client),
            MAX_PAGE_TIMEOUT,
            "Page extraction"
        )
        if page_profiles is None or not page_profiles:
            if page_profiles is None:
                break  # Timeout
            print(f"\n⚠ No profiles found on page {page_num}. Stopping extraction.")
            break
        
        # Add new profiles (avoid duplicates within this run)
        new_count = 0
        duplicate_count = 0
        for name, url, location in page_profiles:
            if url not in seen_urls:
                all_profiles.append((name, url, location))
                seen_urls.add(url)
                new_count += 1
            else:
                duplicate_count += 1
        
        print(f"\n📊 Page {page_num} Summary:")
        print(f"   • Total profiles on page: {len(page_profiles)}")
        print(f"   • New profiles: {new_count}")
        if duplicate_count > 0:
            print(f"   • Duplicates skipped: {duplicate_count}")
        print(f"   • Total profiles collected so far: {len(all_profiles)}")
        
        # Check if we've reached the page limit
        if page_num >= page_limit:
            print(f"\n⚠ Reached page limit ({page_limit}). Stopping extraction.")
            break
        
        # Try to go to next page (go_to_next_page already checks if button is enabled)
        print(f"\n🔍 Attempting to navigate to next page...")
        success = await with_timeout(
            search_extractor.go_to_next_page(client),
            MAX_PAGE_TIMEOUT,
            "Next page navigation"
        )
        if success is None or not success:
            if success is None:
                break  # Timeout
            print("✓ No more pages available. Extraction complete.")
            break
        
        page_num += 1
    
    return all_profiles


async def run_extraction(search_url: str, output_csv: str = None, dry_run: bool = False, max_pages: int = None):
    """Main execution function.
    
    Args:
        search_url: LinkedIn search results URL
        output_csv: Path to output CSV file (ignored if dry_run=True)
        dry_run: If True, don't save to CSV, just print results
        max_pages: Maximum number of pages to extract
    """
    print_banner("LINKEDIN SEARCH RESULTS EXTRACTOR")
    
    print(f"🔗 Search URL: {search_url}")
    if dry_run:
        print(f"🧪 DRY RUN MODE - No CSV will be saved")
    else:
        print(f"💾 Output CSV: {output_csv}")
    if max_pages:
        print(f"📄 Max pages: {max_pages}")
    print()
    
    try:
        async with setup_linkedin_client() as client:
            # Extract all profiles
            print("🚀 Starting profile extraction...")
            all_profiles = await extract_all_profiles(client, search_url, max_pages=max_pages)
            
            # Print all profiles to terminal
            print(f"\n{'='*80}")
            print(f"📋 EXTRACTED PROFILES ({len(all_profiles)} total)")
            print(f"{'='*80}")
            for idx, (name, url, location) in enumerate(all_profiles, 1):
                print(f"{idx:4d}. {name:40s} | {location:30s} | {url}")
            print(f"{'='*80}\n")
            
            if not dry_run:
                # Save to CSV using pandas
                print(f"💾 Saving {len(all_profiles)} profiles to CSV...")
                df = pd.DataFrame(all_profiles, columns=['Name', 'URL', 'Location'])
                output_path = Path(output_csv)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                df.to_csv(output_path, index=False)
                print(f"✓ Saved to: {output_csv}")
            else:
                print(f"🧪 DRY RUN: Skipping CSV save")
            
            print_banner("EXTRACTION COMPLETE!")
            print(f"✅ Total profiles extracted: {len(all_profiles)}")
            if not dry_run:
                print(f"📁 CSV saved to: {output_csv}")
            else:
                print(f"🧪 DRY RUN: No file saved")
    except LinkedInClientError as e:
        print(f"\n❌ {e}")
        return


async def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="LinkedIn Search Results Extractor - Extract profile URLs from search results"
    )
    parser.add_argument(
        "--search-url",
        type=str,
        default=config.DEFAULT_SEARCH_URL,
        help=f"LinkedIn search results URL (default: {config.DEFAULT_SEARCH_URL.replace('%', '%%')})"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=config.DEFAULT_OUTPUT_CSV,
        help=f"Output CSV file path (default: {config.DEFAULT_OUTPUT_CSV})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode: don't save to CSV, just print results to terminal"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help=f"Maximum number of pages to extract (default: no limit except config.MAX_PAGES={config.MAX_PAGES}, or 2 pages in dry-run mode)"
    )
    args = parser.parse_args()
    
    # In dry-run mode, default to 2 pages unless explicitly specified
    max_pages = args.max_pages
    if args.dry_run and max_pages is None:
        max_pages = 2
    
    await run_extraction(
        args.search_url, 
        args.output if not args.dry_run else None,
        dry_run=args.dry_run,
        max_pages=max_pages
    )


if __name__ == "__main__":
    asyncio.run(main())
