"""
Shared utility functions for LinkedIn cleanup scripts.
"""
import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Optional

from linkedin_cleanup.linkedin_client import LinkedInClient


class LinkedInClientError(Exception):
    """Exception raised when LinkedIn client setup or login fails."""
    pass


def print_banner(title: str):
    """Print a formatted banner."""
    print(f"\n{'='*80}")
    print(title)
    print(f"{'='*80}\n")


async def with_timeout(
    coro, 
    timeout: float, 
    operation_name: str,
    on_timeout: Optional[Callable[[], None]] = None
) -> Optional[Any]:
    """
    Execute a coroutine with timeout.
    
    Args:
        coro: Coroutine to execute
        timeout: Timeout in seconds
        operation_name: Name of operation for error message
        on_timeout: Optional callback to call on timeout (e.g., to update DB)
    
    Returns:
        Result of coroutine, or None on timeout
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        print(f"\n❌ TIMEOUT: {operation_name} timeout after {timeout}s")
        print("⚠️  Terminating script due to timeout.")
        if on_timeout:
            on_timeout()
        return None


@asynccontextmanager
async def setup_linkedin_client() -> AsyncGenerator[LinkedInClient, None]:
    """
    Context manager for setting up and cleaning up LinkedIn client.
    
    Sets up browser, ensures login, and automatically cleans up on exit.
    Raises LinkedInClientError if setup or login fails.
    
    Usage:
        try:
            async with setup_linkedin_client() as client:
                # Use client here
        except LinkedInClientError as e:
            print(f"Failed to setup client: {e}")
            return
    """
    client = LinkedInClient()
    
    try:
        # Setup browser
        print("🌐 Setting up browser...")
        await client.setup_browser()
        print("✓ Browser ready\n")
        
        # Ensure logged in
        print("🔐 Checking login status...")
        if not await client.ensure_logged_in():
            raise LinkedInClientError("Failed to log in to LinkedIn. Please check your credentials and try again.")
        print("✓ Logged in successfully\n")
        
        yield client
        
    finally:
        # Always cleanup browser
        print("\n🔒 Closing browser...")
        await client.close()
        print("✓ Browser closed")

