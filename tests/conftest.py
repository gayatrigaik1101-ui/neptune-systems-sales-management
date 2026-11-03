"""
Pytest configuration and isolation fixtures for Neptune Systems.
Ensures test runs use an isolated test mirror and never contaminate production mirrors.
"""

import json
import pytest
from app.config import BACKUPS_DIR
from app.google_sheets import sheets_connector


@pytest.fixture(scope="session", autouse=True)
def isolate_test_database():
    """Points sheets_connector to an isolated test mirror during test sessions."""
    original_mirror = sheets_connector.local_mirror_file
    test_mirror = BACKUPS_DIR / "test_sales_database_mirror.json"

    # Initialize fresh test mirror
    test_data = {
        "sales_entries": [],
        "edit_history": [],
        "metadata": {
            "environment": "test",
            "created_at": "03-11-2026 00:00:00",
        }
    }
    with open(test_mirror, "w", encoding="utf-8") as f:
        json.dump(test_data, f, indent=2)

    sheets_connector.local_mirror_file = test_mirror

    yield

    # Teardown: restore original and remove test mirror
    sheets_connector.local_mirror_file = original_mirror
    if test_mirror.exists():
        test_mirror.unlink()
