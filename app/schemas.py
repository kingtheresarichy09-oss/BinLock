from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    model_config = {
        "from_attributes": True
    }

    id: int
    full_name: str
    email: EmailStr
    role: str
    is_verified: bool

class BinCreate(BaseModel):
    bin_code: str = Field(min_length=3, max_length=50)
    location: str = Field(min_length=3, max_length=255)


class BinUpdate(BaseModel):
    location: str | None = Field(default=None, min_length=3, max_length=255)
    status: str | None = None
    is_active: bool | None = None


class BinResponse(BaseModel):
    model_config = {
        "from_attributes": True
    }

    id: int
    bin_code: str
    location: str
    status: str
    is_active: bool

class PickupRequestCreate(BaseModel):
    bin_id: int
    description: str = Field(min_length=5, max_length=1000)


class PickupRequestStatusUpdate(BaseModel):
    status: str


class PickupRequestResponse(BaseModel):
    model_config = {
        "from_attributes": True
    }

    id: int
    user_id: int
    bin_id: int
    description: str
    status: str
    created_at: datetime