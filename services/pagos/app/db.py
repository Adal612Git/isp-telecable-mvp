from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os


def _build_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    host = os.getenv("DB_HOST", "postgres")
    user = os.getenv("DB_USER", "isp_admin")
    password = os.getenv("DB_PASS", "admin")
    name = os.getenv("DB_NAME", "isp_mvp")
    return f"postgresql+psycopg2://{user}:{password}@{host}:5432/{name}"


DATABASE_URL = _build_database_url()


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    from .models import Pago, Transaccion, WebhookLog, IdempotencyKey, Conciliacion
    Base.metadata.create_all(bind=engine)
