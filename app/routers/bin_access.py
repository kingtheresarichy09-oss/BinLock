
import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models import (
    User,
    Bin,
    Subscription,
    BinAssignment,
    AccessCard,
    AccessAttempt,
)
from app.schemas import (
    BinAssignmentCreate,
    BinAssignmentResponse,
    AccessCardCreate,
    AccessCardResponse,
    AccessCardIssuedResponse,
    AccessCheckRequest,
    AccessAttemptResponse,
)

router = APIRouter(
    prefix="/bin-access",
    tags=["Bin Assignment and Access"],
)


def hash_card_code(card_code: str) -> str:
    return hashlib.sha256(card_code.encode()).hexdigest()


@router.post(
    "/assign",
    response_model=BinAssignmentResponse,
)
def assign_bin(
    assignment_data: BinAssignmentCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(
        User.id == assignment_data.user_id
    ).first()

    bin_item = db.query(Bin).filter(
        Bin.id == assignment_data.bin_id
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if not bin_item:
        raise HTTPException(status_code=404, detail="Bin not found.")

    if not user.is_active or not user.is_verified:
        raise HTTPException(
            status_code=400,
            detail="Household must be active and verified.",
        )

    if not bin_item.is_active or bin_item.status != "available":
        raise HTTPException(
            status_code=400,
            detail="Bin is not available for assignment.",
        )

    existing_assignment = db.query(BinAssignment).filter(
        BinAssignment.bin_id == bin_item.id,
        BinAssignment.status == "active",
    ).first()

    if existing_assignment:
        raise HTTPException(
            status_code=409,
            detail="This bin is already assigned.",
        )

    household_assignment = db.query(BinAssignment).filter(
        BinAssignment.user_id == user.id,
        BinAssignment.status == "active",
    ).first()

    if household_assignment:
        raise HTTPException(
            status_code=409,
            detail="This household already has an active bin assignment.",
        )

    assignment = BinAssignment(
        bin_id=bin_item.id,
        user_id=user.id,
        status="active",
    )

    bin_item.status = "assigned"

    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return assignment


@router.get(
    "/my-bin",
)
def get_my_bin(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assignment = db.query(BinAssignment).filter(
        BinAssignment.user_id == current_user.id,
        BinAssignment.status == "active",
    ).first()

    if not assignment:
        raise HTTPException(
            status_code=404,
            detail="You do not have an assigned bin.",
        )

    bin_item = db.query(Bin).filter(
        Bin.id == assignment.bin_id
    ).first()

    return {
        "assignment_id": assignment.id,
        "bin_id": bin_item.id,
        "bin_code": bin_item.bin_code,
        "location": bin_item.location,
        "status": bin_item.status,
        "assigned_at": assignment.assigned_at,
    }


@router.post(
    "/cards/issue",
    response_model=AccessCardIssuedResponse,
)
def issue_access_card(
    card_data: AccessCardCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    assignment = db.query(BinAssignment).filter(
        BinAssignment.id == card_data.assignment_id,
        BinAssignment.status == "active",
    ).first()

    if not assignment:
        raise HTTPException(
            status_code=404,
            detail="Active bin assignment not found.",
        )

    existing_card = db.query(AccessCard).filter(
        AccessCard.assignment_id == assignment.id,
        AccessCard.is_active == True,
    ).first()

    if existing_card:
        raise HTTPException(
            status_code=409,
            detail="This assignment already has an active access card.",
        )

    card_code = secrets.token_urlsafe(24)

    card = AccessCard(
        assignment_id=assignment.id,
        card_code_hash=hash_card_code(card_code),
        is_active=True,
    )

    db.add(card)
    db.commit()
    db.refresh(card)

    return {
        "id": card.id,
        "assignment_id": card.assignment_id,
        "card_code": card_code,
        "is_active": card.is_active,
    }


@router.get(
    "/cards/my-card",
    response_model=list[AccessCardResponse],
)
def get_my_cards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assignments = db.query(BinAssignment).filter(
        BinAssignment.user_id == current_user.id,
        BinAssignment.status == "active",
    ).all()

    assignment_ids = [item.id for item in assignments]

    if not assignment_ids:
        return []

    return db.query(AccessCard).filter(
        AccessCard.assignment_id.in_(assignment_ids),
        AccessCard.is_active == True,
    ).all()


@router.patch(
    "/cards/{card_id}/deactivate",
)
def deactivate_card(
    card_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    card = db.query(AccessCard).filter(
        AccessCard.id == card_id
    ).first()

    if not card:
        raise HTTPException(
            status_code=404,
            detail="Access card not found.",
        )

    card.is_active = False
    db.commit()

    return {"message": "Access card deactivated successfully."}


@router.post(
    "/check",
)
def check_bin_access(
    access_data: AccessCheckRequest,
    db: Session = Depends(get_db),
):
    bin_item = db.query(Bin).filter(
        Bin.id == access_data.bin_id
    ).first()

    if not bin_item:
        raise HTTPException(
            status_code=404,
            detail="Bin not found.",
        )

    card_hash = hash_card_code(access_data.card_code)

    card = db.query(AccessCard).filter(
        AccessCard.card_code_hash == card_hash,
        AccessCard.is_active == True,
    ).first()

    reason = "Access denied."
    authorised = False

    if not card:
        reason = "Invalid or inactive access card."

    else:
        assignment = db.query(BinAssignment).filter(
            BinAssignment.id == card.assignment_id,
            BinAssignment.bin_id == bin_item.id,
            BinAssignment.status == "active",
        ).first()

        if not assignment:
            reason = "Card is not assigned to this bin."

        else:
            now = datetime.now(timezone.utc)

            subscription = db.query(Subscription).filter(
                Subscription.user_id == assignment.user_id,
                Subscription.status == "active",
                Subscription.expiry_date > now,
            ).order_by(
                Subscription.expiry_date.desc()
            ).first()

            if not subscription:
                reason = "No valid active subscription."

            elif not bin_item.is_active:
                reason = "Bin is inactive."

            else:
                authorised = True
                reason = "Access authorised."
                card.last_used_at = now

    attempt = AccessAttempt(
        bin_id=bin_item.id,
        card_id=card.id if card else None,
        authorised=authorised,
        reason=reason,
    )

    db.add(attempt)
    db.commit()

    return {
        "authorised": authorised,
        "message": reason,
        "simulation": True,
    }


@router.get(
    "/attempts",
    response_model=list[AccessAttemptResponse],
)
def get_access_attempts(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return db.query(AccessAttempt).order_by(
        AccessAttempt.created_at.desc()
    ).all()
