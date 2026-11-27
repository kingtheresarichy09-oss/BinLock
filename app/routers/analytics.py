from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.dependencies import require_admin
from app.models import (
    User,
    Subscription,
    Payment,
    PickupRequest,
    CollectionSchedule,
    Complaint,
    Delivery,
    ExtraPickup,
    CollectionRecord,
    Organisation,
)

router = APIRouter(
    prefix="/admin/analytics",
    tags=["Admin Analytics"],
)


def count_records(db: Session, model, *filters) -> int:
    query = db.query(func.count(model.id))

    if filters:
        query = query.filter(*filters)

    return query.scalar() or 0


def sum_payments(db: Session, payment_status: str) -> float:
    amount = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.status == payment_status)
        .scalar()
    )

    return float(amount or 0)


@router.get("/summary")
def analytics_summary(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    # Customer figures
    total_customers = count_records(db, User)

    household_customers = count_records(
        db,
        User,
        User.customer_type == "household",
    )

    organisation_customers = count_records(
        db,
        User,
        User.customer_type == "organisation",
    )

    # Organisation approval figures
    total_organisations = count_records(db, Organisation)

    pending_organisations = count_records(
        db,
        Organisation,
        Organisation.status == "pending",
    )

    approved_organisations = count_records(
        db,
        Organisation,
        Organisation.status == "approved",
    )

    rejected_organisations = count_records(
        db,
        Organisation,
        Organisation.status == "rejected",
    )

    # Subscription figures
    total_subscriptions = count_records(db, Subscription)

    pending_subscriptions = count_records(
        db,
        Subscription,
        Subscription.status == "pending",
    )

    active_subscriptions = count_records(
        db,
        Subscription,
        Subscription.status == "active",
    )

    expired_subscriptions = count_records(
        db,
        Subscription,
        Subscription.status == "expired",
    )

    # Payment figures
    total_payments = count_records(db, Payment)

    successful_payments = count_records(
        db,
        Payment,
        Payment.status == "successful",
    )

    pending_payments = count_records(
        db,
        Payment,
        Payment.status == "pending",
    )

    failed_payments = count_records(
        db,
        Payment,
        Payment.status == "failed",
    )

    # Revenue includes successful payments only.
    successful_amount = sum_payments(db, "successful")

    # Pending payments are treated as outstanding, not as revenue.
    outstanding_amount = sum_payments(db, "pending")

    # Pickup and collection figures
    regular_pickup_requests = count_records(db, PickupRequest)
    extra_pickup_requests = count_records(db, ExtraPickup)
    scheduled_collections = count_records(db, CollectionSchedule)
    collection_records = count_records(db, CollectionRecord)

    # Complaint figures
    total_complaints = count_records(db, Complaint)

    open_complaints = count_records(
        db,
        Complaint,
        Complaint.status == "open",
    )

    # Delivery figures
    total_deliveries = count_records(db, Delivery)

    pending_deliveries = count_records(
        db,
        Delivery,
        Delivery.status == "pending",
    )

    delivered_deliveries = count_records(
        db,
        Delivery,
        Delivery.status == "delivered",
    )

    return {
        "customers": {
            "total": total_customers,
            "households": household_customers,
            "organisations": organisation_customers,
        },
        "organisations": {
            "total": total_organisations,
            "pending_approval": pending_organisations,
            "approved": approved_organisations,
            "rejected": rejected_organisations,
        },
        "subscriptions": {
            "total": total_subscriptions,
            "pending": pending_subscriptions,
            "active": active_subscriptions,
            "expired": expired_subscriptions,
        },
        "payments": {
            "total": total_payments,
            "successful": successful_payments,
            "pending": pending_payments,
            "failed": failed_payments,
            "successful_amount_naira": successful_amount,
            "outstanding_count": pending_payments,
            "outstanding_amount_naira": outstanding_amount,
        },
        "pickups": {
            "regular_requests": regular_pickup_requests,
            "extra_requests": extra_pickup_requests,
            "scheduled_collections": scheduled_collections,
            "collection_records": collection_records,
        },
        "complaints": {
            "total": total_complaints,
            "open": open_complaints,
        },
        "deliveries": {
            "total": total_deliveries,
            "pending": pending_deliveries,
            "delivered": delivered_deliveries,
        },
    }
