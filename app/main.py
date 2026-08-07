import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.database import engine, Base
from app.routers import auth as auth_router
from app.routers import items as items_router
from app.routers import clients as clients_router
from app.routers import budgets as budgets_router
from app.routers import subscriptions as subscriptions_router
from app.routers import admin as admin_router

# Importar todos los modelos para que SQLAlchemy los registre
import app.models  # noqa: F401

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="PresuApp API",
    description="Backend para la aplicación de presupuestos",
    version="0.1.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — orígenes permitidos (separados por coma en la variable de entorno)
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:4200")
ALLOWED_ORIGINS = [o.strip().rstrip("/") for o in _raw_origins.split(",") if o.strip()]
print(f"[CORS] ALLOWED_ORIGINS = {ALLOWED_ORIGINS}", flush=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Crear tablas automáticamente al iniciar
Base.metadata.create_all(bind=engine)

# Auto-migración: agrega columnas nuevas sin romper datos existentes (PostgreSQL IF NOT EXISTS)
from sqlalchemy import text  # noqa: E402
try:
    with engine.connect() as _conn:
        for _sql in [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS pdf_header_text_color VARCHAR DEFAULT '#ffffff'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS pdf_logo_size VARCHAR DEFAULT 'medium'",
            "ALTER TABLE budgets ADD COLUMN IF NOT EXISTS payment_method TEXT",
            "ALTER TABLE budgets ADD COLUMN IF NOT EXISTS work_timeline TEXT",
            "ALTER TABLE budget_items ADD COLUMN IF NOT EXISTS unit VARCHAR DEFAULT ''",
        ]:
            _conn.execute(text(_sql))
        _conn.commit()
    print("[DB] Auto-migración completada.", flush=True)
except Exception as _e:
    print(f"[DB] Auto-migración: {_e}", flush=True)

# Archivos estáticos (logos subidos)
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Routers
app.include_router(auth_router.router)
app.include_router(items_router.router)
app.include_router(clients_router.router)
app.include_router(budgets_router.router)
app.include_router(subscriptions_router.router)
app.include_router(admin_router.router)


@app.get("/")
def root():
    return {"message": "PresuApp API funcionando ✓"}


@app.get("/health")
def health():
    return {"status": "ok"}
