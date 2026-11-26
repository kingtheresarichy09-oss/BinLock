from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PickupRequest, Bin, User
from app.schemas import (
    PickupRequestCreate,
    PickupRequestStatusUpdate,
    PickupRequestResponse,
)
from app.dependencies import get_current_user, require_admin


router = APIRouter(
    prefix="/pickups",
    tags=["Pickup Management"]
)


@router.post(
    "/",
    response_model=PickupRequestResponse,
    status_code=status.HTTP_201_CREATED
)
def create_pickup_request(
    pickup_data: PickupRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    bin_record = db.query(Bin).filter(
        Bin.id == pickup_data.bin_id,
        Bin.is_active.is_(True)
    ).first()

    if not bin_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active bin not found."
        )

    new_request = PickupRequest(
        user_id=current_user.id,
        bin_id=pickup_data.bin_id,
        description=pickup_data.description
    )

    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    return new_request


@router.get(
    "/my-requests",
    response_model=list[PickupRequestResponse]
)
def get_my_pickup_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(PickupRequest).filter(
        PickupRequest.user_id == current_user.id
    ).all()


@router.get(
    "/",
    response_model=list[PickupRequestResponse]
)
def get_all_pickup_requests(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    return db.query(PickupRequest).all()


@router.get(
    "/{request_id}",
    response_model=PickupRequestResponse
)
def get_pickup_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pickup = db.query(PickupRequest).filter(
        PickupRequest.id == request_id
    ).first()

    if not pickup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pickup request not found."
        )

    if (
        current_user.role != "admin"
        and pickup.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )

    return pickup


@router.patch(
    "/{request_id}/status",
    response_model=PickupRequestResponse
)
def update_pickup_status(
    request_id: int,
    status_data: PickupRequestStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    pickup = db.query(PickupRequest).filter(
        PickupRequest.id == request_id
    ).first()

    if not pickup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pickup request not found."
        )

    allowed_transitions = {
        "pending": ["approved", "cancelled"],
        "approved": ["in_progress", "cancelled"],
        "in_progress": ["completed", "cancelled"],
        "completed": [],
        "cancelled": []
    }

    if status_data.status not in allowed_transitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pickup status."
        )

    if status_data.status not in allowed_transitions[pickup.status]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot change status from {pickup.status} "
                f"to {status_data.status}."
            )
        )

    pickup.status = status_data.status

    db.commit()
    db.refresh(pickup)

    return pickup
