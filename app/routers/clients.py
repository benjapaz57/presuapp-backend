from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.client import Client
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse
from app.services.auth import get_current_user

router = APIRouter(prefix="/clients", tags=["Clientes"])


@router.get("/", response_model=List[ClientResponse])
def list_clients(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Client).filter(Client.user_id == current_user.id).all()


@router.post("/", response_model=ClientResponse, status_code=201)
def create_client(data: ClientCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    client = Client(**data.model_dump(), user_id=current_user.id)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(client_id: int, data: ClientUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=204)
def delete_client(client_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    db.delete(client)
    db.commit()
