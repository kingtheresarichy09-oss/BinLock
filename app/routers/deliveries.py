from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin, get_current_user
from app.models import Delivery, User, Bin, BinAssignment
from app.schemas import DeliveryCreate, DeliveryUpdate, DeliveryResponse


router = APIRouter(prefix="/deliveries", tags=["Deliveries"])

ALLOWED_TRANSITIONS = {
    "pending": {"scheduled", "in_transit", "delivered", "failed"},
    "scheduled": {"in_transit", "delivered", "failed"},
    "in_transit": {"delivered", "failed"},
    "failed": {"scheduled"},
    "delivered": set(),
}

IN_PROGRESS_STATUSES = {"pending", "scheduled", "in_transit"}


def get_active_assignment(db: Session, bin_id: int):
    return db.query(BinAssignment).filter(
        BinAssignment.bin_id == bin_id,
        BinAssignment.status == "active",
    ).first()


def assign_delivered_bin(
    db: Session,
    user_id: int,
    bin_id: int,
):
    """Assign a bin only after its delivery has been confirmed."""

    bin_item = db.query(Bin).filter(
        Bin.id == bin_id
    ).with_for_update().first()

    if not bin_item:
        raise HTTPException(
            status_code=404,
            detail="Bin not found.",
        )

    if not bin_item.is_active:
        raise HTTPException(
            status_code=400,
            detail="This bin is inactive and cannot be assigned.",
        )

    existing_assignment = get_active_assignment(db, bin_id)

    if existing_assignment:
        if existing_assignment.user_id == user_id:
            return

        raise HTTPException(
            status_code=409,
            detail="This bin is already assigned to another customer.",
        )

    # Follow the current BinLock rule of one active bin per customer.
    customer_assignment = db.query(BinAssignment).filter(
        BinAssignment.user_id == user_id,
        BinAssignment.status == "active",
    ).first()

    if customer_assignment:
        raise HTTPException(
            status_code=409,
            detail="This customer already has an active bin assignment.",
        )

    if bin_item.status != "available":
        raise HTTPException(
            status_code=409,
            detail="This bin is not available for assignment.",
        )

    assignment = BinAssignment(
        user_id=user_id,
        bin_id=bin_id,
        status="active",
    )

    bin_item.status = "assigned"
    db.add(assignment)


@router.post(
    "/",
    response_model=DeliveryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_delivery(
    data: DeliveryCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    # Lock the bin row while checking availability.
    bin_item = db.query(Bin).filter(
        Bin.id == data.bin_id
    ).with_for_update().first()

    if not bin_item:
        raise HTTPException(
            status_code=404,
            detail="Bin not found.",
        )

    user = db.query(User).filter(
        User.id == data.user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )

    if not user.is_active or not user.is_verified:
        raise HTTPException(
            status_code=400,
            detail="The customer must have an active, verified account.",
        )

    if not bin_item.is_active:
        raise HTTPException(
            status_code=400,
            detail="This bin is inactive.",
        )

    if bin_item.status != "available":
        raise HTTPException(
            status_code=409,
            detail="This bin is not available for delivery.",
        )

    if get_active_assignment(db, data.bin_id):
        raise HTTPException(
            status_code=409,
            detail="This bin is already assigned.",
        )

    existing_delivery = db.query(Delivery).filter(
        Delivery.bin_id == data.bin_id,
        Delivery.status.in_(IN_PROGRESS_STATUSES),
    ).first()

    if existing_delivery:
        raise HTTPException(
            status_code=409,
            detail="An active delivery already exists for this bin.",
        )

    delivery = Delivery(**data.model_dump())

    db.add(delivery)
    db.commit()
    db.refresh(delivery)

    return delivery


@router.get(
    "/my-deliveries",
    response_model=list[DeliveryResponse],
)
def my_deliveries(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return db.query(Delivery).filter(
        Delivery.user_id == current_user.id
    ).order_by(
        Delivery.created_at.desc()
    ).all()


@router.get(
    "/",
    response_model=list[DeliveryResponse],
)
def all_deliveries(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    return db.query(Delivery).order_by(
        Delivery.created_at.desc()
    ).all()


@router.patch(
    "/{delivery_id}",
    response_model=DeliveryResponse,
)
def update_delivery(
    delivery_id: int,
    data: DeliveryUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    delivery = db.query(Delivery).filter(
        Delivery.id == delivery_id
    ).with_for_update().first()

    if not delivery:
        raise HTTPException(
            status_code=404,
            detail="Delivery not found.",
        )

    old_status = delivery.status
    new_status = data.status

    if new_status != old_status:
        allowed = ALLOWED_TRANSITIONS.get(old_status, set())

        if new_status not in allowed:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Invalid delivery status transition: "
                    f"{old_status} to {new_status}."
                ),
            )

    if new_status == "delivered":
        assign_delivered_bin(
            db=db,
            user_id=delivery.user_id,
            bin_id=delivery.bin_id,
        )

        delivery.delivered_at = (
            data.delivered_at or datetime.now(timezone.utc)
        )
    else:
        delivery.delivered_at = None

    delivery.status = new_status
    delivery.installation_notes = data.installation_notes

    try:
        db.commit()
        db.refresh(delivery)
    except Exception:
        db.rollback()
        raise

    return delivery
