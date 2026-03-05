from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey,
    Numeric, SmallInteger, Text, Date, Time, UUID as SAUUID
)
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.sql import func
import uuid
from database import Base


class DteTipo(Base):
    __tablename__ = "dte_tipos"

    codigo = Column(String(2), primary_key=True)
    descripcion = Column(String(100), nullable=False)
    version = Column(SmallInteger, nullable=False)
    requiere_nit_receptor = Column(Boolean, nullable=False, default=False)
    tiene_iva_item = Column(Boolean, nullable=False, default=False)
    tiene_iva_perci = Column(Boolean, nullable=False, default=False)
    tiene_total_iva = Column(Boolean, nullable=False, default=False)
    tiene_venta_nosuj = Column(Boolean, nullable=False, default=True)
    tiene_venta_exenta = Column(Boolean, nullable=False, default=True)
    tiene_seguro_flete = Column(Boolean, nullable=False, default=False)
    tiene_incoterms = Column(Boolean, nullable=False, default=False)
    tiene_extension = Column(Boolean, nullable=False, default=True)
    tiene_doc_relacionado = Column(Boolean, nullable=False, default=True)
    doc_relacionado_obligatorio = Column(Boolean, nullable=False, default=False)
    receptor_internacional = Column(Boolean, nullable=False, default=False)
    tiene_sujeto_excluido = Column(Boolean, nullable=False, default=False)
    tiene_pagos_resumen = Column(Boolean, nullable=False, default=True)
    tiene_total_pagar = Column(Boolean, nullable=False, default=True)
    tiene_compra_item = Column(Boolean, nullable=False, default=False)


class DteCorrelativo(Base):
    __tablename__ = "dte_correlativos"

    tenant_id = Column(Integer, ForeignKey("tenants.id"), primary_key=True)
    tipo_dte = Column(String(2), primary_key=True)
    cod_establecimiento = Column(String(8), primary_key=True, default="00000000")
    ultimo_correlativo = Column(Numeric, nullable=False, default=0)


class DteIdentificacion(Base):
    __tablename__ = "dte_identificacion"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tipo_dte = Column(String(2), ForeignKey("dte_tipos.codigo"), nullable=False)
    version = Column(SmallInteger, nullable=False)
    ambiente = Column(String(1), nullable=False, default="00")   # 00=pruebas, 01=producción
    numero_control = Column(String(31))
    codigo_generacion = Column(SAUUID(as_uuid=True), default=uuid.uuid4)
    tipo_modelo = Column(SmallInteger, nullable=False, default=1)
    tipo_operacion = Column(SmallInteger, nullable=False, default=1)
    tipo_contingencia = Column(SmallInteger)
    motivo_contin = Column(String(150))
    fec_emi = Column(Date, nullable=False)
    hor_emi = Column(Time, nullable=False)
    tipo_moneda = Column(String(3), nullable=False, default="USD")
    emisor_id = Column(Integer, ForeignKey("contribuyentes.id"), nullable=False)
    receptor_id = Column(Integer, ForeignKey("contribuyentes.id"))
    sujeto_excluido_id = Column(Integer, ForeignKey("contribuyentes.id"))
    venta_tercero_id = Column(Integer, ForeignKey("contribuyentes.id"))
    estado = Column(String(20), nullable=False, default="BORRADOR")
    sello_recibido = Column(String(100))
    observaciones_mh = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DteItem(Base):
    __tablename__ = "dte_items"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    dte_id = Column(Integer, ForeignKey("dte_identificacion.id"), nullable=False)
    num_item = Column(Integer, nullable=False)
    tipo_item = Column(SmallInteger)            # 1=bienes, 2=servicios, 3=ambos, 4=otros
    numero_documento = Column(String(36))
    codigo = Column(String(25))
    cod_tributo = Column(String(2))
    descripcion = Column(String(1000), nullable=False)
    cantidad = Column(Numeric, nullable=False)
    uni_medida = Column(SmallInteger, nullable=False, default=59)  # 59=unidad
    precio_uni = Column(Numeric, nullable=False)
    monto_descu = Column(Numeric, nullable=False, default=0)
    venta_no_suj = Column(Numeric, default=0)
    venta_exenta = Column(Numeric, default=0)
    venta_gravada = Column(Numeric, default=0)
    iva_item = Column(Numeric)
    compra = Column(Numeric)
    psv = Column(Numeric, default=0)
    no_gravado = Column(Numeric, default=0)


class DteItemTributo(Base):
    __tablename__ = "dte_items_tributos"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("dte_items.id"), nullable=False)
    codigo = Column(String(2), nullable=False)   # 20=IVA, A6=FOVIAL, D5=COTRANS


