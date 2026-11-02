import uuid
from pathlib import Path
from datetime import datetime, timezone
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, String, BigInteger, JSON, DateTime, ForeignKey, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    bot_token: str
    database_url: str = 'postgresql+psycopg://fairytale:fairytale@127.0.0.1:55439/fairytale'
    public_url: str = ''
    demo_mode: bool = True
    storage: Path = Path('data')
s = Settings()
s.storage.mkdir(mode=0o700, exist_ok=True)
engine = create_engine(s.database_url, pool_pre_ping=True)
Session = sessionmaker(engine, expire_on_commit=False)
class Base(DeclarativeBase): pass
class Order(Base):
    __tablename__ = 'orders'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    status: Mapped[str] = mapped_column(String, default='draft')
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    error: Mapped[str | None] = mapped_column(String, nullable=True)
class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey('orders.id'), unique=True)
    status: Mapped[str] = mapped_column(String, default='queued')
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
