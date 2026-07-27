import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.routers import auth as auth_router
from app.routers import items as items_router
from app.routers import clients as clients_router
from app.routers import budgets as budgets_router

# Importar todos los modelos para que SQLAlchemy los registre
import app.models  # noqa: F401

app = FastAPI(
    title="PresuApp API",
    description="Backend para la aplicación de presupuestos",
    version="0.1.0"
)

# CORS — orígenes permitidos (separados por coma en la variable de entorno)
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:4200")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/")
def root():
    return {"message": "PresuApp API funcionando ✓"}


@app.get("/health")
def health():
    return {"status": "ok"}
