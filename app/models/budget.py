from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending, accepted, rejected
    subtotal = Column(Float, default=0.0)
    discount_percent = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    tax_percent = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="budgets")
    client = relationship("Client", back_populates="budgets")
    budget_items = relationship("BudgetItem", back_populates="budget", cascade="all, delete-orphan")


class BudgetItem(Base):
    __tablename__ = "budget_items"

    id = Column(Integer, primary_key=True, index=True)
    budget_id = Column(Integer, ForeignKey("budgets.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=True)  # opcional: del banco de servicios
    description = Column(String, nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    budget = relationship("Budget", back_populates="budget_items")
