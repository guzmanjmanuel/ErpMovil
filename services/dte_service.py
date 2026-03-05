"""
Servicio de cálculo y construcción de DTEs (El Salvador).

Tipos soportados:
  01 - Factura Electrónica          (FCF)  → precios IVA-inclusivos
  03 - Comprobante de Crédito Fiscal(CCF)  → precios netos, IVA en resumen
  05 - Nota de Crédito Electrónica  (NC)   → igual que CCF, requiere doc relacionado
  14 - Factura de Sujeto Excluido   (FSE)  → sin IVA, usa campo "compra"

IVA El Salvador = 13%
  FCF: iva_item = venta_gravada * 13/113
  CCF: iva (en tributos resumen) = total_gravada * 13%
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, timezone
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import text

from models.dte import (
    DteIdentificacion, DteItem, DteItemTributo,
    DteResumen, DteResumenPago, DteResumenTributo,
    DteCorrelativo, DteAuditLog,
)
from models.contribuyente import DirectorioCliente, Contribuyente
from models.tenant import Tenant
from models.establecimiento import Establecimiento
from schemas.dte import DteCreate

IVA_RATE = Decimal("0.13")
IVA_DIVISOR = Decimal("1.13")
DOS_DEC = Decimal("0.01")
OCHO_DEC = Decimal("0.00000001")


def _r2(v: Decimal) -> Decimal:
    return v.quantize(DOS_DEC, rounding=ROUND_HALF_UP)


def _num_control(tipo_dte: str, cod_estable: str, correlativo: int) -> str:
    """DTE-{tipo}-{8 cod_estable}{4 cod_pto_venta}-{15 correlativo}"""
    cod = (cod_estable or "00000000").ljust(8, "0")[:8]
    corr = str(correlativo).zfill(15)
    return f"DTE-{tipo_dte}-{cod}0000-{corr}"


def _siguiente_correlativo(db: Session, tenant_id: int, tipo_dte: str, cod_estable: str = "00000000") -> int:
    row = db.execute(
        text("""
            UPDATE dte_correlativos
            SET ultimo_correlativo = ultimo_correlativo + 1
            WHERE tenant_id = :t AND tipo_dte = :dt AND cod_establecimiento = :ce
            RETURNING ultimo_correlativo
        """),
        {"t": tenant_id, "dt": tipo_dte, "ce": cod_estable},
    ).fetchone()

    if row is None:
        db.execute(
            text("""
                INSERT INTO dte_correlativos(tenant_id, tipo_dte, cod_establecimiento, ultimo_correlativo)
                VALUES (:t, :dt, :ce, 1)
            """),
            {"t": tenant_id, "dt": tipo_dte, "ce": cod_estable},
        )
        return 1

    return int(row[0])


def _numero_a_letras(monto: Decimal) -> str:
    """Convierte monto a texto para 'total_letras'. Implementación básica."""
    enteros = int(monto)
    centavos = int((monto - enteros) * 100)
    unidades = ["", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE",
                "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISÉIS",
                "DIECISIETE", "DIECIOCHO", "DIECINUEVE"]
    decenas = ["", "", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA",
               "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"]
    centenas = ["", "CIEN", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS",
                "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]

    def _parte(n: int) -> str:
        if n == 0:
            return "CERO"
        if n < 20:
            return unidades[n]
        if n < 100:
            d, u = divmod(n, 10)
            return decenas[d] + (" Y " + unidades[u] if u else "")
        if n < 1000:
            c, resto = divmod(n, 100)
            if c == 1 and resto == 0:
                return "CIEN"
            return (centenas[c] + (" " if c == 1 else "TO " if c == 5 else " ") +
                    (_parte(resto) if resto else "")).strip()
        if n < 1_000_000:
            m, resto = divmod(n, 1000)
            mil = "MIL" if m == 1 else _parte(m) + " MIL"
            return (mil + (" " + _parte(resto) if resto else "")).strip()
        return str(n)

    texto = _parte(enteros) + f" {int(enteros):,} DÓLARES".replace(",", "")
    if centavos:
        texto += f" CON {centavos:02d}/100"
    return texto


def calcular_item(
    item_input,
    tiene_iva_item: bool,
    tipo_dte: str,
) -> dict:
    """
    Calcula venta_gravada, venta_exenta, venta_no_suj e iva_item para un ítem.

    FCF (01): precio_uni incluye IVA → iva_item = venta_gravada * 13/113
    CCF (03/05): precio_uni es NETO → iva_item se calcula en resumen, no por ítem
    FSE (14): usa campo "compra"
    """
    cantidad = Decimal(str(item_input.cantidad))
    precio = Decimal(str(item_input.precio_uni))
    descuento = Decimal(str(item_input.monto_descu))

    bruto = _r2(precio * cantidad)
    neto = _r2(bruto - descuento)

    venta_no_suj = Decimal("0")
    venta_exenta = Decimal("0")
    venta_gravada = Decimal("0")
    iva_item = None
    compra = None

    if tipo_dte == "14":
        compra = neto
    elif item_input.es_no_sujeto:
        venta_no_suj = neto
    elif item_input.es_exento:
        venta_exenta = neto
    else:
        venta_gravada = neto
        if tiene_iva_item:
            iva_item = _r2(venta_gravada * IVA_RATE / IVA_DIVISOR)

    return {
        "venta_no_suj": venta_no_suj,
        "venta_exenta": venta_exenta,
        "venta_gravada": venta_gravada,
        "iva_item": iva_item,
        "compra": compra,
    }


def calcular_resumen(
    items_calculados: list[dict],
    tipo_dte: str,
    tiene_iva_item: bool,
    tiene_total_iva: bool,
    iva_perci1: Decimal = Decimal("0"),
    iva_rete1: Decimal = Decimal("0"),
    rete_renta: Decimal = Decimal("0"),
    condicion_operacion: int = 1,
) -> dict:
    total_no_suj  = _r2(sum(i["venta_no_suj"]  for i in items_calculados))
    total_exenta  = _r2(sum(i["venta_exenta"]  for i in items_calculados))
    total_gravada = _r2(sum(i["venta_gravada"] for i in items_calculados))
    total_compra  = _r2(sum(i["compra"] or 0   for i in items_calculados))

    sub_total_ventas = _r2(total_no_suj + total_exenta + total_gravada)
    sub_total = sub_total_ventas   # sin descuentos globales por ahora

    total_iva = None
    tributos = []

    if tipo_dte == "01":
        # FCF: IVA ya incluido en precio → se extrae
        total_iva = _r2(total_gravada * IVA_RATE / IVA_DIVISOR)
        monto_total = _r2(sub_total + iva_perci1 - iva_rete1 - rete_renta)
        total_pagar = monto_total
        tributos = [{"codigo": "20", "descripcion": "Impuesto al Valor Agregado 13%", "valor": total_iva}]

    elif tipo_dte in ("03", "05"):
        # CCF/NC: IVA se añade encima del precio neto
        iva = _r2(total_gravada * IVA_RATE)
        monto_total = _r2(sub_total + iva + iva_perci1 - iva_rete1 - rete_renta)
        total_pagar = monto_total
        tributos = [{"codigo": "20", "descripcion": "Impuesto al Valor Agregado 13%", "valor": iva}]

    elif tipo_dte == "14":
        monto_total = total_compra
        total_pagar = total_compra
    else:
        monto_total = sub_total
        total_pagar = sub_total

    return {
        "total_no_suj": total_no_suj,
        "total_exenta": total_exenta,
        "total_gravada": total_gravada,
        "total_compra": total_compra if tipo_dte == "14" else None,
        "sub_total_ventas": sub_total_ventas,
        "sub_total": sub_total,
        "total_iva": total_iva,
        "iva_perci1": iva_perci1,
        "iva_rete1": iva_rete1,
        "rete_renta": rete_renta,
        "monto_total_operacion": monto_total,
        "total_pagar": total_pagar,
        "total_letras": _numero_a_letras(total_pagar or monto_total),
        "condicion_operacion": condicion_operacion,
        "tributos": tributos,
    }


def _get_tenant_ambiente(db: Session, tenant_id: int) -> str:
    """Lee el ambiente configurado en el tenant (CAT-001: 00=prueba, 01=produccion)."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    return tenant.ambiente if tenant else "00"


