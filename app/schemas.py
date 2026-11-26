from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, ConfigDict

class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    address: str = Field(min_length=5, max_length=255)
    number_of_occupants: int = Field(ge=1)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    address: str | None
    number_of_occupants: int | None
    role: str
    is_verified: bool


# =========================
# BIN SCHEMAS
# =========================

class BinCreate(BaseModel):
    bin_code: str = Field(min_length=3, max_length=50)
    location: str = Field(min_length=3, max_length=255)


class BinUpdate(BaseModel):
    location: str | None = Field(
        default=None,
        min_length=3,
        max_length=255
    )
    status: str | None = None
    is_active: bool | None = None


class BinResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bin_code: str
    location: str
    status: str
    is_active: bool

class PickupRequestCreate(BaseModel):
    bin_id: int
    description: str = Field(min_length=5, max_length=1000)


class PickupRequestStatusUpdate(BaseModel):
    status: Literal[
        "approved",
        "in_progress",
        "completed",
        "cancelled"
    ]


class PickupRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    bin_id: int
    description: str
    status: str
    created_at: datetime


class SubscriptionCreate(BaseModel):
    plan: Literal["weekly", "monthly"]


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    plan: str
    amount: int
    status: str
    start_date: datetime | None
    expiry_date: datetime | None
    created_at: datetime


class SubscriptionStatusUpdate(BaseModel):
    status: Literal["active", "expired", "cancelled"]


class PaymentCreate(BaseModel):
    subscription_id: int = Field(ge=1)


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    subscription_id: int
    amount: int
    reference: str
    provider: str
    status: str
    paid_at: datetime | None
    created_at: datetime


class PaymentStatusUpdate(BaseModel):
    status: Literal["pending", "successful", "failed"]


class PaymentInitializationResponse(BaseModel):
    payment_id: int
    reference: str
    authorization_url: str | None
    access_code: str | None
    amount: int
    currency: str
    status: str


class PaymentVerificationResponse(BaseModel):
    reference: str
    status: str
    amount: int
    message: str


class BinAssignmentCreate(BaseModel):
    bin_id: int = Field(ge=1)
    user_id: int = Field(ge=1)


class BinAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bin_id: int
    user_id: int
    status: str
    assigned_at: datetime
    unassigned_at: datetime | None


class AccessCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assignment_id: int
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None


class AccessCardCreate(BaseModel):
    assignment_id: int = Field(ge=1)


class AccessCardIssuedResponse(BaseModel):
    id: int
    assignment_id: int
    card_code: str
    is_active: bool


class AccessAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bin_id: int
    card_id: int | None
    authorised: bool
    reason: str
    created_at: datetime


class AccessCheckRequest(BaseModel):
    bin_id: int = Field(ge=1)
    card_code: str = Field(min_length=12, max_length=100)
