from contextlib import asynccontextmanager
from enum import Enum
import re
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from database import create_database_schema, get_db
from models import Campaign, FeatureCode, Vehicle


FEATURE_CODE_PATTERN = re.compile(r"(?=.*[A-Z])(?=.*[0-9])[A-Z0-9]{5}")


class CampaignStatus(str, Enum):
    """The two optional lifecycle states supported by a campaign."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"


class CampaignCreate(BaseModel):
    """Request body used to create a campaign."""

    id: str
    name: str
    target_version: str
    target_feature_codes: list[str] = Field(default_factory=list)
    status: CampaignStatus = CampaignStatus.DRAFT

    @field_validator("id", "name", "target_version")
    @classmethod
    def require_non_empty_string(cls, value: str) -> str:
        """Reject blank values, including strings that only contain spaces."""
        if not value.strip():
            raise ValueError("Value must not be empty.")
        return value


class CampaignUpdate(BaseModel):
    """Optional values that can be changed after a campaign is created."""

    name: str | None = None
    target_version: str | None = None
    status: CampaignStatus | None = None

    @field_validator("name", "target_version")
    @classmethod
    def require_non_empty_string(cls, value: str | None) -> str | None:
        """Reject blank values when a field is included in an update."""
        if value is not None and not value.strip():
            raise ValueError("Value must not be empty.")
        return value


class VehicleAssignmentCreate(BaseModel):
    """Request body used to assign a vehicle to a campaign."""

    vin: str

    @field_validator("vin")
    @classmethod
    def require_non_empty_vin(cls, value: str) -> str:
        """Reject an empty VIN before looking it up."""
        if not value.strip():
            raise ValueError("VIN must not be empty.")
        return value


def vehicle_response(vehicle: Vehicle) -> dict:
    """Return a vehicle in the API response format."""
    return {
        "vin": vehicle.vin,
        "model": vehicle.model,
        "software_version": vehicle.software_version,
        "feature_codes": sorted(code.code for code in vehicle.feature_codes),
    }


def campaign_response(campaign: Campaign) -> dict:
    """Return a campaign in the API response format."""
    return {
        "id": campaign.id,
        "name": campaign.name,
        "target_version": campaign.target_version,
        "status": campaign.status,
        "target_feature_codes": sorted(code.code for code in campaign.target_feature_codes),
        "vehicle_vins": sorted(vehicle.vin for vehicle in campaign.vehicles),
    }


def get_campaign_or_404(campaign_id: str, db: Session) -> Campaign:
    """Load a campaign and its response relationships, or return 404."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return campaign


