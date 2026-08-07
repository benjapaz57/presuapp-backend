import os
import resend

resend.api_key = os.getenv("RESEND_API_KEY", "")

FROM_EMAIL = os.getenv("FROM_EMAIL", "onboarding@resend.dev")
APP_NAME = "Preformal"


def send_password_reset(to_email: str, reset_url: str) -> bool:
    try:
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": f"{APP_NAME} — Recuperá tu contraseña",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
                <h2 style="color: #4f46e5;">{APP_NAME}</h2>
                <p>Recibimos una solicitud para restablecer tu contraseña.</p>
                <p>Hacé clic en el botón para crear una nueva contraseña. El link expira en <strong>1 hora</strong>.</p>
                <a href="{reset_url}"
                   style="display:inline-block; background:#4f46e5; color:#fff; padding:12px 24px;
                          border-radius:6px; text-decoration:none; font-weight:bold; margin:16px 0;">
                    Restablecer contraseña
                </a>
                <p style="color:#6b7280; font-size:13px;">
                    Si no solicitaste esto, ignorá este email. Tu contraseña no cambia.
                </p>
                <hr style="border:none; border-top:1px solid #e5e7eb; margin:24px 0;">
                <p style="color:#9ca3af; font-size:12px;">{APP_NAME} · generador de presupuestos</p>
            </div>
            """,
        })
        return True
    except Exception as e:
        print(f"[EMAIL] Error enviando reset: {e}")
        return False


def send_budget_to_client(
    to_email: str,
    client_name: str,
    sender_name: str,
    budget_number: int,
    total: float,
    pdf_b64: str,
    filename: str,
) -> bool:
    try:
        total_fmt = f"${total:,.0f}".replace(",", ".")
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": f"Presupuesto #{budget_number:04d} de {sender_name}",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 32px;">
                <h2 style="color: #4f46e5;">{sender_name}</h2>
                <p>Hola <strong>{client_name}</strong>,</p>
                <p>Te compartimos el presupuesto <strong>#{budget_number:04d}</strong> por un total de <strong>{total_fmt}</strong>.</p>
                <p>Encontrás el detalle completo en el PDF adjunto.</p>
                <p style="color:#6b7280; font-size:13px;">Ante cualquier consulta, respondé este email.</p>
                <hr style="border:none; border-top:1px solid #e5e7eb; margin:24px 0;">
                <p style="color:#9ca3af; font-size:12px;">Enviado desde {APP_NAME}</p>
            </div>
            """,
            "attachments": [{
                "filename": filename,
                "content": pdf_b64,
            }],
        })
        return True
    except Exception as e:
        print(f"[EMAIL] Error enviando presupuesto: {e}")
        return False


def send_welcome(to_email: str, name: str) -> bool:
    try:
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": f"¡Bienvenido/a a {APP_NAME}!",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
                <h2 style="color: #4f46e5;">{APP_NAME}</h2>
                <p>Hola <strong>{name}</strong>, ¡gracias por registrarte!</p>
                <p>Ya podés empezar a crear presupuestos profesionales en minutos.</p>
                <p style="color:#6b7280; font-size:13px;">
                    Si tenés alguna pregunta, respondé este email y te ayudamos.
                </p>
                <hr style="border:none; border-top:1px solid #e5e7eb; margin:24px 0;">
                <p style="color:#9ca3af; font-size:12px;">{APP_NAME} · generador de presupuestos</p>
            </div>
            """,
        })
        return True
    except Exception as e:
        print(f"[EMAIL] Error enviando bienvenida: {e}")
        return False
