from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


@pytest.fixture(autouse=True)
def reset_activities():
    original_activities = deepcopy(activities)
    yield
    activities.clear()
    activities.update(deepcopy(original_activities))


@pytest.fixture
def client():
    return TestClient(app)


def test_root_redirects_to_static_index(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_activity_data(client):
    response = client.get("/activities")

    assert response.status_code == 200
    data = response.json()
    assert "Chess Club" in data
    assert data["Chess Club"]["participants"] == [
        "michael@mergington.edu",
        "daniel@mergington.edu",
    ]


def test_signup_adds_student_to_activity(client):
    email = "new.student@mergington.edu"

    response = client.post(
        "/activities/Basketball%20Team/signup",
        params={"email": email},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": f"Signed up {email} for Basketball Team"
    }
    assert email in activities["Basketball Team"]["participants"]


def test_signup_rejects_unknown_activity(client):
    response = client.post(
        "/activities/Unknown%20Club/signup",
        params={"email": "student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_rejects_duplicate_student(client):
    email = "new.student@mergington.edu"
    client.post("/activities/Basketball%20Team/signup", params={"email": email})

    response = client.post(
        "/activities/Basketball%20Team/signup",
        params={"email": email},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"
    assert activities["Basketball Team"]["participants"].count(email) == 1


def test_signup_rejects_full_activity(client):
    activity = activities["Basketball Team"]
    activity["participants"] = [
        f"student{i}@mergington.edu" for i in range(activity["max_participants"])
    ]

    response = client.post(
        "/activities/Basketball%20Team/signup",
        params={"email": "late.student@mergington.edu"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Activity is full"
    assert "late.student@mergington.edu" not in activity["participants"]


def test_unregister_removes_student_from_activity(client):
    email = "new.student@mergington.edu"
    client.post("/activities/Basketball%20Team/signup", params={"email": email})

    response = client.delete(
        "/activities/Basketball%20Team/signup",
        params={"email": email},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": f"Unregistered {email} from Basketball Team"
    }
    assert email not in activities["Basketball Team"]["participants"]


def test_unregister_rejects_unknown_activity(client):
    response = client.delete(
        "/activities/Unknown%20Club/signup",
        params={"email": "student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_rejects_nonparticipant(client):
    response = client.delete(
        "/activities/Basketball%20Team/signup",
        params={"email": "not.registered@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"
