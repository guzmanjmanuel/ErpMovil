from sqlalchemy import Column, String
from database import Base


class CatActividadEconomica(Base):
    __tablename__ = "cat_actividad_economica"

    codigo      = Column(String(10), primary_key=True)
    descripcion = Column(String(250), nullable=False)
