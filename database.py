"""Database configuration shared by the API and the seed script."""

import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set before starting the application.")


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class used by every database model."""


def create_database_schema() -> None:
    """Create tables and apply the one small schema update used by this project."""
    Base.metadata.create_all(bind=engine)

    campaign_columns = {
        column["name"] for column in inspect(engine).get_columns("campaigns")
    }
    if "status" not in campaign_columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE campaigns "
                    "ADD COLUMN status VARCHAR NOT NULL DEFAULT 'DRAFT'"
                )
            )


def get_db():
    """Provide one database session for a request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
