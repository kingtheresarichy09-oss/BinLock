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
)

router = APIRouter(prefix="/admin/analytics", tags=["Admin Analytics"])


@router.get("/summary")
def analytics_summary(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    def count(query):
        return query.scalar() or 0

    return {
        "customers": {
            "total": count(db.query(func.count(User.id))),
            "households": count(
                db.query(func.count(User.id)).filter(
                    User.customer_type == "household"
                )
            ),
            "organisations": count(
                db.query(func.count(User.id)).filter(
                    User.customer_type == "organisation"
                )
            ),
        },
        "subscriptions": {
            "total": count(db.query(func.count(Subscription.id))),
            "pending": count(
                db.query(func.count(Subscription.id)).filter(
                    Subscription.status == "pending"
                )
            ),
            "active": count(
                db.query(func.count(Subscription.id)).filter(
                    Subscription.status == "active"
                )
            ),
            "expired": count(
                db.query(func.count(Subscription.id)).filter(
                    Subscription.status == "expired"
                )
            ),
        },
        "payments": {
            "total": count(db.query(func.count(Payment.id))),
            "successful": count(
                db.query(func.count(Payment.id)).filter(
                    Payment.status == "successful"
                )
            ),
            "pending": count(
                db.query(func.count(Payment.id)).filter(
                    Payment.status == "pending"
                )
            ),
            "failed": count(
                db.query(func.count(Payment.id)).filter(
                    Payment.status == "failed"
                )
            ),
            "successful_amount_naira": (
                db.query(func.coalesce(func.sum(Payment.amount), 0))
                .filter(Payment.status == "successful")
                .scalar()
            ),
        },
        "pickups": {
            "regular_requests": count(db.query(func.count(PickupRequest.id))),
            "extra_requests": count(db.query(func.count(ExtraPickup.id))),
            "scheduled_collections": count(
                db.query(func.count(CollectionSchedule.id))
            ),
            "collection_records": count(
                db.query(func.count(CollectionRecord.id))
            ),
        },
        "complaints": {
            "total": count(db.query(func.count(Complaint.id))),
            "open": count(
                db.query(func.count(Complaint.id)).filter(
                    Complaint.status == "open"
                )
            ),
        },
        "deliveries": {
            "total": count(db.query(func.count(Delivery.id))),
            "pending": count(
                db.query(func.count(Delivery.id)).filter(
                    Delivery.status == "pending"
                )
            ),
            "delivered": count(
                db.query(func.count(Delivery.id)).filter(
                    Delivery.status == "delivered"
                )
            ),
        },
    }
