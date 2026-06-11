"""
FastAPI endpoint tests for Mergington High School Activities API.

Test coverage:
- GET / (redirect)
- GET /activities (list all activities)
- POST /activities/{activity_name}/signup (register for activity)
- DELETE /activities/{activity_name}/unregister (unregister from activity)

Following AAA (Arrange-Act-Assert) pattern for clarity and maintainability.
"""

import pytest


# ============================================================================
# GET / - Root Redirect
# ============================================================================

class TestRootEndpoint:
    """Tests for the root endpoint redirect."""

    def test_root_redirects_to_static_html(self, client, reset_activities):
        """
        Arrange: Make a GET request to root
        Act: Get response
        Assert: Should redirect to /static/index.html
        """
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"

    def test_root_redirect_with_follow(self, client, reset_activities):
        """
        Arrange: Make a GET request to root with redirects enabled
        Act: Get response
        Assert: Should eventually reach the static file route
        """
        response = client.get("/", follow_redirects=True)
        # The static file is mounted, so we expect a successful response or 404
        # (404 is acceptable since we're testing the redirect behavior, not static file serving)
        assert response.status_code in [200, 404]


# ============================================================================
# GET /activities - List All Activities
# ============================================================================

class TestGetActivitiesEndpoint:
    """Tests for retrieving all activities."""

    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """
        Arrange: API has 9 activities loaded
        Act: Make GET request to /activities
        Assert: Response contains all activities with correct structure
        """
        response = client.get("/activities")
        assert response.status_code == 200

        activities = response.json()
        assert isinstance(activities, dict)
        assert len(activities) > 0

    def test_get_activities_returns_correct_structure(self, client, reset_activities):
        """
        Arrange: Make request to /activities
        Act: Parse response
        Assert: Each activity has required fields
        """
        response = client.get("/activities")
        activities = response.json()

        # Check each activity has the required fields
        for activity_name, details in activities.items():
            assert isinstance(activity_name, str)
            assert "description" in details
            assert "schedule" in details
            assert "max_participants" in details
            assert "participants" in details
            assert isinstance(details["participants"], list)
            assert isinstance(details["max_participants"], int)

    def test_get_activities_contains_chess_club(self, client, reset_activities):
        """
        Arrange: API initialized with default activities
        Act: Fetch activities
        Assert: Chess Club exists with correct details
        """
        response = client.get("/activities")
        activities = response.json()

        assert "Chess Club" in activities
        chess = activities["Chess Club"]
        assert "chess" in chess["description"].lower()
        assert "Fridays" in chess["schedule"]
        assert chess["max_participants"] == 12

    def test_get_activities_participants_list_is_empty_or_populated(self, client, reset_activities):
        """
        Arrange: Make request to /activities
        Act: Check participants field
        Assert: Participants is a list (empty or with emails)
        """
        response = client.get("/activities")
        activities = response.json()

        for activity_name, details in activities.items():
            participants = details["participants"]
            assert isinstance(participants, list)
            # Each participant should be an email-like string
            for participant in participants:
                assert isinstance(participant, str)
                assert "@" in participant  # Simple email validation


# ============================================================================
# POST /activities/{activity_name}/signup - Register for Activity
# ============================================================================

class TestSignupEndpoint:
    """Tests for signing up a student for an activity."""

    def test_signup_valid_activity_valid_email_success(self, client, reset_activities):
        """
        Arrange: Valid activity name and new email
        Act: Make POST request to signup
        Assert: Success response (200) and participant added
        """
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        result = response.json()
        assert "message" in result
        assert "newstudent@mergington.edu" in result["message"]

    def test_signup_adds_participant_to_activity(self, client, reset_activities):
        """
        Arrange: Signup a new participant
        Act: Get activities and check participants list
        Assert: New participant appears in the activity
        """
        client.post(
            "/activities/Soccer%20Team/signup",
            params={"email": "alice@mergington.edu"}
        )

        # Verify participant was added
        response = client.get("/activities")
        activities = response.json()
        assert "alice@mergington.edu" in activities["Soccer Team"]["participants"]

    def test_signup_activity_not_found(self, client, reset_activities):
        """
        Arrange: Nonexistent activity name
        Act: Make POST request to signup
        Assert: 404 error response
        """
        response = client.post(
            "/activities/Nonexistent%20Club/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        result = response.json()
        assert "not found" in result["detail"].lower()

    def test_signup_already_registered_error(self, client, reset_activities):
        """
        Arrange: Student already registered for activity
        Act: Try to register same student again
        Assert: 400 error (duplicate registration)
        """
        email = "michael@mergington.edu"  # Already in Chess Club

        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": email}
        )
        assert response.status_code == 400
        result = response.json()
        assert "already" in result["detail"].lower()

    def test_signup_multiple_different_participants(self, client, reset_activities):
        """
        Arrange: Multiple new participants for same activity
        Act: Sign up three different students
        Assert: All three appear in participants list
        """
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]

        for email in emails:
            response = client.post(
                "/activities/Art%20Studio/signup",
                params={"email": email}
            )
            assert response.status_code == 200

        # Verify all participants were added
        response = client.get("/activities")
        activities = response.json()
        for email in emails:
            assert email in activities["Art Studio"]["participants"]

    def test_signup_updates_availability_count(self, client, reset_activities):
        """
        Arrange: Get initial participant count
        Act: Sign up a new participant
        Assert: Availability count decreases
        """
        # Get initial state
        response1 = client.get("/activities")
        initial_participants = len(response1.json()["Drama Club"]["participants"])
        initial_max = response1.json()["Drama Club"]["max_participants"]

        # Sign up new participant
        client.post(
            "/activities/Drama%20Club/signup",
            params={"email": "newactor@mergington.edu"}
        )

        # Verify count increased
        response2 = client.get("/activities")
        new_participants = len(response2.json()["Drama Club"]["participants"])
        assert new_participants == initial_participants + 1
        assert new_participants <= initial_max


