from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    unit_price = Column(Float, nullable=False, default=0.0)
    unit = Column(String, default="unidad")  # hora, metro, m2, unidad, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="items")
