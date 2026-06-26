from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Load(Base):
    __tablename__ = "loads"

    load_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    origin: Mapped[str] = mapped_column(String, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    pickup_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    delivery_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    equipment_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    loadboard_rate: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight: Mapped[int] = mapped_column(Integer, nullable=False)
    commodity_type: Mapped[str] = mapped_column(String, nullable=False)
    num_of_pieces: Mapped[int] = mapped_column(Integer, nullable=False)
    miles: Mapped[int] = mapped_column(Integer, nullable=False)
    dimensions: Mapped[str | None] = mapped_column(String, nullable=True)
