"""
Logging configuration for LinkedIn cleanup project.
"""

import logging
import sys


def setup_logging(level: int | None = None) -> logging.Logger:
    """Set up logging configuration for the application."""
    if level is None:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logger = logging.getLogger("linkedin_cleanup")
    logger.setLevel(level)

    # Suppress noisy third-party loggers
    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return logger
