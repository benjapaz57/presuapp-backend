import os
import mercadopago
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/subscriptions", tags=["Suscripciones"])

MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://presuapp-frontend.vercel.app")
PRO_AMOUNT = float(os.getenv("PRO_AMOUNT", "2000"))
MP_WEBHOOK_SECRET = os.getenv("MP_WEBHOOK_SECRET", "")


def get_sdk():
    return mercadopago.SDK(MP_ACCESS_TOKEN)


@router.post("/checkout")
def create_checkout(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.plan == "pro":
        raise HTTPException(status_code=400, detail="Ya tenés el plan Pro activo.")

    sdk = get_sdk()

    preapproval_data = {
        "reason": "Preformal Pro — Plan mensual",
        "payer_email": current_user.email,
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "transaction_amount": PRO_AMOUNT,
            "currency_id": "ARS",
        },
        "back_url": f"{FRONTEND_URL}/dashboard?subscribed=true",
        "external_reference": str(current_user.id),
        "status": "pending",
    }

    try:
        result = sdk.preapproval().create(preapproval_data)
    except Exception as e:
        print(f"[MP] Excepción al crear preapproval: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    print(f"[MP] status={result['status']} response={result.get('response')}")

    if result["status"] not in (200, 201):
        raise HTTPException(status_code=500, detail=f"MP error {result['status']}: {result.get('response')}")

    data = result["response"]

    # Guardar el ID de la suscripción en el usuario
    current_user.mp_subscription_id = data["id"]
    db.commit()

    return {"init_point": data["init_point"]}


@router.post("/webhook")
async def mp_webhook(request: Request, db: Session = Depends(get_db)):
    """MercadoPago notifica aquí cuando cambia el estado de una suscripción."""
    body = await request.json()

    # MP envía distintos tipos de notificación
    topic = body.get("type") or request.query_params.get("topic", "")

    if topic not in ("subscription_preapproval", "preapproval"):
        return {"status": "ignored"}

    preapproval_id = (body.get("data") or {}).get("id") or request.query_params.get("id")
    if not preapproval_id:
        return {"status": "no_id"}

    sdk = get_sdk()
    result = sdk.preapproval().get(preapproval_id)
    if result["status"] != 200:
        return {"status": "mp_error"}

    preapproval = result["response"]
    user_id = preapproval.get("external_reference")
    mp_status = preapproval.get("status")

    if not user_id:
        return {"status": "no_reference"}

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        return {"status": "user_not_found"}

    if mp_status == "authorized":
        user.plan = "pro"
        user.mp_subscription_id = preapproval_id
    elif mp_status in ("cancelled", "paused"):
        user.plan = "free"
        user.mp_subscription_id = None

    db.commit()
    return {"status": "ok"}


@router.delete("/cancel")
def cancel_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.plan != "pro" or not current_user.mp_subscription_id:
        raise HTTPException(status_code=400, detail="No tenés una suscripción activa.")

    sdk = get_sdk()
    result = sdk.preapproval().update(
        current_user.mp_subscription_id,
        {"status": "cancelled"}
    )

    if result["status"] != 200:
        raise HTTPException(status_code=500, detail="Error al cancelar la suscripción.")

    current_user.plan = "free"
    current_user.mp_subscription_id = None
    db.commit()
    return {"message": "Suscripción cancelada."}
