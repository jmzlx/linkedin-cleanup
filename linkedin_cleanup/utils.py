"""
Shared utility functions for LinkedIn cleanup scripts.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from linkedin_cleanup.linkedin_client import LinkedInClient

logger = logging.getLogger(__name__)


class LinkedInClientError(Exception):
    """Exception raised when LinkedIn client setup or login fails."""

    pass


def print_banner(title: str):
    """Print a formatted banner."""
    print(f"\n{'='*80}")
    print(title)
    print(f"{'='*80}\n")


async def with_timeout(
    coro, timeout: float, operation_name: str, on_timeout: Callable[[], None] | None = None
) -> Any | None:
    """Execute a coroutine with timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except TimeoutError:
        logger.error(f"TIMEOUT: {operation_name} timeout after {timeout}s")
        if on_timeout:
            on_timeout()
        return None


@asynccontextmanager
async def setup_linkedin_client() -> AsyncGenerator["LinkedInClient", None]:
    """Context manager for setting up and cleaning up LinkedIn client."""
    from linkedin_cleanup.linkedin_client import LinkedInClient

    client = LinkedInClient()

    try:
        await client.setup_browser()
        if not await client.ensure_logged_in():
            raise LinkedInClientError("Failed to log in to LinkedIn")
        yield client
    finally:
        await client.close()
