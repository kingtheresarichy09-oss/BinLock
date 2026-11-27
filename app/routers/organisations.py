from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models import Organisation, OrganisationServiceTier
from app.schemas import (
    OrganisationResponse,
    OrganisationStatusUpdate,
    OrganisationServiceTierCreate,
    OrganisationServiceTierUpdate,
    OrganisationServiceTierResponse,
)

router = APIRouter(
    prefix="/organisations",
    tags=["Organisations"],
)

@router.get(
    "/my-organisation",
    response_model=OrganisationResponse,
)
def get_my_organisation(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    organisation = db.query(Organisation).filter(
        Organisation.owner_user_id == current_user.id
    ).first()

    if not organisation:
        raise HTTPException(
            status_code=404,
            detail="No organisation profile found.",
        )

    return organisation


@router.get(
    "/",
    response_model=list[OrganisationResponse],
)
def get_all_organisations(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    return db.query(Organisation).order_by(
        Organisation.created_at.desc()
    ).all()


@router.patch(
    "/{organisation_id}/status",
    response_model=OrganisationResponse,
)
def update_organisation_status(
    organisation_id: int,
    status_data: OrganisationStatusUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    organisation = db.query(Organisation).filter(
        Organisation.id == organisation_id
    ).first()

    if not organisation:
        raise HTTPException(
            status_code=404,
            detail="Organisation not found.",
        )

    organisation.status = status_data.status

    db.commit()
    db.refresh(organisation)

    return organisation


# ORGANISATION SERVICE TIERS

@router.post(
    "/tiers",
    response_model=OrganisationServiceTierResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_organisation_tier(
    tier_data: OrganisationServiceTierCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    tier_name = tier_data.tier_name.lower()

    existing_tier = db.query(OrganisationServiceTier).filter(
        OrganisationServiceTier.tier_name == tier_name
    ).first()

    if existing_tier:
        raise HTTPException(
            status_code=409,
            detail="This organisation service tier already exists.",
        )

    tier = OrganisationServiceTier(
        tier_name=tier_name,
        weekly_price=tier_data.weekly_price,
        monthly_price=tier_data.monthly_price,
        max_monthly_waste_kg=tier_data.max_monthly_waste_kg,
        features=tier_data.features,
        is_active=tier_data.is_active,
    )

    db.add(tier)
    db.commit()
    db.refresh(tier)

    return tier


@router.get(
    "/tiers",
    response_model=list[OrganisationServiceTierResponse],
)
def get_available_organisation_tiers(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return db.query(OrganisationServiceTier).filter(
        OrganisationServiceTier.is_active.is_(True)
    ).order_by(
        OrganisationServiceTier.id.asc()
    ).all()


@router.get(
    "/tiers/admin/all",
    response_model=list[OrganisationServiceTierResponse],
)
def get_all_organisation_tiers(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    return db.query(OrganisationServiceTier).order_by(
        OrganisationServiceTier.id.asc()
    ).all()


@router.patch(
    "/tiers/{tier_id}",
    response_model=OrganisationServiceTierResponse,
)
def update_organisation_tier(
    tier_id: int,
    tier_data: OrganisationServiceTierUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    tier = db.query(OrganisationServiceTier).filter(
        OrganisationServiceTier.id == tier_id
    ).first()

    if not tier:
        raise HTTPException(
            status_code=404,
            detail="Organisation service tier not found.",
        )

    update_data = tier_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(tier, field, value)

    db.commit()
    db.refresh(tier)

    return tier


@router.post(
    "/tiers/initialize-defaults",
    response_model=OrganisationServiceTierResponse,
)
def initialize_default_organisation_tier(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):

    basic_tier = db.query(OrganisationServiceTier).filter(
        OrganisationServiceTier.tier_name == "basic"
    ).first()

    if basic_tier:
        return basic_tier

    basic_tier = OrganisationServiceTier(
        tier_name="basic",
        weekly_price=3000,
        monthly_price=10000,
        max_monthly_waste_kg=None,
        features=[],
        is_active=True,
    )

    db.add(basic_tier)
    db.commit()
    db.refresh(basic_tier)

    return basic_tier
