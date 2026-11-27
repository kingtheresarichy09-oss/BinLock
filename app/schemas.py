from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator
class UserRegister(BaseModel):
    customer_type: Literal["household", "organisation"]
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    address: str = Field(min_length=5, max_length=255)

    full_name: str | None = None
    number_of_occupants: int | None = Field(default=None, ge=1)
    organisation_name: str | None = None
    registration_number: str | None = None
    industry: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    estimated_monthly_waste_kg: float | None = Field(default=None, gt=0)
    service_requirements: str | None = None

    @model_validator(mode="after")
    def validate_customer_details(self):
        if self.customer_type == "household":
            if not self.full_name or self.number_of_occupants is None:
                raise ValueError(
                    "Household registration requires full_name "
                    "and number_of_occupants."
                )

        elif self.customer_type == "organisation":
            if not self.organisation_name or not self.contact_person or not self.phone:
                raise ValueError(
                    "Organisation registration requires organisation_name, "
                    "contact_person and phone."
                )

        return self

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
    customer_type: str
    is_verified: bool

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
    service_tier: Literal["basic", "standard", "premium"] | None = None


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    plan: str
    amount: int
    status: str
    service_tier: str | None = None
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


class OrganisationRegister(BaseModel):
    organisation_name: str = Field(min_length=2, max_length=200)
    registration_number: str | None = Field(default=None, max_length=100)
    industry: str | None = Field(default=None, max_length=100)
    contact_person: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=30)
    address: str = Field(min_length=5, max_length=255)
    estimated_monthly_waste_kg: int | None = Field(default=None, ge=1)
    service_requirements: str | None = Field(default=None, max_length=2000)


class OrganisationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_user_id: int
    organisation_name: str
    registration_number: str | None
    industry: str | None
    contact_person: str
    email: EmailStr
    phone: str
    address: str
    estimated_monthly_waste_kg: int | None
    service_requirements: str | None
    status: str
    created_at: datetime


class OrganisationStatusUpdate(BaseModel):
    status: Literal["approved", "rejected"]


# COLLECTION TEAMS

class CollectionTeamCreate(BaseModel):
    team_name: str = Field(min_length=2, max_length=150)
    contact_person: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=7, max_length=30)


class CollectionTeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_name: str
    contact_person: str
    phone: str
    is_active: bool
    created_at: datetime


# COLLECTION SCHEDULES

class CollectionScheduleCreate(BaseModel):
    user_id: int = Field(ge=1)
    bin_id: int = Field(ge=1)
    team_id: int | None = Field(default=None, ge=1)
    scheduled_for: datetime
    notes: str | None = None


class CollectionScheduleStatusUpdate(BaseModel):
    status: Literal["scheduled", "in_progress", "completed", "missed", "cancelled"]


class CollectionScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    bin_id: int
    team_id: int | None
    scheduled_for: datetime
    status: str
    notes: str | None
    created_at: datetime


class CollectionRecordCreate(BaseModel):
    status: Literal["completed", "missed"]
    waste_collected_kg: int | None = Field(default=None, ge=0)
    notes: str | None = None


class CollectionRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    schedule_id: int
    status: str
    waste_collected_kg: int | None
    notes: str | None
    completed_at: datetime | None
    created_at: datetime


# EXTRA PICKUPS

class ExtraPickupCreate(BaseModel):
    bin_id: int = Field(ge=1)
    requested_for: datetime | None = None
    reason: str = Field(min_length=5, max_length=1000)


class ExtraPickupStatusUpdate(BaseModel):
    status: Literal["approved", "scheduled", "completed", "rejected", "cancelled"]


class ExtraPickupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    bin_id: int
    requested_for: datetime | None
    reason: str
    status: str
    created_at: datetime


# COMPLAINTS

class ComplaintCreate(BaseModel):
    bin_id: int | None = Field(default=None, ge=1)
    category: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=10, max_length=2000)


class ComplaintUpdate(BaseModel):
    status: Literal["open", "in_review", "resolved", "rejected"]
    admin_response: str | None = Field(default=None, max_length=2000)


class ComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    bin_id: int | None
    category: str
    description: str
    status: str
    admin_response: str | None
    created_at: datetime
    resolved_at: datetime | None


# DELIVERIES

class DeliveryCreate(BaseModel):
    user_id: int = Field(ge=1)
    bin_id: int = Field(ge=1)
    delivery_address: str = Field(min_length=5, max_length=255)
    scheduled_for: datetime | None = None


class DeliveryUpdate(BaseModel):
    status: Literal["pending", "scheduled", "in_transit", "delivered", "failed"]
    delivered_at: datetime | None = None
    installation_notes: str | None = Field(default=None, max_length=2000)


class DeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    bin_id: int
    delivery_address: str
    status: str
    scheduled_for: datetime | None
    delivered_at: datetime | None
    installation_notes: str | None
    created_at: datetime


class OrganisationServiceTierCreate(BaseModel):
    tier_name: Literal["basic", "standard", "premium"]

    weekly_price: int | None = Field(default=None, ge=1)
    monthly_price: int | None = Field(default=None, ge=1)

    max_monthly_waste_kg: int | None = Field(default=None, ge=1)

    features: list[str] = Field(default_factory=list)
    is_active: bool = True


class OrganisationServiceTierUpdate(BaseModel):
    weekly_price: int | None = Field(default=None, ge=1)
    monthly_price: int | None = Field(default=None, ge=1)

    max_monthly_waste_kg: int | None = Field(default=None, ge=1)

    features: list[str] | None = None
    is_active: bool | None = None


class OrganisationServiceTierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tier_name: str
    weekly_price: int | None
    monthly_price: int | None
    max_monthly_waste_kg: int | None
    features: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime