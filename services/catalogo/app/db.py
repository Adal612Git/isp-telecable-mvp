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
    from .models import Plan, Combo, ZonaCobertura, CompatibilidadTecnologica
    Base.metadata.create_all(bind=engine)
    # Minimal seed for offline/unit usage
    from sqlalchemy.orm import Session
    with Session(bind=engine) as s:
        if not s.query(ZonaCobertura).first():
            s.add(ZonaCobertura(nombre="NORTE", factor_precio=1.0, tecnologias="FTTH,HFC"))
            s.add(ZonaCobertura(nombre="SUR", factor_precio=1.1, tecnologias="FTTH"))
        if not s.query(Plan).first():
            s.add(Plan(codigo="INT100", tecnologia="FTTH", velocidad=100, precio_base=299.0))
            s.add(Plan(codigo="INT300", tecnologia="FTTH", velocidad=300, precio_base=499.0))
            s.add(Plan(codigo="HFC50", tecnologia="HFC", velocidad=50, precio_base=199.0))
        if not s.query(CompatibilidadTecnologica).first():
            for z in s.query(ZonaCobertura).all():
                for t in z.tecnologias.split(","):
                    s.add(CompatibilidadTecnologica(tecnologia=t, zona=z.nombre))
        s.commit()
