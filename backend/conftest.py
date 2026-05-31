"""
Pytest configuration and shared fixtures.
Sets up the testing environment, asyncio event loops, and database mocks.
"""

import pytest


@pytest.fixture(scope="session")
def anyio_backend():
    """
    Configures the async backend for tests using anyio.
    This replaces the deprecated pytest-asyncio strict mode.
    """
    return "asyncio"
