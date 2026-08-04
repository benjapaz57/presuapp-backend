import os
import io
import uuid
from datetime import timedelta
import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from PIL import Image
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, LoginRequest, Token, UserUpdate
from app.services.auth import hash_password, verify_password, create_access_token, get_current_user, SECRET_KEY, ALGORITHM
from app.services.email import send_password_reset, send_welcome

router = APIRouter(prefix="/auth", tags=["Autenticación"])

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
LOGO_SIZE = (200, 200)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:4200")


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

# Configurar Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)


def _process_logo(content: bytes) -> bytes:
    """Resize a máximo 200x200 manteniendo proporción."""
    img = Image.open(io.BytesIO(content))
    img.thumbnail(LOGO_SIZE, Image.LANCZOS)
    buf_out = io.BytesIO()
    fmt = img.format or "PNG"
    if fmt not in ("PNG", "JPEG", "WEBP"):
        fmt = "PNG"
    img.save(buf_out, format=fmt, optimize=True)
    return buf_out.getvalue()


@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        business_name=data.business_name,
        phone=data.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    send_welcome(user.email, user.name)
    return user


@router.post("/forgot-password", status_code=200)
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    # Siempre respondemos OK para no revelar si el email existe o no
    if user:
        token = create_access_token(
            {"sub": str(user.id), "type": "reset"},
            expires_delta=timedelta(hours=1),
        )
        reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
        send_password_reset(user.email, reset_url)
    return {"message": "Si el email existe, recibirás un link para restablecer tu contraseña."}


@router.post("/reset-password", status_code=200)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(data.token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "reset":
            raise HTTPException(status_code=400, detail="Token inválido.")
        user_id = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(status_code=400, detail="El link expiró o es inválido.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres.")

    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": "Contraseña actualizada correctamente."}


@router.post("/login", response_model=Token)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/profile", response_model=UserResponse)
def update_profile(data: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/upload-logo", response_model=UserResponse)
async def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Formato no permitido. Usá PNG, JPG o WEBP.")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="El archivo no puede superar 5MB.")

    try:
        processed = _process_logo(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo procesar la imagen: {str(e)}")

    # Eliminar logo anterior de Cloudinary si existe
    if current_user.logo_url and "cloudinary.com" in current_user.logo_url:
        try:
            # Extraer el public_id (presuapp/logos/user_{id})
            public_id = f"presuapp/logos/user_{current_user.id}"
            cloudinary.uploader.destroy(public_id)
        except Exception:
            pass  # Si falla el borrado, continuamos igual

    # Subir a Cloudinary
    try:
        public_id = f"presuapp/logos/user_{current_user.id}"
        result = cloudinary.uploader.upload(
            io.BytesIO(processed),
            public_id=public_id,
            overwrite=True,
            resource_type="image",
            format=ext.lstrip(".") if ext != ".jpg" else "jpg",
        )
        logo_url = result["secure_url"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir el logo: {str(e)}")

    current_user.logo_url = logo_url
    db.commit()
    db.refresh(current_user)
    return current_user
