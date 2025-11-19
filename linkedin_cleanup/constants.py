"""
Constants for LinkedIn cleanup project.
Centralized constants including status enums.
"""

from enum import StrEnum


class ConnectionStatus(StrEnum):
    """Connection status values used throughout the application."""

    CONNECTED = "connected"
    NOT_CONNECTED = "not_connected"
    UNKNOWN = "unknown"
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
