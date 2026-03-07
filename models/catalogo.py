from sqlalchemy import Column, SmallInteger, String, Boolean
from database import Base


class CatActividadEconomica(Base):
    __tablename__ = "cat_actividad_economica"

    codigo      = Column(String(10), primary_key=True)
    descripcion = Column(String(250), nullable=False)


class Departamento(Base):
    __tablename__ = "departamentos"   # CAT-012, tabla existente

    codigo = Column(String(2), primary_key=True)
    nombre = Column(String(50), nullable=False)


class Municipio(Base):
    __tablename__ = "municipios"      # CAT-013, tabla existente

    codigo          = Column(String(4), primary_key=True)
    departamento_id = Column(String(2), nullable=False)
    nombre          = Column(String(100), nullable=False)


class CatTipoItem(Base):
    __tablename__ = "cat_tipo_item"   # CAT-011

    codigo      = Column(SmallInteger, primary_key=True)
    descripcion = Column(String(100), nullable=False)


class CatUnidadMedida(Base):
    __tablename__ = "cat_unidad_medida"   # CAT-014

    codigo      = Column(SmallInteger, primary_key=True)
    descripcion = Column(String(100), nullable=False)


class CatCondicionOperacion(Base):
    """CAT-016 — Condición de la Operación (requerido en DTE)."""
    __tablename__ = "cat_condicion_operacion"

    codigo      = Column(SmallInteger, primary_key=True)   # 1, 2, 3
    descripcion = Column(String(50), nullable=False)       # Contado, A crédito, Otro


class CatFormaPago(Base):
    """CAT-017 — Forma de Pago (requerido en DTE)."""
    __tablename__ = "cat_forma_pago"

    codigo              = Column(String(2), primary_key=True)   # "01" … "99"
    descripcion         = Column(String(100), nullable=False)
    requiere_referencia = Column(Boolean, nullable=False, default=False)  # True solo para código 99
