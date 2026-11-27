from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models import (
    ExtraPickup,
    Complaint,
    Bin,
    BinAssignment,
    Subscription,
)
from app.schemas import (
    ExtraPickupCreate,
    ExtraPickupStatusUpdate,
    ExtraPickupResponse,
    ComplaintCreate,
    ComplaintUpdate,
    ComplaintResponse,
)

router = APIRouter(
    prefix="/service-requests",
    tags=["Service Requests"],
)


def to_utc(value: datetime) -> datetime:
    
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def verify_customer_bin(
    db: Session,
    user_id: int,
    bin_id: int,
) -> None:
    
    assignment = (
        db.query(BinAssignment)
        .filter(
            BinAssignment.user_id == user_id,
            BinAssignment.bin_id == bin_id,
            BinAssignment.status == "active",
        )
        .first()
    )

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have an active assignment for this bin.",
        )

    bin_item = db.query(Bin).filter(Bin.id == bin_id).first()

    if not bin_item or not bin_item.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This bin is not active.",
        )


def ensure_active_subscription(
    db: Session,
    user_id: int,
) -> None:
    
    now = datetime.now(timezone.utc)

    subscriptions = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status == "active",
        )
        .all()
    )

    for subscription in subscriptions:
        if not subscription.start_date or not subscription.expiry_date:
            continue

        start_date = to_utc(subscription.start_date)
        expiry_date = to_utc(subscription.expiry_date)

        if start_date <= now < expiry_date:
            return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="An active, valid subscription is required to request an extra pickup.",
    )


EXTRA_PICKUP_TRANSITIONS = {
    "pending": {"approved", "rejected", "cancelled"},
    "approved": {"scheduled", "rejected", "cancelled"},
    "scheduled": {"completed", "cancelled"},
    "completed": set(),
    "rejected": set(),
    "cancelled": set(),
}


@router.post(
    "/extra-pickups",
    response_model=ExtraPickupResponse,
    status_code=status.HTTP_201_CREATED,
)
def request_extra_pickup(
    data: ExtraPickupCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ensure_active_subscription(db, current_user.id)

    verify_customer_bin(
        db,
        current_user.id,
        data.bin_id,
    )

    extra_pickup = ExtraPickup(
        user_id=current_user.id,
        **data.model_dump(),
    )

    db.add(extra_pickup)
    db.commit()
    db.refresh(extra_pickup)

    return extra_pickup


@router.get(
    "/my-extra-pickups",
    response_model=list[ExtraPickupResponse],
)
def my_extra_pickups(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return (
        db.query(ExtraPickup)
        .filter(ExtraPickup.user_id == current_user.id)
        .order_by(ExtraPickup.created_at.desc())
        .all()
    )


@router.get(
    "/extra-pickups",
    response_model=list[ExtraPickupResponse],
)
def all_extra_pickups(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    return (
        db.query(ExtraPickup)
        .order_by(ExtraPickup.created_at.desc())
        .all()
    )


@router.patch(
    "/extra-pickups/{request_id}",
    response_model=ExtraPickupResponse,
)
def update_extra_pickup(
    request_id: int,
    data: ExtraPickupStatusUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    extra_pickup = (
        db.query(ExtraPickup)
        .filter(ExtraPickup.id == request_id)
        .first()
    )

    if not extra_pickup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extra pickup request not found.",
        )

    current_status = extra_pickup.status
    new_status = data.status

    allowed_transitions = EXTRA_PICKUP_TRANSITIONS.get(
        current_status,
        set(),
    )

    if new_status not in allowed_transitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid extra pickup status transition: "
                f"{current_status} -> {new_status}."
            ),
        )

    extra_pickup.status = new_status

    db.commit()
    db.refresh(extra_pickup)

    return extra_pickup


@router.post(
    "/complaints",
    response_model=ComplaintResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_complaint(
    data: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Complaints remain available even when a subscription has expired.
    if data.bin_id is not None:
        verify_customer_bin(
            db,
            current_user.id,
            data.bin_id,
        )

    complaint = Complaint(
        user_id=current_user.id,
        **data.model_dump(),
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    return complaint


@router.get(
    "/my-complaints",
    response_model=list[ComplaintResponse],
)
def my_complaints(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return (
        db.query(Complaint)
        .filter(Complaint.user_id == current_user.id)
        .order_by(Complaint.created_at.desc())
        .all()
    )


@router.get(
    "/complaints",
    response_model=list[ComplaintResponse],
)
def all_complaints(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    return (
        db.query(Complaint)
        .order_by(Complaint.created_at.desc())
        .all()
    )


@router.patch(
    "/complaints/{complaint_id}",
    response_model=ComplaintResponse,
)
def update_complaint(
    complaint_id: int,
    data: ComplaintUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == complaint_id)
        .first()
    )

    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found.",
        )

    update_data = data.model_dump(exclude_unset=True)

    if "status" in update_data:
        new_status = update_data["status"]

        if new_status == "resolved":
            complaint.resolved_at = datetime.now(timezone.utc)
        else:
            complaint.resolved_at = None

    for field, value in update_data.items():
        setattr(complaint, field, value)

    db.commit()
    db.refresh(complaint)

    return complaint
