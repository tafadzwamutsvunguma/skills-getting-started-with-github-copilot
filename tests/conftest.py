"""
Pytest configuration and fixtures for FastAPI app tests.

Provides:
- TestClient fixture for API testing
- Fresh activities data isolation between tests
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """
    Provide a TestClient for making requests to the FastAPI app.
    """
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """
    Reset activities to a known state before each test.
    This prevents test interference and ensures data isolation.
    """
    # Store original state
    original_activities = {
        activity: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy(),
        }
        for activity, details in activities.items()
    }

    yield

    # Restore original state after test
    activities.clear()
    activities.update(original_activities)
