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


@app.get("/")
def root():
    return {"message": "PresuApp API funcionando ✓"}


@app.get("/health")
def health():
    return {"status": "ok"}
