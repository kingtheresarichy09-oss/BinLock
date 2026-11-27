import logging

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models import (
    Subscription,
    Organisation,
    OrganisationServiceTier,
    User,
)
from app.schemas import (
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionStatusUpdate,
)
from app.email_service import (
    create_expiry_reminder_email,
    create_subscription_expired_email,
)
from app.email_sender import send_email


router = APIRouter(
    prefix="/subscriptions",
    tags=["Subscriptions"],
)

logger = logging.getLogger(__name__)


HOUSEHOLD_PRICES = {
    "weekly": 1500,
    "monthly": 5000,
}


def get_utc_datetime(value: datetime) -> datetime:
    """Ensure database datetimes are timezone-aware UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def ensure_organisation_approved(
    db: Session,
    user: User,
) -> None:
    """
    Prevent organisations from subscribing before admin approval.

    Household accounts do not require organisation approval.
    """

    if user.customer_type != "organisation":
        return

    organisation = db.query(Organisation).filter(
        Organisation.owner_user_id == user.id
    ).first()

    if not organisation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No organisation registration was found for this account.",
        )

    if (organisation.status or "").strip().lower() != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Your organisation registration has not been approved yet. "
                "Please wait for BinLock administration to approve it."
            ),
        )


def process_expired_subscriptions(db: Session) -> int:
    """Mark active subscriptions as expired when their expiry date passes."""
    now = datetime.now(timezone.utc)

    subscriptions = db.query(Subscription).filter(
        Subscription.status == "active",
        Subscription.expiry_date.isnot(None),
    ).all()

    expired_count = 0

    for subscription in subscriptions:
        expiry_date = get_utc_datetime(subscription.expiry_date)

        if expiry_date <= now:
            subscription.status = "expired"
            expired_count += 1

    if expired_count:
        db.commit()

    return expired_count


def process_subscription_reminders(db: Session) -> dict:
    process_expired_subscriptions(db)

    now = datetime.now(timezone.utc)
    reminder_deadline = now + timedelta(days=3)

    upcoming_sent = 0
    expired_sent = 0
    failed = 0

    # UPCOMING EXPIRY REMINDERS

    upcoming_subscriptions = db.query(Subscription).filter(
        Subscription.status == "active",
        Subscription.expiry_date.isnot(None),
        Subscription.expiry_reminder_sent_at.is_(None),
    ).all()

    for subscription in upcoming_subscriptions:
        expiry_date = get_utc_datetime(subscription.expiry_date)

        if not now < expiry_date <= reminder_deadline:
            continue

        user = db.query(User).filter(
            User.id == subscription.user_id
        ).first()

        if not user or not user.email:
            continue

        try:
            message = create_expiry_reminder_email(
                recipient_email=user.email,
                full_name=user.full_name,
                plan=subscription.plan,
                expiry_date=expiry_date,
            )

            send_email(message)

            subscription.expiry_reminder_sent_at = now
            db.commit()

            upcoming_sent += 1

        except Exception:
            db.rollback()
            failed += 1
            logger.exception(
                "Failed to send upcoming-expiry reminder for subscription %s",
                subscription.id,
            )

    # EXPIRED SUBSCRIPTION NOTIFICATIONS

    expired_subscriptions = db.query(Subscription).filter(
        Subscription.status == "expired",
        Subscription.expiry_date.isnot(None),
        Subscription.expired_reminder_sent_at.is_(None),
    ).all()

    for subscription in expired_subscriptions:
        expiry_date = get_utc_datetime(subscription.expiry_date)

        if expiry_date > now:
            continue

        user = db.query(User).filter(
            User.id == subscription.user_id
        ).first()

        if not user or not user.email:
            continue

        try:
            message = create_subscription_expired_email(
                recipient_email=user.email,
                full_name=user.full_name,
                plan=subscription.plan,
            )

            send_email(message)

            subscription.expired_reminder_sent_at = now
            db.commit()

            expired_sent += 1

        except Exception:
            db.rollback()
            failed += 1
            logger.exception(
                "Failed to send expired-subscription notification for subscription %s",
                subscription.id,
            )

    return {
        "upcoming_reminders_sent": upcoming_sent,
        "expired_notifications_sent": expired_sent,
        "failed_emails": failed,
    }


def get_subscription_amount(
    db: Session,
    customer_type: str,
    plan: str,
    service_tier: str | None = None,
) -> int:
    """Determine the correct subscription price."""

    if customer_type == "household":
        if service_tier is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Household subscriptions do not use "
                    "organisation service tiers."
                ),
            )

        return HOUSEHOLD_PRICES[plan]

    if customer_type == "organisation":
        if service_tier is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please select an organisation service tier.",
            )

        tier = db.query(OrganisationServiceTier).filter(
            OrganisationServiceTier.tier_name == service_tier.lower(),
            OrganisationServiceTier.is_active.is_(True),
        ).first()

        if not tier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The selected organisation service tier is unavailable.",
            )

        amount = (
            tier.weekly_price
            if plan == "weekly"
            else tier.monthly_price
        )

        if amount is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Pricing for the {service_tier.title()} "
                    f"{plan} plan has not been configured yet. "
                    "Please contact BinLock for a quotation."
                ),
            )

        return amount

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid customer type.",
    )


# CREATE SUBSCRIPTION

@router.post(
    "/",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_subscription(
    subscription_data: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    process_expired_subscriptions(db)

    # Organisations must be approved before subscribing.
    ensure_organisation_approved(db, current_user)

    existing_subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status.in_(["pending", "active"]),
    ).first()

    if existing_subscription:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a pending or active subscription.",
        )

    plan = subscription_data.plan
    service_tier = subscription_data.service_tier

    amount = get_subscription_amount(
        db=db,
        customer_type=current_user.customer_type,
        plan=plan,
        service_tier=service_tier,
    )

    new_subscription = Subscription(
        user_id=current_user.id,
        plan=plan,
        service_tier=service_tier,
        amount=amount,
        status="pending",
    )

    db.add(new_subscription)
    db.commit()
    db.refresh(new_subscription)

    return new_subscription


# CUSTOMER SUBSCRIPTIONS

@router.get(
    "/my-subscriptions",
    response_model=list[SubscriptionResponse],
)
def get_my_subscriptions(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    process_expired_subscriptions(db)

    return db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).order_by(
        Subscription.created_at.desc()
    ).all()


# ADMIN SUBSCRIPTION MANAGEMENT

@router.get(
    "/",
    response_model=list[SubscriptionResponse],
)
def get_all_subscriptions(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    process_expired_subscriptions(db)

    return db.query(Subscription).order_by(
        Subscription.created_at.desc()
    ).all()


@router.patch(
    "/{subscription_id}/status",
    response_model=SubscriptionResponse,
)
def update_subscription_status(
    subscription_id: int,
    status_data: SubscriptionStatusUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found.",
        )

    new_status = status_data.status

    if new_status == "active":
        # Admin activation must not bypass organisation approval.
        user = db.query(User).filter(
            User.id == subscription.user_id
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription customer not found.",
            )

        ensure_organisation_approved(db, user)

        if subscription.status != "active":
            now = datetime.now(timezone.utc)

            duration = (
                timedelta(days=7)
                if subscription.plan == "weekly"
                else timedelta(days=30)
            )

            subscription.start_date = now
            subscription.expiry_date = now + duration
            subscription.expiry_reminder_sent_at = None
            subscription.expired_reminder_sent_at = None

    elif new_status == "expired":
        subscription.expiry_date = datetime.now(timezone.utc)

    subscription.status = new_status

    db.commit()
    db.refresh(subscription)

    return subscription


# AUTOMATIC EXPIRY PROCESSING

@router.post("/process-expired")
def run_expiry_processing(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    expired_count = process_expired_subscriptions(db)

    return {
        "message": "Subscription expiry processing completed.",
        "expired_subscriptions": expired_count,
    }


# SUBSCRIPTION RENEWAL

@router.post(
    "/renew/{subscription_id}",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
def renew_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    process_expired_subscriptions(db)

    # Organisations must still be approved when renewing.
    ensure_organisation_approved(db, current_user)

    old_subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == current_user.id,
    ).first()

    if not old_subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found.",
        )

    if old_subscription.status not in ["active", "expired"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active or expired subscriptions can be renewed.",
        )

    pending_subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == "pending",
    ).first()

    if pending_subscription:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a pending subscription awaiting payment.",
        )

    amount = get_subscription_amount(
        db=db,
        customer_type=current_user.customer_type,
        plan=old_subscription.plan,
        service_tier=old_subscription.service_tier,
    )

    new_subscription = Subscription(
        user_id=current_user.id,
        plan=old_subscription.plan,
        service_tier=old_subscription.service_tier,
        amount=amount,
        status="pending",
    )

    db.add(new_subscription)
    db.commit()
    db.refresh(new_subscription)

    return new_subscription
