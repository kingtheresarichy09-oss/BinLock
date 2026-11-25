from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Subscription
from app.schemas import (
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionStatusUpdate,
)
from app.dependencies import get_current_user, require_admin


router = APIRouter(
    prefix="/subscriptions",
    tags=["Subscriptions"]
)


# Prices are controlled by the backend.
SUBSCRIPTION_PRICES = {
    "weekly": 1500,
    "monthly": 5000,
}


@router.post(
    "/",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED
)
def create_subscription(
    subscription_data: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    existing_subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status.in_(["pending", "active"])
    ).first()

    if existing_subscription:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a pending or active subscription."
        )

    plan = subscription_data.plan
    amount = SUBSCRIPTION_PRICES[plan]

    new_subscription = Subscription(
        user_id=current_user.id,
        plan=plan,
        amount=amount,
        status="pending"
    )

    db.add(new_subscription)
    db.commit()
    db.refresh(new_subscription)

    return new_subscription


@router.get(
    "/my-subscriptions",
    response_model=list[SubscriptionResponse]
)
def get_my_subscriptions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).order_by(Subscription.created_at.desc()).all()

    return subscriptions


# Admin views all subscriptions.
@router.get(
    "/",
    response_model=list[SubscriptionResponse]
)
def get_all_subscriptions(
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    return db.query(Subscription).order_by(
        Subscription.created_at.desc()
    ).all()


@router.patch(
    "/{subscription_id}/status",
    response_model=SubscriptionResponse
)
def update_subscription_status(
    subscription_id: int,
    status_data: SubscriptionStatusUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found."
        )

    new_status = status_data.status

    if new_status == "active":
        if subscription.status != "active":
            now = datetime.now(timezone.utc)

            duration = (
                timedelta(days=7)
                if subscription.plan == "weekly"
                else timedelta(days=30)
            )

            subscription.start_date = now
            subscription.expiry_date = now + duration

    elif new_status == "expired":
        subscription.expiry_date = datetime.now(timezone.utc)

    subscription.status = new_status

    db.commit()
    db.refresh(subscription)

    return subscription
