from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    business_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    pdf_color = Column(String, nullable=True, default="#4f46e5")
    plan = Column(String, nullable=False, default="free")
    mp_subscription_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    items = relationship("Item", back_populates="user", cascade="all, delete-orphan")
    clients = relationship("Client", back_populates="user", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="user", cascade="all, delete-orphan")
