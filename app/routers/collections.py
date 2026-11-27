from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models import (
    CollectionTeam,
    CollectionSchedule,
    CollectionRecord,
    Bin,
    BinAssignment,
    Subscription,
    User,
)
from app.schemas import (
    CollectionTeamCreate,
    CollectionTeamResponse,
    CollectionScheduleCreate,
    CollectionScheduleResponse,
    CollectionScheduleStatusUpdate,
    CollectionRecordCreate,
    CollectionRecordResponse,
)

router = APIRouter(prefix="/collections", tags=["Collections"])


def to_utc(value: datetime) -> datetime:
    
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def ensure_active_subscription(db: Session, user_id: int) -> None:

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
        detail="The customer must have a valid active subscription before a collection can be scheduled.",
    )


@router.post(
    "/teams",
    response_model=CollectionTeamResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_team(
    data: CollectionTeamCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    team = CollectionTeam(**data.model_dump())

    db.add(team)
    db.commit()
    db.refresh(team)

    return team


@router.get("/teams", response_model=list[CollectionTeamResponse])
def list_teams(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    return (
        db.query(CollectionTeam)
        .order_by(CollectionTeam.id.desc())
        .all()
    )


@router.post(
    "/schedules",
    response_model=CollectionScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_schedule(
    data: CollectionScheduleCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    user = db.query(User).filter(User.id == data.user_id).first()
    bin_item = db.query(Bin).filter(Bin.id == data.bin_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if not bin_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bin not found.",
        )

    if not bin_item.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This bin is inactive and cannot be scheduled for collection.",
        )

    ensure_active_subscription(db, user.id)

    assignment = (
        db.query(BinAssignment)
        .filter(
            BinAssignment.user_id == data.user_id,
            BinAssignment.bin_id == data.bin_id,
            BinAssignment.status == "active",
        )
        .first()
    )

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This bin is not actively assigned to the selected customer.",
        )

    # If a team was selected, it must exist and be active.
    if data.team_id is not None:
        team = (
            db.query(CollectionTeam)
            .filter(
                CollectionTeam.id == data.team_id,
                CollectionTeam.is_active.is_(True),
            )
            .first()
        )

        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active collection team not found.",
            )

    scheduled_for = to_utc(data.scheduled_for)

    if scheduled_for <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collection date must be in the future.",
        )

    schedule_data = data.model_dump()
    schedule_data["scheduled_for"] = scheduled_for

    schedule = CollectionSchedule(**schedule_data)

    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    return schedule


@router.get(
    "/my-schedules",
    response_model=list[CollectionScheduleResponse],
)
def my_schedules(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return (
        db.query(CollectionSchedule)
        .filter(CollectionSchedule.user_id == current_user.id)
        .order_by(CollectionSchedule.scheduled_for.desc())
        .all()
    )


@router.get(
    "/schedules",
    response_model=list[CollectionScheduleResponse],
)
def all_schedules(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    return (
        db.query(CollectionSchedule)
        .order_by(CollectionSchedule.scheduled_for.desc())
        .all()
    )


@router.patch(
    "/schedules/{schedule_id}",
    response_model=CollectionScheduleResponse,
)
def update_schedule(
    schedule_id: int,
    data: CollectionScheduleStatusUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    schedule = (
        db.query(CollectionSchedule)
        .filter(CollectionSchedule.id == schedule_id)
        .first()
    )

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found.",
        )

    schedule.status = data.status

    db.commit()
    db.refresh(schedule)

    return schedule


@router.post(
    "/schedules/{schedule_id}/record",
    response_model=CollectionRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_collection(
    schedule_id: int,
    data: CollectionRecordCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    schedule = (
        db.query(CollectionSchedule)
        .filter(CollectionSchedule.id == schedule_id)
        .first()
    )

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found.",
        )

    existing = (
        db.query(CollectionRecord)
        .filter(CollectionRecord.schedule_id == schedule_id)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A collection record already exists for this schedule.",
        )

    now = datetime.now(timezone.utc)

    record = CollectionRecord(
        schedule_id=schedule_id,
        status=data.status,
        waste_collected_kg=data.waste_collected_kg,
        notes=data.notes,
        completed_at=now if data.status == "completed" else None,
    )

    schedule.status = data.status

    db.add(record)
    db.commit()
    db.refresh(record)

    return record


@router.get(
    "/schedules/{schedule_id}/record",
    response_model=CollectionRecordResponse,
)
def get_collection_record(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    schedule = (
        db.query(CollectionSchedule)
        .filter(CollectionSchedule.id == schedule_id)
        .first()
    )

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found.",
        )

    if (
        schedule.user_id != current_user.id
        and current_user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )

    record = (
        db.query(CollectionRecord)
        .filter(CollectionRecord.schedule_id == schedule_id)
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection record not found.",
        )

    return record