def _get_establecimiento_principal(db: Session, tenant_id: int) -> Establecimiento | None:
    """Retorna el establecimiento marcado como principal del tenant."""
    return db.query(Establecimiento).filter(
        Establecimiento.tenant_id == tenant_id,
        Establecimiento.es_principal == True,
        Establecimiento.activo == True,
    ).first()


def crear_dte(db: Session, tenant_id: int, usuario_id: int, data: DteCreate, emisor_id: int) -> DteIdentificacion:
    """Crea el DTE completo en base de datos (estado BORRADOR)."""

    tipo = db.query(type("DteTipo", (), {})).first()  # Se carga más abajo
    from models.dte import DteTipo
    tipo = db.query(DteTipo).filter(DteTipo.codigo == data.tipo_dte).first()
    if not tipo:
        from fastapi import HTTPException
        raise HTTPException(400, f"Tipo de DTE '{data.tipo_dte}' no existe")

    # Ambiente desde configuración del tenant (CAT-001)
    ambiente = _get_tenant_ambiente(db, tenant_id)

    # Resolver receptor
    receptor_id = None
    if data.receptor_id:
        cliente = db.query(DirectorioCliente).filter(
            DirectorioCliente.id == data.receptor_id,
            DirectorioCliente.tenant_id == tenant_id,
        ).first()
        if cliente and cliente.contribuyente_id:
            receptor_id = cliente.contribuyente_id

    # Crear dte_identificacion
    now = datetime.now(timezone.utc)
    dte = DteIdentificacion(
        tenant_id=tenant_id,
        tipo_dte=data.tipo_dte,
        version=tipo.version,
        ambiente=ambiente,   # Leído del tenant, no del request
        codigo_generacion=uuid.uuid4(),
        tipo_modelo=1,
        tipo_operacion=1,
        fec_emi=data.fec_emi,
        hor_emi=now.time(),
        tipo_moneda="USD",
        emisor_id=emisor_id,
        receptor_id=receptor_id,
        estado="BORRADOR",
    )
    db.add(dte)
    db.flush()

    # Crear ítems
    items_calculados = []
    for idx, item_in in enumerate(data.items, start=1):
        calc = calcular_item(item_in, tipo.tiene_iva_item, data.tipo_dte)
        items_calculados.append(calc)

        item_db = DteItem(
            tenant_id=tenant_id,
            dte_id=dte.id,
            num_item=idx,
            tipo_item=item_in.tipo_item,
            codigo=item_in.codigo,
            descripcion=item_in.descripcion,
            cantidad=item_in.cantidad,
            uni_medida=item_in.uni_medida,
            precio_uni=item_in.precio_uni,
            monto_descu=item_in.monto_descu,
            venta_no_suj=calc["venta_no_suj"],
            venta_exenta=calc["venta_exenta"],
            venta_gravada=calc["venta_gravada"],
            iva_item=calc["iva_item"],
            compra=calc["compra"],
        )
        db.add(item_db)
        db.flush()

        for cod_trib in item_in.tributos:
            db.add(DteItemTributo(tenant_id=tenant_id, item_id=item_db.id, codigo=cod_trib))

    # Calcular resumen
    res = calcular_resumen(
        items_calculados,
        tipo_dte=data.tipo_dte,
        tiene_iva_item=tipo.tiene_iva_item,
        tiene_total_iva=tipo.tiene_total_iva,
        iva_perci1=data.iva_perci1,
        iva_rete1=data.iva_rete1,
        rete_renta=data.rete_renta,
        condicion_operacion=data.condicion_operacion,
    )

    resumen_db = DteResumen(
        tenant_id=tenant_id,
        dte_id=dte.id,
        total_no_suj=res["total_no_suj"],
        total_exenta=res["total_exenta"],
        total_gravada=res["total_gravada"],
        sub_total_ventas=res["sub_total_ventas"],
        sub_total=res["sub_total"],
        total_iva=res["total_iva"],
        iva_perci1=res["iva_perci1"],
        iva_rete1=res["iva_rete1"],
        rete_renta=res["rete_renta"],
        monto_total_operacion=res["monto_total_operacion"],
        total_pagar=res["total_pagar"],
        total_letras=res["total_letras"],
        condicion_operacion=res["condicion_operacion"],
        observaciones=data.observaciones,
    )
    db.add(resumen_db)
    db.flush()

    # Tributos del resumen
    for trib in res["tributos"]:
        db.add(DteResumenTributo(
            tenant_id=tenant_id,
            resumen_id=resumen_db.id,
            codigo=trib["codigo"],
            descripcion=trib["descripcion"],
            valor=trib["valor"],
        ))

    # Pagos (si los hay en contado, se auto-agrega el pago total)
    pagos = data.pagos
    if not pagos and data.condicion_operacion == 1:
        pagos = [type("P", (), {
            "codigo": "01",
            "monto_pago": res["total_pagar"] or res["monto_total_operacion"],
            "referencia": None,
            "plazo": None,
            "periodo": None,
        })()]

    for pago in pagos:
        db.add(DteResumenPago(
            tenant_id=tenant_id,
            resumen_id=resumen_db.id,
            codigo=pago.codigo,
            monto_pago=pago.monto_pago,
            referencia=pago.referencia,
            plazo=pago.plazo,
            periodo=pago.periodo,
        ))

    # Documento relacionado
    if data.doc_relacionado:
        from models.dte import DteDocumentoRelacionado
        db.add(DteDocumentoRelacionado(
            tenant_id=tenant_id,
            dte_id=dte.id,
            tipo_documento=data.doc_relacionado.tipo_documento,
            tipo_generacion=data.doc_relacionado.tipo_generacion,
            numero_documento=data.doc_relacionado.numero_documento,
            fecha_emision=data.doc_relacionado.fecha_emision,
        ))

    # Extensión
    if data.extension:
        from models.dte import DteExtension
        ext = data.extension
        db.add(DteExtension(
            tenant_id=tenant_id,
            dte_id=dte.id,
            nomb_entrega=ext.nomb_entrega,
            docu_entrega=ext.docu_entrega,
            nomb_recibe=ext.nomb_recibe,
            docu_recibe=ext.docu_recibe,
            observaciones=ext.observaciones,
            placa_vehiculo=ext.placa_vehiculo,
        ))

    # Audit log
    db.add(DteAuditLog(
        tenant_id=tenant_id,
        dte_id=dte.id,
        accion="CREAR",
        usuario_id=usuario_id,
        detalle={"tipo_dte": data.tipo_dte, "total": str(res["total_pagar"])},
    ))

    db.commit()
    db.refresh(dte)
    return dte


def emitir_dte(db: Session, tenant_id: int, usuario_id: int, dte: DteIdentificacion) -> DteIdentificacion:
    """
    Genera el número de control y pasa el DTE a estado EMITIDO.
    En producción aquí se enviaría al MH; por ahora se marca localmente.
    """
    if dte.estado != "BORRADOR":
        from fastapi import HTTPException
        raise HTTPException(400, f"Solo se pueden emitir DTEs en estado BORRADOR. Estado actual: {dte.estado}")

    # Usar cod_estable del establecimiento principal; fallback a "00000000"
    estab = _get_establecimiento_principal(db, tenant_id)
    cod_estable = (estab.cod_estable or "00000000") if estab else "00000000"

    correlativo = _siguiente_correlativo(db, tenant_id, dte.tipo_dte, cod_estable)
    dte.numero_control = _num_control(dte.tipo_dte, cod_estable, correlativo)
    dte.estado = "EMITIDO"

    db.add(DteAuditLog(
        tenant_id=tenant_id,
        dte_id=dte.id,
        accion="EMITIR",
        usuario_id=usuario_id,
        detalle={"numero_control": dte.numero_control},
    ))

    db.commit()
    db.refresh(dte)
    return dte
