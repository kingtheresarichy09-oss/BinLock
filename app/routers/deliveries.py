from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models import Delivery, User, Bin, BinAssignment
from app.schemas import DeliveryCreate, DeliveryUpdate, DeliveryResponse

router = APIRouter(prefix="/deliveries", tags=["Deliveries"])


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
    user = db.query(User).filter(User.id == data.user_id).first()
    bin_item = db.query(Bin).filter(Bin.id == data.bin_id).first()

    if not user or not bin_item:
        raise HTTPException(status_code=404, detail="User or bin not found.")

    delivery = Delivery(**data.model_dump())
    db.add(delivery)
    db.commit()
    db.refresh(delivery)
    return delivery


@router.get("/my-deliveries", response_model=list[DeliveryResponse])
def my_deliveries(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return db.query(Delivery).filter(
        Delivery.user_id == current_user.id
    ).order_by(Delivery.created_at.desc()).all()


@router.get("/", response_model=list[DeliveryResponse])
def all_deliveries(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    return db.query(Delivery).order_by(Delivery.created_at.desc()).all()


@router.patch("/{delivery_id}", response_model=DeliveryResponse)
def update_delivery(
    delivery_id: int,
    data: DeliveryUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    delivery = db.query(Delivery).filter(
        Delivery.id == delivery_id
    ).first()

    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found.")

    delivery.status = data.status
    delivery.installation_notes = data.installation_notes

    if data.status == "delivered":
        delivery.delivered_at = data.delivered_at or datetime.now(timezone.utc)
        bin_item = db.query(Bin).filter(Bin.id == delivery.bin_id).first()
        if bin_item:
            bin_item.status = "assigned"

        assignment = db.query(BinAssignment).filter(
            BinAssignment.user_id == delivery.user_id,
            BinAssignment.bin_id == delivery.bin_id,
            BinAssignment.status == "active",
        ).first()

        if not assignment:
            assignment = BinAssignment(
                user_id=delivery.user_id,
                bin_id=delivery.bin_id,
                status="active",
            )
            db.add(assignment)

    db.commit()
    db.refresh(delivery)
    return delivery
