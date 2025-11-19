"""
Tests for database functionality.
"""
import os
import tempfile
from pathlib import Path

import pytest

from linkedin_cleanup import config
from linkedin_cleanup.db import (
    get_all_connections,
    get_connection_status,
    get_pending_urls,
    update_connection_status,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Create temporary file
    fd, temp_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Save original config value
    original_path = config.PROGRESS_FILE
    
    # Set config to use temp database
    config.PROGRESS_FILE = temp_path
    
    # Initialize database by calling update_connection_status (which initializes DB)
    # This ensures the database is created
    update_connection_status("__init__", "pending")
    
    yield temp_path
    
    # Restore original config
    config.PROGRESS_FILE = original_path
    
    # Clean up temp file
    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_update_and_get_connection_status(temp_db):
    """Test updating and getting connection status."""
    url = "https://www.linkedin.com/in/test-profile"
    
    # Update status
    update_connection_status(url, "pending", "Test message", "2024-01-01T00:00:00")
    
    # Get status
    status = get_connection_status(url)
    assert status == "pending"


def test_get_pending_urls(temp_db):
    """Test getting pending URLs (includes both pending and failed for retry)."""
    # Add some URLs with different statuses
    update_connection_status("https://www.linkedin.com/in/pending1", "pending")
    update_connection_status("https://www.linkedin.com/in/pending2", "pending")
    update_connection_status("https://www.linkedin.com/in/success1", "success")
    update_connection_status("https://www.linkedin.com/in/failed1", "failed")
    
    # Get pending URLs (filter out the __init__ entry from fixture)
    pending = [url for url in get_pending_urls() if url != "__init__"]
    
    # Verify: get_pending_urls returns both pending and failed (for retry)
    assert len(pending) == 3
    assert "https://www.linkedin.com/in/pending1" in pending
    assert "https://www.linkedin.com/in/pending2" in pending
    assert "https://www.linkedin.com/in/failed1" in pending  # Failed URLs are included for retry
    assert "https://www.linkedin.com/in/success1" not in pending  # Success should not be included


def test_get_all_connections(temp_db):
    """Test getting all connections."""
    # Add some URLs
    update_connection_status("https://www.linkedin.com/in/test1", "success", "Success message")
    update_connection_status("https://www.linkedin.com/in/test2", "failed", "Failed message")
    update_connection_status("https://www.linkedin.com/in/test3", "pending")
    
    # Get all connections (filter out the __init__ entry from fixture)
    all_conns = [conn for conn in get_all_connections() if conn["url"] != "__init__"]
    
    # Verify
    assert len(all_conns) == 3
    
    # Check structure
    for conn in all_conns:
        assert "url" in conn
        assert "status" in conn
        assert "message" in conn
        assert "timestamp" in conn
    
    # Check specific entries
    urls = [conn["url"] for conn in all_conns]
    assert "https://www.linkedin.com/in/test1" in urls
    assert "https://www.linkedin.com/in/test2" in urls
    assert "https://www.linkedin.com/in/test3" in urls


def test_update_connection_status_overwrite(temp_db):
    """Test that updating a connection overwrites the previous status."""
    url = "https://www.linkedin.com/in/test-profile"
    
    # Update with initial status
    update_connection_status(url, "pending", "Initial message")
    assert get_connection_status(url) == "pending"
    
    # Update with new status
    update_connection_status(url, "success", "Success message")
    assert get_connection_status(url) == "success"
    
    # Verify only one entry exists
    all_conns = get_all_connections()
    matching = [conn for conn in all_conns if conn["url"] == url]
    assert len(matching) == 1
    assert matching[0]["status"] == "success"
    assert matching[0]["message"] == "Success message"


def test_get_connection_status_nonexistent(temp_db):
    """Test getting status for non-existent URL."""
    status = get_connection_status("https://www.linkedin.com/in/nonexistent")
    assert status is None

