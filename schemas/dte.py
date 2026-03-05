from pydantic import BaseModel, field_validator
from typing import Optional, List
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID


# ── Catálogos ─────────────────────────────────────────────────────────────────

class DteTipoOut(BaseModel):
    codigo: str
    descripcion: str
    version: int
    requiere_nit_receptor: bool
    tiene_iva_item: bool
    tiene_total_iva: bool

    model_config = {"from_attributes": True}


# ── Items ─────────────────────────────────────────────────────────────────────

class DteItemInput(BaseModel):
    tipo_item: int = 2                          # 1=bienes 2=servicios 3=ambos
    codigo: Optional[str] = None
    descripcion: str
    cantidad: Decimal
    uni_medida: int = 59                        # 59 = unidad
    precio_uni: Decimal                         # precio unitario (IVA-inclusivo para FCF, neto para CCF)
    monto_descu: Decimal = Decimal("0")
    es_exento: bool = False
    es_no_sujeto: bool = False
    tributos: List[str] = ["20"]               # 20=IVA por defecto


class DteItemOut(BaseModel):
    id: int
    num_item: int
    tipo_item: Optional[int] = None
    codigo: Optional[str] = None
    descripcion: str
    cantidad: Decimal
    precio_uni: Decimal
    monto_descu: Decimal
    venta_no_suj: Optional[Decimal] = None
    venta_exenta: Optional[Decimal] = None
    venta_gravada: Optional[Decimal] = None
    iva_item: Optional[Decimal] = None

    model_config = {"from_attributes": True}


# ── Pagos ─────────────────────────────────────────────────────────────────────

class DtePagoInput(BaseModel):
    codigo: str = "01"                          # 01=efectivo 02=tarjeta 03=electrónico 04=cheque
    monto_pago: Decimal
    referencia: Optional[str] = None
    plazo: Optional[str] = None                # 01=días 02=meses 03=años (si crédito)
    periodo: Optional[int] = None


class DtePagoOut(BaseModel):
    id: int
    codigo: str
    monto_pago: Decimal
    referencia: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Documento relacionado ─────────────────────────────────────────────────────

class DocRelacionadoInput(BaseModel):
    tipo_documento: str
    tipo_generacion: int = 2                    # 2=electrónico
    numero_documento: str
    fecha_emision: date


# ── Extensión ─────────────────────────────────────────────────────────────────

class ExtensionInput(BaseModel):
    nomb_entrega: Optional[str] = None
    docu_entrega: Optional[str] = None
    nomb_recibe: Optional[str] = None
    docu_recibe: Optional[str] = None
    observaciones: Optional[str] = None
    placa_vehiculo: Optional[str] = None


# ── Creación del DTE ──────────────────────────────────────────────────────────

class DteCreate(BaseModel):
    tipo_dte: str                               # 01=FCF 03=CCF 05=NC 11=Exportación 14=SujetoExcluido
    ambiente: str = "00"                        # 00=pruebas 01=producción
    fec_emi: date
    condicion_operacion: int = 1                # 1=contado 2=crédito
    observaciones: Optional[str] = None

    # Receptor (cliente)
    receptor_id: Optional[int] = None          # id en directorio_clientes
    nit_receptor: Optional[str] = None         # o ingresarlo directo
    nombre_receptor: Optional[str] = None
    nrc_receptor: Optional[str] = None

    items: List[DteItemInput]
    pagos: List[DtePagoInput] = []
    doc_relacionado: Optional[DocRelacionadoInput] = None
    extension: Optional[ExtensionInput] = None

    iva_perci1: Decimal = Decimal("0")
    iva_rete1: Decimal = Decimal("0")
    rete_renta: Decimal = Decimal("0")

    pedido_id: Optional[int] = None            # vincular al pedido


# ── Resumen del DTE ───────────────────────────────────────────────────────────

class DteResumenOut(BaseModel):
    id: int
    total_no_suj: Optional[Decimal] = None
    total_exenta: Optional[Decimal] = None
    total_gravada: Optional[Decimal] = None
    sub_total_ventas: Optional[Decimal] = None
    total_descu: Optional[Decimal] = None
    sub_total: Optional[Decimal] = None
    total_iva: Optional[Decimal] = None
    iva_perci1: Optional[Decimal] = None
    iva_rete1: Optional[Decimal] = None
    rete_renta: Optional[Decimal] = None
    monto_total_operacion: Decimal
    total_pagar: Optional[Decimal] = None
    total_letras: str
    condicion_operacion: int
    observaciones: Optional[str] = None

    model_config = {"from_attributes": True}


# ── DTE completo ──────────────────────────────────────────────────────────────

class DteOut(BaseModel):
    id: int
    tipo_dte: str
    tipo_dte_desc: Optional[str] = None
    ambiente: str
    numero_control: Optional[str] = None
    codigo_generacion: Optional[UUID] = None
    fec_emi: date
    estado: str
    emisor_id: int
    receptor_id: Optional[int] = None
    created_at: datetime
    items: List[DteItemOut] = []
    resumen: Optional[DteResumenOut] = None
    pagos: List[DtePagoOut] = []

    model_config = {"from_attributes": True}


class DteListItem(BaseModel):
    id: int
    tipo_dte: str
    numero_control: Optional[str] = None
    codigo_generacion: Optional[UUID] = None
    fec_emi: date
    estado: str
    receptor_nombre: Optional[str] = None
    receptor_nit: Optional[str] = None
    monto_total_operacion: Optional[Decimal] = None
    total_pagar: Optional[Decimal] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Anulación ─────────────────────────────────────────────────────────────────

class AnulacionCreate(BaseModel):
    motivo_anulacion: str
    nombre_responsable: str
    tipo_doc_responsable: str           # 36=NIT 13=DUI
    num_doc_responsable: str
    nombre_solicita: str
    tipo_doc_solicita: str
    num_doc_solicita: str
