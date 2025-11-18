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
from linkedin_cleanup.linkedin_client import LinkedInClient
from linkedin_cleanup import search_extractor


def _print_banner(title: str):
    """Print a formatted banner."""
    print(f"\n{'='*80}")
    print(title)
    print(f"{'='*80}\n")


async def extract_all_profiles(client: LinkedInClient, search_url: str) -> List[Tuple[str, str, str]]:
    """Extract all profiles from search results, handling pagination.
    Returns list of (name, url, location) tuples.
    Deduplicates within a single run by URL.
    """
    all_profiles = []
    seen_urls: Set[str] = set()
    page_num = 1
    
    # Navigate to search URL
    print("Navigating to search results...")
    await client.navigate_to(search_url)
    
    # Wait a bit for page to load
    await client.random_delay(2, 3)
    
    while True:
        print(f"\nExtracting profiles from page {page_num}...")
        
        # Extract profiles from current page
        page_profiles = await search_extractor.extract_profiles_from_page(client)
        
        if not page_profiles:
            print(f"No profiles found on page {page_num}. Stopping.")
            break
        
        # Add new profiles (avoid duplicates within this run)
        new_count = 0
        for name, url, location in page_profiles:
            if url not in seen_urls:
                all_profiles.append((name, url, location))
                seen_urls.add(url)
                new_count += 1
        
        print(f"Found {len(page_profiles)} profiles on page {page_num} ({new_count} new)")
        
        # Check for next page
        if not await search_extractor.has_next_page(client):
            print("No more pages available.")
            break
        
        # Go to next page
        if not await search_extractor.go_to_next_page(client):
            print("Could not navigate to next page. Stopping.")
            break
        
        page_num += 1
        
        # Safety limit (shouldn't be needed, but just in case)
        if page_num > config.MAX_PAGES:
            print(f"Reached page limit ({config.MAX_PAGES}). Stopping.")
            break
    
    return all_profiles


async def run_extraction(search_url: str, output_csv: str):
    """Main execution function."""
    _print_banner("LINKEDIN SEARCH RESULTS EXTRACTOR")
    
    client = LinkedInClient()
    
    # Setup browser
    print("Setting up browser...")
    await client.setup_browser()
    
    try:
        # Ensure logged in
        if not await client.ensure_logged_in():
            print("Failed to log in. Exiting.")
            return
        
        # Extract all profiles
        all_profiles = await extract_all_profiles(client, search_url)
        
        # Save to CSV using pandas
        df = pd.DataFrame(all_profiles, columns=['Name', 'URL', 'Location'])
        output_path = Path(output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"\nSaved {len(all_profiles)} profiles to {output_csv}")
        
        _print_banner("EXTRACTION COMPLETE!")
        print(f"Total profiles extracted: {len(all_profiles)}")
        print(f"CSV saved to: {output_csv}")
    
    finally:
        print("\nClosing browser...")
        await client.close()


async def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="LinkedIn Search Results Extractor - Extract profile URLs from search results"
    )
    parser.add_argument(
        "--search-url",
        type=str,
        default=config.DEFAULT_SEARCH_URL,
        help=f"LinkedIn search results URL (default: {config.DEFAULT_SEARCH_URL})"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=config.DEFAULT_OUTPUT_CSV,
        help=f"Output CSV file path (default: {config.DEFAULT_OUTPUT_CSV})"
    )
    args = parser.parse_args()
    
    await run_extraction(args.search_url, args.output)


if __name__ == "__main__":
    asyncio.run(main())
