from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
)

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String(150), nullable=False)

    email = Column(String(255), unique=True, index=True, nullable=False)

    address = Column(String(255), nullable=True)

    number_of_occupants = Column(Integer, nullable=True)

    hashed_password = Column(String(255), nullable=False)

    role = Column(String(50), default="user", nullable=False)

    customer_type = Column(String(50), default="household", nullable=False)

    is_active = Column(Boolean, default=False, nullable=False)

    is_verified = Column(Boolean, default=False, nullable=False)

    verification_token_hash = Column(String(255), nullable=True)

    verification_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Bin(Base):
    __tablename__ = "bins"

    id = Column(Integer, primary_key=True, index=True)

    bin_code = Column(String(50), unique=True, index=True, nullable=False)

    location = Column(String(255), nullable=False)

    status = Column(String(50), default="available", nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class PickupRequest(Base):
    __tablename__ = "pickup_requests"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    bin_id = Column(Integer, ForeignKey("bins.id"), nullable=False)

    description = Column(Text, nullable=False)

    status = Column(String(50), default="pending", nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan = Column(String(50), nullable=False)
    amount = Column(Integer, nullable=False)
    service_tier = Column(String(30), nullable=True)
    status = Column(String(50), default="pending", nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=True)
    expiry_reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
    expired_reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    subscription_id = Column(
        Integer,
        ForeignKey("subscriptions.id"),
        nullable=False,
    )

    amount = Column(Integer, nullable=False)

    reference = Column(String(100), unique=True, index=True, nullable=False)

    provider = Column(String(50), default="manual", nullable=False)

    status = Column(String(50), default="pending", nullable=False)

    paid_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class BinAssignment(Base):
    __tablename__ = "bin_assignments"

    id = Column(Integer, primary_key=True, index=True)

    bin_id = Column(Integer, ForeignKey("bins.id"), nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    status = Column(String(50), default="active", nullable=False)

    assigned_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    unassigned_at = Column(DateTime(timezone=True), nullable=True)


class AccessCard(Base):
    __tablename__ = "access_cards"

    id = Column(Integer, primary_key=True, index=True)

    assignment_id = Column(
        Integer,
        ForeignKey("bin_assignments.id"),
        nullable=False,
    )

    card_code_hash = Column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    last_used_at = Column(DateTime(timezone=True), nullable=True)


class AccessAttempt(Base):
    __tablename__ = "access_attempts"

    id = Column(Integer, primary_key=True, index=True)

    bin_id = Column(Integer, ForeignKey("bins.id"), nullable=False)

    card_id = Column(
        Integer,
        ForeignKey("access_cards.id"),
        nullable=True,
    )

    authorised = Column(Boolean, nullable=False)

    reason = Column(String(255), nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Organisation(Base):
    __tablename__ = "organisations"

    id = Column(Integer, primary_key=True, index=True)

    owner_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )

    organisation_name = Column(String(200), nullable=False)

    registration_number = Column(String(100), nullable=True)

    industry = Column(String(100), nullable=True)

    contact_person = Column(String(150), nullable=False)

    email = Column(String(255), nullable=False, index=True)

    phone = Column(String(30), nullable=False)

    address = Column(String(255), nullable=False)

    estimated_monthly_waste_kg = Column(Integer, nullable=True)

    service_requirements = Column(Text, nullable=True)

    status = Column(String(50), default="pending", nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class OrganisationServiceTier(Base):
    __tablename__ = "organisation_service_tiers"

    id = Column(Integer, primary_key=True, index=True)

    tier_name = Column(String(30), unique=True, index=True, nullable=False)

    weekly_price = Column(Integer, nullable=True)
    monthly_price = Column(Integer, nullable=True)

    max_monthly_waste_kg = Column(Integer, nullable=True)

    features = Column(JSON, default=list, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class CollectionTeam(Base):
    __tablename__ = "collection_teams"

    id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String(150), nullable=False)
    contact_person = Column(String(150), nullable=False)
    phone = Column(String(30), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class CollectionSchedule(Base):
    __tablename__ = "collection_schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bin_id = Column(Integer, ForeignKey("bins.id"), nullable=False)
    team_id = Column(
        Integer,
        ForeignKey("collection_teams.id"),
        nullable=True,
    )
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="scheduled", nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class CollectionRecord(Base):
    __tablename__ = "collection_records"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(
        Integer,
        ForeignKey("collection_schedules.id"),
        nullable=False,
    )
    status = Column(String(50), nullable=False)
    waste_collected_kg = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ExtraPickup(Base):
    __tablename__ = "extra_pickups"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bin_id = Column(Integer, ForeignKey("bins.id"), nullable=False)
    requested_for = Column(DateTime(timezone=True), nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(String(50), default="pending", nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    bin_id = Column(Integer, ForeignKey("bins.id"), nullable=True)
    category = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), default="open", nullable=False)
    admin_response = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    bin_id = Column(Integer, ForeignKey("bins.id"), nullable=False)

    delivery_address = Column(String(255), nullable=False)

    status = Column(String(50), default="pending", nullable=False)

    scheduled_for = Column(DateTime(timezone=True), nullable=True)

    delivered_at = Column(DateTime(timezone=True), nullable=True)

    installation_notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
