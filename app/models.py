from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database import Base

class User(Base):
    __tablename__="users"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String(150), nullable=False)

    email = Column(String(255), unique=True, index=True, nullable=False)

    hashed_password = Column(String(255), nullable=False)

    role = Column(String(50), default="user", nullable=False)

    is_active = Column(Boolean, default=False, nullable=False)

    is_verified = Column(Boolean, default=False, nullable=False)

    verification_token_hash = Column(String(255), nullable=True)

    verification_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
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
        nullable=False
    )