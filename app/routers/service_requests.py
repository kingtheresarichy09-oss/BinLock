from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models import ExtraPickup, Complaint, Bin, BinAssignment
from app.schemas import (
    ExtraPickupCreate,
    ExtraPickupStatusUpdate,
    ExtraPickupResponse,
    ComplaintCreate,
    ComplaintUpdate,
    ComplaintResponse,
)

router = APIRouter(prefix="/service-requests", tags=["Service Requests"])


def verify_customer_bin(db: Session, user_id: int, bin_id: int):
    assignment = db.query(BinAssignment).filter(
        BinAssignment.user_id == user_id,
        BinAssignment.bin_id == bin_id,
        BinAssignment.status == "active",
    ).first()

    if not assignment:
        raise HTTPException(
            status_code=403,
            detail="You can only request services for a bin assigned to your account.",
        )


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
    verify_customer_bin(db, current_user.id, data.bin_id)

    request = ExtraPickup(
        user_id=current_user.id,
        **data.model_dump(),
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


@router.get("/my-extra-pickups", response_model=list[ExtraPickupResponse])
def my_extra_pickups(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return db.query(ExtraPickup).filter(
        ExtraPickup.user_id == current_user.id
    ).order_by(ExtraPickup.created_at.desc()).all()


@router.get("/extra-pickups", response_model=list[ExtraPickupResponse])
def all_extra_pickups(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    return db.query(ExtraPickup).order_by(
        ExtraPickup.created_at.desc()
    ).all()


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
    request = db.query(ExtraPickup).filter(
        ExtraPickup.id == request_id
    ).first()

    if not request:
        raise HTTPException(status_code=404, detail="Extra pickup request not found.")

    request.status = data.status
    db.commit()
    db.refresh(request)
    return request


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
    if data.bin_id is not None:
        verify_customer_bin(db, current_user.id, data.bin_id)

    complaint = Complaint(
        user_id=current_user.id,
        **data.model_dump(),
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint


@router.get("/my-complaints", response_model=list[ComplaintResponse])
def my_complaints(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return db.query(Complaint).filter(
        Complaint.user_id == current_user.id
    ).order_by(Complaint.created_at.desc()).all()


@router.get("/complaints", response_model=list[ComplaintResponse])
def all_complaints(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    return db.query(Complaint).order_by(Complaint.created_at.desc()).all()


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
    complaint = db.query(Complaint).filter(
        Complaint.id == complaint_id
    ).first()

    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    complaint.status = data.status
    complaint.admin_response = data.admin_response

    if data.status == "resolved":
        complaint.resolved_at = datetime.now(timezone.utc)
    else:
        complaint.resolved_at = None

    db.commit()
    db.refresh(complaint)
    return complaint
