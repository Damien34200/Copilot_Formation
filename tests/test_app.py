from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


@pytest.fixture
def client():
    original_activities = deepcopy(activities)
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        activities.clear()
        activities.update(original_activities)


def test_root_redirects_to_static_activity_page(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"

    page_response = client.get(response.headers["location"])
    assert page_response.status_code == 200
    assert page_response.headers["content-type"].startswith("text/html")
    assert "Mergington High School" in page_response.text


def test_get_activities_returns_activity_details(client):
    response = client.get("/activities")

    assert response.status_code == 200
    activity_data = response.json()
    assert "Chess Club" in activity_data
    assert {
        "description",
        "schedule",
        "max_participants",
        "participants",
    } <= activity_data["Chess Club"].keys()
    assert isinstance(activity_data["Chess Club"]["participants"], list)


def test_signup_adds_participant_and_get_activities_reflects_change(client):
    activity_name = "Soccer Team"
    email = "new-student@mergington.edu"

    response = client.post(
        f"/activities/{activity_name}/signup", params={"email": email}
    )

    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for {activity_name}"}
    activity_data = client.get("/activities").json()
    assert email in activity_data[activity_name]["participants"]


def test_signup_returns_404_for_unknown_activity(client):
    response = client.post(
        "/activities/Unknown%20Activity/signup",
        params={"email": "student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_signup_returns_400_for_duplicate_participant(client):
    activity_name = "Soccer Team"
    email = "student@mergington.edu"
    client.post(f"/activities/{activity_name}/signup", params={"email": email})

    response = client.post(
        f"/activities/{activity_name}/signup", params={"email": email}
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Student already signed up for this activity"
    }


def test_signup_requires_email(client):
    response = client.post("/activities/Soccer%20Team/signup")

    assert response.status_code == 422


def test_unregister_removes_participant_and_get_activities_reflects_change(client):
    activity_name = "Soccer Team"
    email = "student@mergington.edu"
    signup_response = client.post(
        f"/activities/{activity_name}/signup", params={"email": email}
    )
    assert signup_response.status_code == 200

    response = client.delete(
        f"/activities/{activity_name}/signup", params={"email": email}
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": f"Unregistered {email} from {activity_name}"
    }
    activity_data = client.get("/activities").json()
    assert email not in activity_data[activity_name]["participants"]


def test_unregister_returns_404_for_unknown_activity(client):
    response = client.delete(
        "/activities/Unknown%20Activity/signup",
        params={"email": "student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_unregister_returns_404_for_nonparticipant(client):
    response = client.delete(
        "/activities/Soccer%20Team/signup",
        params={"email": "not-registered@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Student is not signed up for this activity"
    }


def test_unregister_requires_email(client):
    response = client.delete("/activities/Soccer%20Team/signup")

    assert response.status_code == 422