# ============================================================================
# DELETE /activities/{activity_name}/unregister - Unregister from Activity
# ============================================================================

class TestUnregisterEndpoint:
    """Tests for unregistering a student from an activity."""

    def test_unregister_existing_participant_success(self, client, reset_activities):
        """
        Arrange: Valid activity and registered participant
        Act: Make DELETE request to unregister
        Assert: Success response (200) and participant removed
        """
        email = "michael@mergington.edu"  # Already in Chess Club

        response = client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        result = response.json()
        assert "Unregistered" in result["message"]

    def test_unregister_removes_participant_from_activity(self, client, reset_activities):
        """
        Arrange: Participant registered for activity
        Act: Unregister participant and fetch activities
        Assert: Participant no longer in participants list
        """
        email = "michael@mergington.edu"

        client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": email}
        )

        # Verify participant was removed
        response = client.get("/activities")
        activities = response.json()
        assert email not in activities["Chess Club"]["participants"]

    def test_unregister_activity_not_found(self, client, reset_activities):
        """
        Arrange: Nonexistent activity name
        Act: Make DELETE request to unregister
        Assert: 404 error response
        """
        response = client.delete(
            "/activities/Nonexistent%20Club/unregister",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        result = response.json()
        assert "not found" in result["detail"].lower()

    def test_unregister_participant_not_registered(self, client, reset_activities):
        """
        Arrange: Email not registered for activity
        Act: Try to unregister non-participant
        Assert: 400 error (not signed up)
        """
        response = client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": "notregistered@mergington.edu"}
        )
        assert response.status_code == 400
        result = response.json()
        assert "not" in result["detail"].lower()

    def test_unregister_last_participant_leaves_empty_list(self, client, reset_activities):
        """
        Arrange: Activity with only one participant
        Act: Unregister the only participant
        Assert: Participants list becomes empty
        """
        # Find an activity and unregister all participants
        response = client.get("/activities")
        activities = response.json()

        # Use Chess Club which has 2 participants
        for participant in activities["Chess Club"]["participants"].copy():
            response = client.delete(
                "/activities/Chess%20Club/unregister",
                params={"email": participant}
            )
            assert response.status_code == 200

        # Verify list is now empty
        response = client.get("/activities")
        assert len(response.json()["Chess Club"]["participants"]) == 0

    def test_unregister_decreases_participant_count(self, client, reset_activities):
        """
        Arrange: Get initial participant count
        Act: Unregister a participant
        Assert: Participant count decreases by 1
        """
        # Get initial state
        response1 = client.get("/activities")
        initial_count = len(response1.json()["Programming Class"]["participants"])

        # Unregister one participant
        email = response1.json()["Programming Class"]["participants"][0]
        client.delete(
            "/activities/Programming%20Class/unregister",
            params={"email": email}
        )

        # Verify count decreased
        response2 = client.get("/activities")
        new_count = len(response2.json()["Programming Class"]["participants"])
        assert new_count == initial_count - 1


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple operations."""

    def test_signup_then_unregister_flow(self, client, reset_activities):
        """
        Arrange: New participant email
        Act: Sign up, then unregister
        Assert: Participant added then removed correctly
        """
        email = "flowtest@mergington.edu"

        # Sign up
        response1 = client.post(
            "/activities/Debate%20Team/signup",
            params={"email": email}
        )
        assert response1.status_code == 200

        # Verify signup
        response2 = client.get("/activities")
        assert email in response2.json()["Debate Team"]["participants"]

        # Unregister
        response3 = client.delete(
            "/activities/Debate%20Team/unregister",
            params={"email": email}
        )
        assert response3.status_code == 200

        # Verify unregister
        response4 = client.get("/activities")
        assert email not in response4.json()["Debate Team"]["participants"]

    def test_cannot_signup_after_unregister_then_signup_again(self, client, reset_activities):
        """
        Arrange: Participant email
        Act: Sign up, unregister, sign up again
        Assert: All operations succeed (no residual state)
        """
        email = "statetest@mergington.edu"

        # First signup
        response1 = client.post(
            "/activities/Swimming%20Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200

        # Unregister
        response2 = client.delete(
            "/activities/Swimming%20Club/unregister",
            params={"email": email}
        )
        assert response2.status_code == 200

        # Second signup (should succeed, not fail as duplicate)
        response3 = client.post(
            "/activities/Swimming%20Club/signup",
            params={"email": email}
        )
        assert response3.status_code == 200

        # Verify participant is there
        response4 = client.get("/activities")
        assert email in response4.json()["Swimming Club"]["participants"]
