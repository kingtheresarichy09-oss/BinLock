from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
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

    is_active = Column(Boolean, default=False, nullable=False)

    is_verified = Column(Boolean, default=False, nullable=False)

    verification_token_hash = Column(String(255), nullable=True)

    verification_token_expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
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
    status = Column(String(50), default="pending", nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=True)
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
        nullable=False
    )

    amount = Column(Integer, nullable=False)

    reference = Column(String(100), unique=True, index=True, nullable=False)

    provider = Column(String(50), default="manual", nullable=False)

    status = Column(String(50), default="pending", nullable=False)

    paid_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
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