def validate_target_feature_codes(codes: list[str], db: Session) -> list[str]:
    """Validate target codes and return them once each, preserving input order."""
    unique_codes = list(dict.fromkeys(codes))
    invalid_codes = [code for code in unique_codes if not FEATURE_CODE_PATTERN.fullmatch(code)]
    if invalid_codes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid feature code: {invalid_codes[0]}.",
        )

    known_codes = {
        row[0]
        for row in db.query(FeatureCode.code)
        .filter(FeatureCode.code.in_(unique_codes))
        .all()
    }
    unknown_codes = [code for code in unique_codes if code not in known_codes]
    if unknown_codes:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown feature code: {unknown_codes[0]}.",
        )
    return unique_codes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure the schema exists when the API starts."""
    create_database_schema()
    yield


app = FastAPI(
    title="OTA Campaign API",
    description="Manage vehicles and over-the-air software update campaigns.",
    version="1.0.0",
    openapi_tags=[
        {"name": "vehicles", "description": "Read vehicle information."},
        {"name": "campaigns", "description": "Manage OTA campaigns."},
    ],
    lifespan=lifespan,
)


@app.get("/health", tags=["vehicles"])
def health_check(db: Session = Depends(get_db)):
    """Confirm that the API can connect to PostgreSQL."""
    db.execute(text("SELECT 1"))
    return {"database": "connected"}


@app.get("/vehicles", tags=["vehicles"])
def get_vehicles(db: Session = Depends(get_db)):
    """List the vehicles loaded from PostgreSQL."""
    vehicles = db.query(Vehicle).all()
    return [vehicle_response(vehicle) for vehicle in vehicles]


@app.get("/campaigns", tags=["campaigns"])
def get_campaigns(db: Session = Depends(get_db)):
    """List all campaigns."""
    campaigns = db.query(Campaign).all()
    return [campaign_response(campaign) for campaign in campaigns]


@app.get("/campaigns/{campaign_id}", tags=["campaigns"])
def get_campaign(campaign_id: str, db: Session = Depends(get_db)):
    """Get one campaign, or return a standard 404 response."""
    campaign = get_campaign_or_404(campaign_id, db)
    return campaign_response(campaign)


@app.post("/campaigns", status_code=status.HTTP_201_CREATED, tags=["campaigns"])
def create_campaign(campaign_data: CampaignCreate, db: Session = Depends(get_db)):
    """Create a campaign and assign vehicles matching any target feature code."""
    if db.get(Campaign, campaign_data.id) is not None:
        raise HTTPException(status_code=409, detail="Campaign ID already exists.")

    target_codes = validate_target_feature_codes(campaign_data.target_feature_codes, db)
    target_feature_codes = (
        db.query(FeatureCode).filter(FeatureCode.code.in_(target_codes)).all()
    )

    matched_vehicles = []
    if target_codes:
        matched_vehicles = (
            db.query(Vehicle)
            .join(Vehicle.feature_codes)
            .filter(FeatureCode.code.in_(target_codes))
            .distinct()
            .all()
        )

    campaign = Campaign(
        id=campaign_data.id,
        name=campaign_data.name,
        target_version=campaign_data.target_version,
        status=campaign_data.status.value,
    )
    campaign.target_feature_codes = target_feature_codes
    campaign.vehicles = matched_vehicles
    db.add(campaign)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Campaign ID already exists.")

    return campaign_response(get_campaign_or_404(campaign.id, db))


@app.patch("/campaigns/{campaign_id}", tags=["campaigns"])
def update_campaign(
    campaign_id: str,
    campaign_data: CampaignUpdate,
    db: Session = Depends(get_db),
):
    """Update a campaign's name, target version, or status."""
    campaign = get_campaign_or_404(campaign_id, db)

    if campaign_data.name is not None:
        campaign.name = campaign_data.name
    if campaign_data.target_version is not None:
        campaign.target_version = campaign_data.target_version
    if campaign_data.status is not None:
        campaign.status = campaign_data.status.value

    db.commit()
    return campaign_response(campaign)


@app.delete(
    "/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["campaigns"]
)
def delete_campaign(campaign_id: str, db: Session = Depends(get_db)):
    """Delete a campaign without deleting any vehicles."""
    campaign = get_campaign_or_404(campaign_id, db)
    db.delete(campaign)
    db.commit()


@app.post("/campaigns/{campaign_id}/vehicles", tags=["campaigns"])
def add_vehicle_to_campaign(
    campaign_id: str,
    assignment_data: VehicleAssignmentCreate,
    db: Session = Depends(get_db),
):
    """Assign a vehicle directly, even if it does not match target feature codes."""
    campaign = get_campaign_or_404(campaign_id, db)
    vehicle = db.get(Vehicle, assignment_data.vin)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found.")

    if vehicle not in campaign.vehicles:
        campaign.vehicles.append(vehicle)
        db.commit()

    return campaign_response(campaign)


@app.delete(
    "/campaigns/{campaign_id}/vehicles/{vin}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["campaigns"],
)
def remove_vehicle_from_campaign(campaign_id: str, vin: str, db: Session = Depends(get_db)):
    """Remove one direct or automatic vehicle assignment from a campaign."""
    campaign = get_campaign_or_404(campaign_id, db)
    vehicle = db.get(Vehicle, vin)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found.")
    if vehicle not in campaign.vehicles:
        raise HTTPException(status_code=404, detail="Vehicle is not assigned to this campaign.")

    campaign.vehicles.remove(vehicle)
    db.commit()
