from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Bin
from app.schemas import BinCreate, BinUpdate, BinResponse
from app.dependencies import get_current_user, require_admin


router = APIRouter(
    prefix="/bins",
    tags=["Bin Management"]
)


@router.post(
    "/",
    response_model=BinResponse,
    status_code=status.HTTP_201_CREATED
)
def create_bin(
    bin_data: BinCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    existing_bin = db.query(Bin).filter(
        Bin.bin_code == bin_data.bin_code
    ).first()

    if existing_bin:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A bin with this code already exists."
        )

    new_bin = Bin(
        bin_code=bin_data.bin_code,
        location=bin_data.location
    )

    db.add(new_bin)
    db.commit()
    db.refresh(new_bin)

    return new_bin


@router.get("/", response_model=list[BinResponse])
def get_bins(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return db.query(Bin).all()


@router.get("/{bin_id}", response_model=BinResponse)
def get_bin(
    bin_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    bin_record = db.query(Bin).filter(
        Bin.id == bin_id
    ).first()

    if not bin_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bin not found."
        )

    return bin_record


@router.patch("/{bin_id}", response_model=BinResponse)
def update_bin(
    bin_id: int,
    bin_data: BinUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    bin_record = db.query(Bin).filter(
        Bin.id == bin_id
    ).first()

    if not bin_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bin not found."
        )

    update_data = bin_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(bin_record, key, value)

    db.commit()
    db.refresh(bin_record)

    return bin_record


@router.delete(
    "/{bin_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_bin(
    bin_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    bin_record = db.query(Bin).filter(
        Bin.id == bin_id
    ).first()

    if not bin_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bin not found."
        )

    db.delete(bin_record)
    db.commit()

    return None
