"""
Tests for retry mechanism functionality.
"""

import pytest

from linkedin_cleanup.retry import retry_async


@pytest.mark.asyncio
async def test_retry_async_success_on_first_attempt():
    """Test that retry_async succeeds on first attempt."""

    async def success_func():
        return "success"

    result = await retry_async(success_func, max_attempts=3)
    assert result == "success"


@pytest.mark.asyncio
async def test_retry_async_succeeds_after_retries():
    """Test that retry_async succeeds after some failures."""
    attempt_count = 0

    async def flaky_func():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ValueError("Temporary failure")
        return "success"

    result = await retry_async(flaky_func, max_attempts=5, delay=0.1)
    assert result == "success"
    assert attempt_count == 3


@pytest.mark.asyncio
async def test_retry_async_fails_after_max_attempts():
    """Test that retry_async raises exception after max attempts."""

    async def always_fails():
        raise ValueError("Always fails")

    with pytest.raises(ValueError, match="Always fails"):
        await retry_async(always_fails, max_attempts=3, delay=0.1)


@pytest.mark.asyncio
async def test_retry_async_respects_exception_filter():
    """Test that retry_async only retries on specified exceptions."""

    async def raises_key_error():
        raise KeyError("Wrong exception")

    # Should not retry on KeyError if only ValueError is specified
    with pytest.raises(KeyError):
        await retry_async(raises_key_error, max_attempts=3, exceptions=(ValueError,))