class DteResumen(Base):
    __tablename__ = "dte_resumen"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    dte_id = Column(Integer, ForeignKey("dte_identificacion.id"), nullable=False)
    total_no_suj = Column(Numeric, default=0)
    total_exenta = Column(Numeric, default=0)
    total_gravada = Column(Numeric, default=0)
    sub_total_ventas = Column(Numeric)
    decu_no_suj = Column(Numeric, default=0)
    decu_exenta = Column(Numeric, default=0)
    decu_gravada = Column(Numeric, default=0)
    porcentaje_descuento = Column(Numeric, default=0)
    total_descu = Column(Numeric, default=0)
    descuento = Column(Numeric)
    total_compra = Column(Numeric)
    descu = Column(Numeric)
    sub_total = Column(Numeric)
    iva_perci1 = Column(Numeric, default=0)
    iva_rete1 = Column(Numeric, default=0)
    rete_renta = Column(Numeric, default=0)
    total_iva = Column(Numeric)
    monto_total_operacion = Column(Numeric, nullable=False)
    total_no_gravado = Column(Numeric, default=0)
    total_pagar = Column(Numeric)
    total_letras = Column(String(200), nullable=False)
    saldo_favor = Column(Numeric)
    seguro = Column(Numeric)
    flete = Column(Numeric)
    cod_incoterms = Column(String(10))
    desc_incoterms = Column(String(100))
    observaciones = Column(String(3000))
    condicion_operacion = Column(SmallInteger, nullable=False, default=1)  # 1=contado, 2=crédito, 3=otro
    num_pago_electronico = Column(String(50))


class DteResumenPago(Base):
    __tablename__ = "dte_resumen_pagos"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    resumen_id = Column(Integer, ForeignKey("dte_resumen.id"), nullable=False)
    codigo = Column(String(2), nullable=False)   # 01=billete, 02=tarjeta, 03=dinero electrónico, 04=cheque
    monto_pago = Column(Numeric, nullable=False)
    referencia = Column(String(50))
    plazo = Column(String(2))                    # 01=día, 02=mes, 03=año (si crédito)
    periodo = Column(Numeric)


class DteResumenTributo(Base):
    __tablename__ = "dte_resumen_tributos"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    resumen_id = Column(Integer, ForeignKey("dte_resumen.id"), nullable=False)
    codigo = Column(String(2), nullable=False)
    descripcion = Column(String(100), nullable=False)
    valor = Column(Numeric, nullable=False)


class DteDocumentoRelacionado(Base):
    __tablename__ = "dte_documentos_relacionados"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    dte_id = Column(Integer, ForeignKey("dte_identificacion.id"), nullable=False)
    tipo_documento = Column(String(2), nullable=False)
    tipo_generacion = Column(SmallInteger, nullable=False, default=2)  # 1=manual, 2=electrónico
    numero_documento = Column(String(36), nullable=False)
    fecha_emision = Column(Date, nullable=False)


class DteExtension(Base):
    __tablename__ = "dte_extension"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    dte_id = Column(Integer, ForeignKey("dte_identificacion.id"), nullable=False)
    nomb_entrega = Column(String(100))
    docu_entrega = Column(String(25))
    nomb_recibe = Column(String(100))
    docu_recibe = Column(String(25))
    observaciones = Column(String(3000))
    placa_vehiculo = Column(String(10))


class DteApendice(Base):
    __tablename__ = "dte_apendice"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    dte_id = Column(Integer, ForeignKey("dte_identificacion.id"), nullable=False)
    campo = Column(String(25), nullable=False)
    etiqueta = Column(String(50), nullable=False)
    valor = Column(String(150), nullable=False)


class DteAuditLog(Base):
    __tablename__ = "dte_audit_log"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    dte_id = Column(Integer, ForeignKey("dte_identificacion.id"), nullable=False)
    accion = Column(String(30), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    detalle = Column(JSONB)
    ip_origen = Column(INET)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MhEnvio(Base):
    __tablename__ = "mh_envios"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    dte_id = Column(Integer, ForeignKey("dte_identificacion.id"), nullable=False)
    intento = Column(SmallInteger, nullable=False, default=1)
    estado = Column(String(20), nullable=False, default="pendiente")
    url_endpoint = Column(String(200))
    request_payload = Column(JSONB)
    response_payload = Column(JSONB)
    sello_recibido = Column(String(100))
    codigo_mensaje = Column(String(20))
    descripcion_msg = Column(Text)
    fecha_envio = Column(DateTime(timezone=True))
    fecha_respuesta = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MhAnulacion(Base):
    __tablename__ = "mh_anulaciones"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    dte_id = Column(Integer, ForeignKey("dte_identificacion.id"), nullable=False)
    motivo_anulacion = Column(String(250), nullable=False)
    nombre_responsable = Column(String(100), nullable=False)
    tipo_doc_responsable = Column(String(2), nullable=False)
    num_doc_responsable = Column(String(20), nullable=False)
    nombre_solicita = Column(String(100), nullable=False)
    tipo_doc_solicita = Column(String(2), nullable=False)
    num_doc_solicita = Column(String(20), nullable=False)
    estado = Column(String(20), nullable=False, default="pendiente")
    response_payload = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
