from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Call(Base):
    __tablename__ = "calls"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    mc_number: Mapped[str | None] = mapped_column(String, nullable=True)
    carrier_name: Mapped[str | None] = mapped_column(String, nullable=True)
    carrier_eligible: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    load_id: Mapped[str | None] = mapped_column(String, nullable=True)
    load_found: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String, nullable=True)
    outcome_source: Mapped[str | None] = mapped_column(String, nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String, nullable=True)
    final_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    rounds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    run_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NegotiationEvent(Base):
    __tablename__ = "negotiation_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Intentionally no FK to calls.run_id — events may be written before the call row exists
    run_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    load_id: Mapped[str] = mapped_column(String, nullable=False)
    carrier_offer: Mapped[float] = mapped_column(Float, nullable=False)
    agent_price: Mapped[float] = mapped_column(Float, nullable=False)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


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
