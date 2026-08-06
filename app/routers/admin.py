import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.user import User
from app.models.budget import Budget
from app.services.auth import get_current_user

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(current_user: User = Depends(get_current_user)):
    if not ADMIN_EMAIL or current_user.email != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    return current_user


class PlanUpdate(BaseModel):
    plan: str


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), _=Depends(require_admin)):
    total_users = db.query(func.count(User.id)).scalar() or 0
    pro_users = db.query(func.count(User.id)).filter(User.plan == "pro").scalar() or 0
    total_budgets = db.query(func.count(Budget.id)).scalar() or 0
    return {
        "total_users": total_users,
        "pro_users": pro_users,
        "free_users": total_users - pro_users,
        "total_budgets": total_budgets,
    }


@router.get("/users")
def list_users(db: Session = Depends(get_db), _=Depends(require_admin)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    result = []
    for u in users:
        budget_count = db.query(func.count(Budget.id)).filter(Budget.user_id == u.id).scalar() or 0
        result.append({
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "plan": u.plan,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "budget_count": budget_count,
        })
    return result


@router.put("/users/{user_id}/plan")
def update_user_plan(user_id: int, data: PlanUpdate, db: Session = Depends(get_db), _=Depends(require_admin)):
    if data.plan not in ("free", "pro"):
        raise HTTPException(status_code=400, detail="Plan inválido. Usá 'free' o 'pro'.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    user.plan = data.plan
    db.commit()
    return {"message": f"Plan actualizado a {data.plan}.", "user_id": user_id, "plan": data.plan}


@router.get("/budgets")
def list_all_budgets(db: Session = Depends(get_db), _=Depends(require_admin)):
    rows = (
        db.query(Budget, User)
        .join(User, Budget.user_id == User.id)
        .order_by(Budget.created_at.desc())
        .all()
    )
    return [
        {
            "id": b.id,
            "number": b.number,
            "title": b.title,
            "total": b.total,
            "status": b.status,
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "user_id": u.id,
            "user_email": u.email,
            "user_name": u.name,
        }
        for b, u in rows
    ]


@router.delete("/budgets/{budget_id}", status_code=204)
def delete_any_budget(budget_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado.")
    db.delete(budget)
    db.commit()


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    if user.email == current_user.email:
        raise HTTPException(status_code=400, detail="No podés eliminar tu propio usuario.")
    db.delete(user)
    db.commit()
