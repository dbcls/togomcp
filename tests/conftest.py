from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_toolcall_log():
    """Suppress toolcall_log during tests to avoid HTTP request context errors."""
    with patch("togo_mcp.server.toolcall_log"):
        yield
