from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse
from app.services.auth import get_current_user

router = APIRouter(prefix="/items", tags=["Banco de servicios"])


@router.get("/", response_model=List[ItemResponse])
def list_items(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Item).filter(Item.user_id == current_user.id).all()


@router.post("/", response_model=ItemResponse, status_code=201)
def create_item(data: ItemCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = Item(**data.model_dump(), user_id=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(Item).filter(Item.id == item_id, Item.user_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return item


@router.put("/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, data: ItemUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(Item).filter(Item.id == item_id, Item.user_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = db.query(Item).filter(Item.id == item_id, Item.user_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    db.delete(item)
    db.commit()
