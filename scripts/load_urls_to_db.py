"""
Load URLs from CSV into SQLite database.
"""

import argparse
from pathlib import Path

import pandas as pd

from linkedin_cleanup import config
from linkedin_cleanup.constants import ConnectionStatus
from linkedin_cleanup.db import get_connection_status, update_connection_status
from linkedin_cleanup.logging_config import setup_logging

logger = setup_logging()


def load_urls_from_csv(csv_path: str) -> int:
    """Load URLs from CSV into database with status='pending'."""
    logger.info(f"Loading URLs from: {csv_path}")

    # Read CSV
    df = pd.read_csv(csv_path)
    if "URL" not in df.columns:
        raise ValueError(f"CSV file must have a 'URL' column. Found columns: {df.columns.tolist()}")

    urls = df["URL"].tolist()
    logger.info(f"Found {len(urls)} URLs in CSV")

    # Insert into database
    logger.info("Inserting URLs into database...")
    new_count = 0
    existing_count = 0

    for url in urls:
        # Check if URL already exists
        if get_connection_status(url) is not None:
            existing_count += 1
        else:
            update_connection_status(url, ConnectionStatus.PENDING)
            new_count += 1

    logger.info(f"Loaded {new_count} new URLs")
    if existing_count > 0:
        logger.info(f"Skipped {existing_count} URLs that already exist in database")
    logger.info(f"Total URLs in database: {new_count + existing_count}")

    return new_count


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="Load URLs from CSV into SQLite database")
    parser.add_argument(
        "--input-csv",
        type=str,
        metavar="CSV",
        help=f"Input CSV file with URLs (default: {config.OUTPUT_CSV})",
    )
    args = parser.parse_args()

    csv_path = args.input_csv or config.OUTPUT_CSV

    if not Path(csv_path).exists():
        logger.error(f"CSV file not found: {csv_path}")
        return

    try:
        load_urls_from_csv(csv_path)
        logger.info("Done!")
    except Exception as e:
        logger.exception(f"Error loading URLs: {e}")
        raise


if __name__ == "__main__":
    main()
