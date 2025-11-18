"""
Load URLs from CSV into SQLite database.
"""
import argparse
from pathlib import Path

import pandas as pd

from linkedin_cleanup import config
from linkedin_cleanup.db import get_connection_status, update_connection_status


def load_urls_from_csv(csv_path: str) -> int:
    """Load URLs from CSV into database with status='pending'."""
    print(f"📂 Loading URLs from: {csv_path}")
    
    # Read CSV
    df = pd.read_csv(csv_path)
    if "URL" not in df.columns:
        raise ValueError(f"CSV file must have a 'URL' column. Found columns: {df.columns.tolist()}")
    
    urls = df["URL"].tolist()
    print(f"✓ Found {len(urls)} URLs in CSV\n")
    
    # Insert into database
    print("💾 Inserting URLs into database...")
    new_count = 0
    existing_count = 0
    
    for url in urls:
        # Check if URL already exists
        if get_connection_status(url) is not None:
            existing_count += 1
        else:
            update_connection_status(url, "pending")
            new_count += 1
    
    print(f"✓ Loaded {new_count} new URLs")
    if existing_count > 0:
        print(f"  (Skipped {existing_count} URLs that already exist in database)")
    print(f"\n📊 Total URLs in database: {new_count + existing_count}")
    
    return new_count


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Load URLs from CSV into SQLite database"
    )
    parser.add_argument(
        "--input-csv",
        type=str,
        metavar="CSV",
        help=f"Input CSV file with URLs (default: {config.OUTPUT_CSV})"
    )
    args = parser.parse_args()
    
    csv_path = args.input_csv or config.OUTPUT_CSV
    
    if not Path(csv_path).exists():
        print(f"❌ Error: CSV file not found: {csv_path}")
        return
    
    try:
        load_urls_from_csv(csv_path)
        print("\n✅ Done!")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise


if __name__ == "__main__":
    main()

