"""SQLAlchemy models for vehicles, campaigns, and feature codes."""

from sqlalchemy import Column, ForeignKey, String, Table, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


vehicle_feature_codes = Table(
    "vehicle_feature_codes",
    Base.metadata,
    Column("vehicle_vin", ForeignKey("vehicles.vin"), primary_key=True),
    Column("feature_code", ForeignKey("feature_codes.code"), primary_key=True),
)

campaign_target_feature_codes = Table(
    "campaign_target_feature_codes",
    Base.metadata,
    Column("campaign_id", ForeignKey("campaigns.id"), primary_key=True),
    Column("feature_code", ForeignKey("feature_codes.code"), primary_key=True),
)

campaign_vehicles = Table(
    "campaign_vehicles",
    Base.metadata,
    Column("campaign_id", ForeignKey("campaigns.id"), primary_key=True),
    Column("vehicle_vin", ForeignKey("vehicles.vin"), primary_key=True),
)


class Vehicle(Base):
    __tablename__ = "vehicles"

    vin: Mapped[str] = mapped_column(String, primary_key=True)
    model: Mapped[str] = mapped_column(String, nullable=False)
    software_version: Mapped[str] = mapped_column(String, nullable=False)
    feature_codes: Mapped[list["FeatureCode"]] = relationship(
        secondary=vehicle_feature_codes, back_populates="vehicles"
    )
    campaigns: Mapped[list["Campaign"]] = relationship(
        secondary=campaign_vehicles, back_populates="vehicles"
    )


class FeatureCode(Base):
    __tablename__ = "feature_codes"

    code: Mapped[str] = mapped_column(String(5), primary_key=True)
    vehicles: Mapped[list[Vehicle]] = relationship(
        secondary=vehicle_feature_codes, back_populates="feature_codes"
    )
    target_campaigns: Mapped[list["Campaign"]] = relationship(
        secondary=campaign_target_feature_codes, back_populates="target_feature_codes"
    )


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    target_version: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default=text("'DRAFT'")
    )
    target_feature_codes: Mapped[list[FeatureCode]] = relationship(
        secondary=campaign_target_feature_codes, back_populates="target_campaigns"
    )
    vehicles: Mapped[list[Vehicle]] = relationship(
        secondary=campaign_vehicles, back_populates="campaigns"
    )
