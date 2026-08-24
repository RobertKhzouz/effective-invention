"""End-to-end tests for the OTA Campaign API."""

import os
from pathlib import Path


TEST_DATABASE = Path(__file__).parent / "ota_campaign_api_tests.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE}"

from fastapi.testclient import TestClient

from api import app
from database import Base, engine
from seed import seed_database


def reset_database() -> None:
    """Create a clean schema and load the supplied vehicle data."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_database()


def test_list_vehicles_includes_feature_codes():
    reset_database()

    with TestClient(app) as client:
        response = client.get("/vehicles")

    assert response.status_code == 200
    vehicles = response.json()
    assert len(vehicles) == 25
    assert len(vehicles[0]["feature_codes"]) == 20


def test_create_campaign_assigns_matching_vehicles():
    reset_database()

    with TestClient(app) as client:
        response = client.post(
            "/campaigns",
            json={
                "id": "f150-update",
                "name": "F150 update",
                "target_version": "4.3.0",
                "target_feature_codes": ["B7STG", "B7STG"],
            },
        )

    assert response.status_code == 201
    campaign = response.json()
    assert campaign["target_feature_codes"] == ["B7STG"]
    assert len(campaign["vehicle_vins"]) == 4


def test_create_campaign_without_target_codes_assigns_no_vehicles():
    reset_database()

    with TestClient(app) as client:
        response = client.post(
            "/campaigns",
            json={
                "id": "manual-update",
                "name": "Manual update",
                "target_version": "4.3.0",
            },
        )

    assert response.status_code == 201
    assert response.json()["target_feature_codes"] == []
    assert response.json()["vehicle_vins"] == []


def test_multiple_target_codes_assign_the_union_of_matching_vehicles():
    reset_database()

    with TestClient(app) as client:
        vehicles = client.get("/vehicles").json()
        expected_vins = sorted(
            vehicle["vin"]
            for vehicle in vehicles
            if "B7STG" in vehicle["feature_codes"]
            or "703SI" in vehicle["feature_codes"]
        )
        response = client.post(
            "/campaigns",
            json={
                "id": "two-model-update",
                "name": "Two model update",
                "target_version": "4.3.0",
                "target_feature_codes": ["B7STG", "703SI"],
            },
        )

    assert response.status_code == 201
    assert response.json()["vehicle_vins"] == expected_vins


def test_campaign_creation_rejects_invalid_and_unknown_feature_codes():
    reset_database()

    with TestClient(app) as client:
        invalid_response = client.post(
            "/campaigns",
            json={
                "id": "invalid-code",
                "name": "Invalid code",
                "target_version": "4.3.0",
                "target_feature_codes": ["ABCDE"],
            },
        )
        unknown_response = client.post(
            "/campaigns",
            json={
                "id": "unknown-code",
                "name": "Unknown code",
                "target_version": "4.3.0",
                "target_feature_codes": ["A1B2C"],
            },
        )

    assert invalid_response.status_code == 400
    assert invalid_response.json()["detail"] == "Invalid feature code: ABCDE."
    assert unknown_response.status_code == 400
    assert unknown_response.json()["detail"] == "Unknown feature code: A1B2C."


def test_campaign_creation_rejects_blank_required_fields():
    reset_database()

    with TestClient(app) as client:
        response = client.post(
            "/campaigns",
            json={
                "id": "blank-name",
                "name": "   ",
                "target_version": "4.3.0",
            },
        )

    assert response.status_code == 422


def test_duplicate_campaign_id_is_rejected():
    reset_database()
    request_body = {
        "id": "duplicate-id",
        "name": "First campaign",
        "target_version": "4.3.0",
    }

    with TestClient(app) as client:
        assert client.post("/campaigns", json=request_body).status_code == 201
        response = client.post("/campaigns", json=request_body)

    assert response.status_code == 409
    assert response.json()["detail"] == "Campaign ID already exists."


def test_direct_assignment_does_not_duplicate_a_vehicle():
    reset_database()

    with TestClient(app) as client:
        client.post(
            "/campaigns",
            json={
                "id": "assignment-test",
                "name": "Assignment test",
                "target_version": "4.3.0",
                "target_feature_codes": ["B7STG"],
            },
        )
        response = client.post(
            "/campaigns/assignment-test/vehicles",
            json={"vin": "1FMCU9G68MUA23456"},
        )
        repeated_response = client.post(
            "/campaigns/assignment-test/vehicles",
            json={"vin": "1FMCU9G68MUA23456"},
        )

    assert response.status_code == 200
    assert len(response.json()["vehicle_vins"]) == 5
    assert repeated_response.status_code == 200
    assert len(repeated_response.json()["vehicle_vins"]) == 5


def test_campaign_status_can_be_updated():
    reset_database()

    with TestClient(app) as client:
        created = client.post(
            "/campaigns",
            json={
                "id": "status-test",
                "name": "Status test",
                "target_version": "4.3.0",
            },
        )
        updated = client.patch(
            "/campaigns/status-test",
            json={"status": "ACTIVE", "target_version": "4.3.1"},
        )

    assert created.status_code == 201
    assert created.json()["status"] == "DRAFT"
    assert updated.status_code == 200
    assert updated.json()["status"] == "ACTIVE"
    assert updated.json()["target_version"] == "4.3.1"


def test_vehicle_assignment_and_campaign_can_be_deleted():
    reset_database()

    with TestClient(app) as client:
        client.post(
            "/campaigns",
            json={
                "id": "delete-test",
                "name": "Delete test",
                "target_version": "4.3.0",
            },
        )
        client.post(
            "/campaigns/delete-test/vehicles",
            json={"vin": "1FMCU9G68MUA23456"},
        )
        removed_vehicle = client.delete(
            "/campaigns/delete-test/vehicles/1FMCU9G68MUA23456"
        )
        deleted_campaign = client.delete("/campaigns/delete-test")
        missing_campaign = client.get("/campaigns/delete-test")

    assert removed_vehicle.status_code == 204
    assert deleted_campaign.status_code == 204
    assert missing_campaign.status_code == 404


def test_missing_campaign_and_vehicle_return_404():
    reset_database()

    with TestClient(app) as client:
        missing_campaign = client.get("/campaigns/missing")
        client.post(
            "/campaigns",
            json={
                "id": "vehicle-check",
                "name": "Vehicle check",
                "target_version": "4.3.0",
            },
        )
        missing_vehicle = client.post(
            "/campaigns/vehicle-check/vehicles",
            json={"vin": "missing-vin"},
        )

    assert missing_campaign.status_code == 404
    assert missing_vehicle.status_code == 404
