import base64
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.budget import Budget, BudgetItem
from app.models.client import Client
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse
from app.services.auth import get_current_user
from app.services.pdf_generator import generate_budget_pdf
from app.services.email import send_budget_to_client

router = APIRouter(prefix="/budgets", tags=["Presupuestos"])


def _calculate_totals(items_data, discount_percent, tax_percent):
    subtotal = sum(item.quantity * item.unit_price for item in items_data)
    discount_amount = subtotal * (discount_percent / 100)
    net = subtotal - discount_amount          # base imponible
    tax_amount = net * (tax_percent / 100)
    total = net + tax_amount
    return subtotal, discount_amount, tax_amount, total


@router.get("/", response_model=List[BudgetResponse])
def list_budgets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Budget).filter(Budget.user_id == current_user.id).order_by(Budget.created_at.desc()).all()


PLAN_LIMITS = {
    "free": 3,
    "pro": None,  # sin límite
}

@router.post("/", response_model=BudgetResponse, status_code=201)
def create_budget(data: BudgetCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Validar límite de plan
    limit = PLAN_LIMITS.get(current_user.plan, 3)
    if limit is not None:
        count = db.query(Budget).filter(Budget.user_id == current_user.id).count()
        if count >= limit:
            raise HTTPException(
                status_code=403,
                detail=f"PLAN_LIMIT_REACHED|Tu plan gratuito permite hasta {limit} presupuestos. Actualizá a Pro para continuar."
            )

    # Número de presupuesto autoincremental por usuario
    last = db.query(Budget).filter(Budget.user_id == current_user.id).order_by(Budget.number.desc()).first()
    number = (last.number + 1) if last else 1

    subtotal, discount_amount, tax_amount, total = _calculate_totals(
        data.items, data.discount_percent, data.tax_percent
    )

    budget = Budget(
        user_id=current_user.id,
        client_id=data.client_id,
        number=number,
        title=data.title,
        description=data.description,
        discount_percent=data.discount_percent,
        discount_amount=discount_amount,
        tax_percent=data.tax_percent,
        tax_amount=tax_amount,
        subtotal=subtotal,
        total=total,
        notes=data.notes,
        valid_until=data.valid_until,
    )
    db.add(budget)
    db.flush()  # para obtener budget.id antes del commit

    for item_data in data.items:
        budget_item = BudgetItem(
            budget_id=budget.id,
            item_id=item_data.item_id,
            description=item_data.description,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            subtotal=item_data.quantity * item_data.unit_price,
        )
        db.add(budget_item)

    db.commit()
    db.refresh(budget)
    return budget


@router.get("/{budget_id}", response_model=BudgetResponse)
def get_budget(budget_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    budget = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == current_user.id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return budget


@router.put("/{budget_id}", response_model=BudgetResponse)
def update_budget(budget_id: int, data: BudgetUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    budget = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == current_user.id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(budget, field, value)
    db.commit()
    db.refresh(budget)
    return budget


@router.delete("/{budget_id}", status_code=204)
def delete_budget(budget_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    budget = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == current_user.id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    db.delete(budget)
    db.commit()


@router.get("/{budget_id}/pdf")
def download_budget_pdf(budget_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    budget = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == current_user.id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    client = db.query(Client).filter(Client.id == budget.client_id).first() if budget.client_id else None

    pdf_bytes = generate_budget_pdf(budget, current_user, client)

    filename = f"presupuesto-{budget.number:04d}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post("/{budget_id}/send-email", status_code=200)
def send_budget_email(budget_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    budget = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == current_user.id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    client = db.query(Client).filter(Client.id == budget.client_id).first() if budget.client_id else None

    if not client or not client.email:
        raise HTTPException(status_code=400, detail="El cliente no tiene email registrado.")

    pdf_bytes = generate_budget_pdf(budget, current_user, client)
    filename = f"presupuesto-{budget.number:04d}.pdf"
    pdf_b64 = base64.b64encode(pdf_bytes).decode()

    ok = send_budget_to_client(
        to_email=client.email,
        client_name=client.name,
        sender_name=current_user.business_name or current_user.name,
        budget_number=budget.number,
        total=budget.total,
        pdf_b64=pdf_b64,
        filename=filename,
    )

    if not ok:
        raise HTTPException(status_code=500, detail="Error al enviar el email.")

    return {"message": f"Presupuesto enviado a {client.email}"}
