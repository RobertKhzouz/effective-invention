"""Create the schema and load the supplied vehicles into PostgreSQL."""

import json
from pathlib import Path

from sqlalchemy import select

from database import SessionLocal, create_database_schema
from models import FeatureCode, Vehicle


DATA_FILE = Path(__file__).parent / "data" / "vehicles.json"


def seed_database() -> None:
    """Create tables and upsert vehicles and their feature-code associations."""
    create_database_schema()

    with DATA_FILE.open() as data_file:
        vehicles = json.load(data_file)

    with SessionLocal() as db:
        # Keep new feature codes until transaction commits, avoids adding same code twice while processing JSON
        feature_codes_by_code = {
            feature_code.code: feature_code
            for feature_code in db.scalars(select(FeatureCode))
        }

        for vehicle_data in vehicles:
            vehicle = db.get(Vehicle, vehicle_data["vin"])
            if vehicle is None:
                vehicle = Vehicle(
                    vin=vehicle_data["vin"],
                    model=vehicle_data["model"],
                    software_version=vehicle_data["software_version"],
                )
                db.add(vehicle)
            else:
                vehicle.model = vehicle_data["model"]
                vehicle.software_version = vehicle_data["software_version"]

            for code in vehicle_data["feature_codes"]:
                feature_code = feature_codes_by_code.get(code)
                if feature_code is None:
                    feature_code = FeatureCode(code=code)
                    db.add(feature_code)
                    feature_codes_by_code[code] = feature_code
                if feature_code not in vehicle.feature_codes:
                    vehicle.feature_codes.append(feature_code)

        db.commit()


if __name__ == "__main__":
    seed_database()
    print("Database schema created and vehicles seeded.")
