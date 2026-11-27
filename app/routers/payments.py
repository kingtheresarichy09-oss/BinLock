import os
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models import Payment, Subscription, User
from app.schemas import (
    PaymentCreate,
    PaymentResponse,
    PaymentInitializationResponse,
    PaymentVerificationResponse,
)

router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
)

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_BASE_URL = "https://api.paystack.co"


def get_paystack_headers():
    if not PAYSTACK_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment service is not configured yet.",
        )

    return {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }


@router.post(
    "/initialize",
    response_model=PaymentInitializationResponse,
)
def initialize_payment(
    payment_data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    headers = get_paystack_headers()

    subscription = db.query(Subscription).filter(
        Subscription.id == payment_data.subscription_id,
        Subscription.user_id == current_user.id,
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=404,
            detail="Subscription not found.",
        )

    if subscription.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Only pending subscriptions can be paid for.",
        )

    existing_payment = db.query(Payment).filter(
        Payment.subscription_id == subscription.id,
        Payment.status == "successful",
    ).first()

    if existing_payment:
        raise HTTPException(
            status_code=400,
            detail="This subscription has already been paid for.",
        )

    reference = f"BINLOCK-{secrets.token_hex(12)}"

    payment = Payment(
        user_id=current_user.id,
        subscription_id=subscription.id,
        amount=subscription.amount,
        reference=reference,
        provider="paystack",
        status="pending",
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    payload = {
        "email": current_user.email,
        "amount": subscription.amount * 100,
        "reference": reference,
        "currency": "NGN",
        "metadata": {
            "user_id": current_user.id,
            "subscription_id": subscription.id,
        },
    }

    callback_url = os.getenv("PAYSTACK_CALLBACK_URL")

    if callback_url:
        payload["callback_url"] = callback_url

    try:
        response = httpx.post(
            f"{PAYSTACK_BASE_URL}/transaction/initialize",
            json=payload,
            headers=headers,
            timeout=20.0,
        )
        response.raise_for_status()
        result = response.json()

    except httpx.HTTPError:
        payment.status = "failed"
        db.commit()

        raise HTTPException(
            status_code=502,
            detail="Could not initialize payment with the provider.",
        )

    if not result.get("status"):
        payment.status = "failed"
        db.commit()

        raise HTTPException(
            status_code=502,
            detail="Payment provider could not initialize the transaction.",
        )

    provider_data = result.get("data", {})

    return {
        "payment_id": payment.id,
        "reference": reference,
        "authorization_url": provider_data.get("authorization_url"),
        "access_code": provider_data.get("access_code"),
        "amount": payment.amount,
        "currency": "NGN",
        "status": payment.status,
    }


@router.get(
    "/verify/{reference}",
    response_model=PaymentVerificationResponse,
)
def verify_payment(
    reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payment = db.query(Payment).filter(
        Payment.reference == reference,
        Payment.user_id == current_user.id,
    ).first()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment record not found.",
        )

    if payment.status == "successful":
        return {
            "reference": payment.reference,
            "status": "successful",
            "amount": payment.amount,
            "message": "Payment has already been verified.",
        }

    if payment.status == "failed":
        raise HTTPException(
            status_code=400,
            detail="This payment has already been marked as failed.",
        )

    headers = get_paystack_headers()

    try:
        response = httpx.get(
            f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",
            headers=headers,
            timeout=20.0,
        )
        response.raise_for_status()
        result = response.json()

    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail="Could not verify payment with the provider.",
        )

    if not result.get("status"):
        raise HTTPException(
            status_code=400,
            detail="Payment provider could not verify this transaction.",
        )

    transaction = result.get("data", {})

    if transaction.get("reference") != payment.reference:
        raise HTTPException(
            status_code=400,
            detail="Payment reference does not match.",
        )

    if transaction.get("status") != "success":
        payment.status = "failed"
        db.commit()

        return {
            "reference": payment.reference,
            "status": "failed",
            "amount": payment.amount,
            "message": "The payment was not successful.",
        }

    expected_amount = payment.amount * 100

    if transaction.get("amount") != expected_amount:
        raise HTTPException(
            status_code=400,
            detail="Verified payment amount does not match.",
        )

    if transaction.get("currency") != "NGN":
        raise HTTPException(
            status_code=400,
            detail="Unexpected payment currency.",
    )

    customer_email = transaction.get("customer", {}).get("email", "")

    if customer_email.lower() != current_user.email.lower():
        raise HTTPException(
            status_code=400,
            detail="Payment customer email does not match.",
        )

    subscription = db.query(Subscription).filter(
        Subscription.id == payment.subscription_id,
        Subscription.user_id == current_user.id,
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=404,
            detail="Related subscription was not found.",
        )

    if subscription.status != "pending":
        raise HTTPException(
            status_code=409,
            detail="Subscription is no longer pending.",
        )

    now = datetime.now(timezone.utc)

    if subscription.plan == "weekly":
        duration = timedelta(days=7)
    elif subscription.plan == "monthly":
        duration = timedelta(days=30)
    else:
        raise HTTPException(
            status_code=400,
            detail="Unknown subscription plan.",
        )

    payment.status = "successful"
    payment.paid_at = now


    previous_subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.id != subscription.id,
        Subscription.plan == subscription.plan,
        Subscription.service_tier == subscription.service_tier,
        Subscription.status == "active",
        Subscription.expiry_date > now,
    ).order_by(
        Subscription.expiry_date.desc()
    ).first()

    renewal_start = (
        previous_subscription.expiry_date
        if previous_subscription
        else now
    )

    subscription.status = "active"
    subscription.start_date = renewal_start
    subscription.expiry_date = renewal_start + duration


    db.commit()

    return {
        "reference": payment.reference,
        "status": "successful",
        "amount": payment.amount,
        "message": "Payment verified and subscription activated.",
    }


@router.get(
    "/my-payments",
    response_model=list[PaymentResponse],
)
def get_my_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Payment)
        .filter(Payment.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .all()
    )


@router.get(
    "/",
    response_model=list[PaymentResponse],
)
def get_all_payments(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return (
        db.query(Payment)
        .order_by(Payment.created_at.desc())
        .all()
    )
