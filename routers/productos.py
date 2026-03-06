from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

from database import get_db
from models.inventario import (
    Producto, ProductoCodigoBarra, CategoriaProducto,
    Ubicacion, Lote, InventarioStock,
    ListaPrecio, ProductoPrecio, HistorialPrecioProducto,
)
from auth.deps import get_tenant_user
from cache.manager import (
    tenant_cache, CacheKeys,
    invalidar_listas_precio, invalidar_categorias,
    invalidar_precios_producto, invalidar_tenant,
)

router = APIRouter(prefix="/tenants/{tenant_id}", tags=["Productos"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class CodigoBarraOut(BaseModel):
    id: int
    codigo: str
    tipo: str
    es_principal: bool
    model_config = {"from_attributes": True}


class ProductoCreate(BaseModel):
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    categoria_id: Optional[int] = None
    tipo_item: int                              # CAT-011
    unidad_medida_id: int                       # CAT-014
    usa_lotes: bool = False
    usa_vencimiento: bool = False
    metodo_costo: str = "PROMEDIO"              # FIFO | LIFO | PROMEDIO
    stock_minimo: Optional[Decimal] = None
    stock_maximo: Optional[Decimal] = None
    precio_venta: Optional[Decimal] = None
    costo_referencia: Optional[Decimal] = None
    exento: bool = False
    no_sujeto: bool = False


class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    categoria_id: Optional[int] = None
    tipo_item: Optional[int] = None
    unidad_medida_id: Optional[int] = None
    usa_lotes: Optional[bool] = None
    usa_vencimiento: Optional[bool] = None
    metodo_costo: Optional[str] = None
    stock_minimo: Optional[Decimal] = None
    stock_maximo: Optional[Decimal] = None
    precio_venta: Optional[Decimal] = None
    costo_referencia: Optional[Decimal] = None
    exento: Optional[bool] = None
    no_sujeto: Optional[bool] = None


class ProductoOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    categoria_id: Optional[int] = None
    tipo_item: int
    unidad_medida_id: int
    usa_lotes: bool
    usa_vencimiento: bool
    metodo_costo: str
    stock_minimo: Optional[Decimal] = None
    stock_maximo: Optional[Decimal] = None
    precio_venta: Optional[Decimal] = None
    costo_referencia: Optional[Decimal] = None
    exento: bool
    no_sujeto: bool
    activo: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# ── Schemas Ubicaciones ────────────────────────────────────────────────────────

class UbicacionCreate(BaseModel):
    establecimiento_id: int
    nombre: str
    codigo: Optional[str] = None
    tipo: str = "BODEGA"          # BODEGA | PASILLO | ESTANTE | CASILLA | VIRTUAL
    padre_id: Optional[int] = None
    permite_picking: bool = True


class UbicacionOut(BaseModel):
    id: int
    establecimiento_id: int
    nombre: str
    codigo: Optional[str] = None
    tipo: str
    padre_id: Optional[int] = None
    permite_picking: bool
    activo: bool
    model_config = {"from_attributes": True}


# ── Schemas Categorías ─────────────────────────────────────────────────────────

class CategoriaCreate(BaseModel):
    nombre: str
    padre_id: Optional[int] = None


class CategoriaOut(BaseModel):
    id: int
    nombre: str
    padre_id: Optional[int] = None
    activo: bool
    model_config = {"from_attributes": True}


# ── Schemas Stock ──────────────────────────────────────────────────────────────

class StockOut(BaseModel):
    id: int
    producto_id: int
    ubicacion_id: int
    lote_id: Optional[int] = None
    cantidad: Decimal
    cantidad_reservada: Decimal
    costo_promedio: Optional[Decimal] = None
    model_config = {"from_attributes": True}


# ── Endpoints Categorías ───────────────────────────────────────────────────────

@router.get("/categorias-producto", response_model=List[CategoriaOut])
def listar_categorias(
    tenant_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    cached = tenant_cache.get(CacheKeys.categorias(tenant_id))
    if cached is not None:
        return cached
    rows = (
        db.query(CategoriaProducto)
        .filter(CategoriaProducto.tenant_id == tenant_id, CategoriaProducto.activo == True)
        .order_by(CategoriaProducto.nombre)
        .all()
    )
    result = [CategoriaOut.model_validate(r) for r in rows]
    tenant_cache.set(CacheKeys.categorias(tenant_id), result)
    return result


@router.post("/categorias-producto", response_model=CategoriaOut, status_code=201)
def crear_categoria(
    tenant_id: int,
    data: CategoriaCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    cat = CategoriaProducto(tenant_id=tenant_id, **data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    invalidar_categorias(tenant_id)
    return cat


@router.patch("/categorias-producto/{cat_id}", response_model=CategoriaOut)
def actualizar_categoria(
    tenant_id: int,
    cat_id: int,
    data: CategoriaCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    cat = db.query(CategoriaProducto).filter(
        CategoriaProducto.id == cat_id,
        CategoriaProducto.tenant_id == tenant_id,
    ).first()
    if not cat:
        raise HTTPException(404, "Categoría no encontrada")
    cat.nombre   = data.nombre
    cat.padre_id = data.padre_id
    db.commit()
    db.refresh(cat)
    invalidar_categorias(tenant_id)
    return cat


@router.delete("/categorias-producto/{cat_id}", status_code=204)
def eliminar_categoria(
    tenant_id: int,
    cat_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    cat = db.query(CategoriaProducto).filter(
        CategoriaProducto.id == cat_id,
        CategoriaProducto.tenant_id == tenant_id,
    ).first()
    if not cat:
        raise HTTPException(404, "Categoría no encontrada")
    # Desvincular productos y sub-categorías huérfanas
    db.query(Producto).filter(Producto.categoria_id == cat_id).update({"categoria_id": None})
    db.query(CategoriaProducto).filter(CategoriaProducto.padre_id == cat_id).update({"padre_id": None})
    cat.activo = False
    db.commit()
    invalidar_categorias(tenant_id)


# ── Endpoints Productos ────────────────────────────────────────────────────────

@router.get("/productos", response_model=List[ProductoOut])
def listar_productos(
    tenant_id: int,
    buscar: Optional[str] = None,
    categoria_id: Optional[int] = None,
    tipo_item: Optional[int] = None,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    q = db.query(Producto).filter(
        Producto.tenant_id == tenant_id,
        Producto.activo == True,
    )
    if buscar:
        like = f"%{buscar}%"
        q = q.filter(
            Producto.nombre.ilike(like) |
            Producto.codigo.ilike(like) |
            Producto.descripcion.ilike(like)
        )
    if categoria_id:
        q = q.filter(Producto.categoria_id == categoria_id)
    if tipo_item:
        q = q.filter(Producto.tipo_item == tipo_item)
    return q.order_by(Producto.nombre).all()


@router.get("/productos/{producto_id}", response_model=ProductoOut)
def obtener_producto(
    tenant_id: int,
    producto_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    p = db.query(Producto).filter(
        Producto.id == producto_id,
        Producto.tenant_id == tenant_id,
    ).first()
    if not p:
        raise HTTPException(404, "Producto no encontrado")
    return p


@router.post("/productos", response_model=ProductoOut, status_code=201)
def crear_producto(
    tenant_id: int,
    data: ProductoCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    # Verificar código único en el tenant
    existente = db.query(Producto).filter(
        Producto.tenant_id == tenant_id,
        Producto.codigo == data.codigo,
    ).first()
    if existente:
        raise HTTPException(409, f"Ya existe un producto con código '{data.codigo}'")

    p = Producto(tenant_id=tenant_id, **data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.patch("/productos/{producto_id}", response_model=ProductoOut)
def actualizar_producto(
    tenant_id: int,
    producto_id: int,
    data: ProductoUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    p = db.query(Producto).filter(
        Producto.id == producto_id,
        Producto.tenant_id == tenant_id,
    ).first()
    if not p:
        raise HTTPException(404, "Producto no encontrado")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(p, field, val)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/productos/{producto_id}", status_code=204)
def desactivar_producto(
    tenant_id: int,
    producto_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    p = db.query(Producto).filter(
        Producto.id == producto_id,
        Producto.tenant_id == tenant_id,
    ).first()
    if not p:
        raise HTTPException(404, "Producto no encontrado")
    p.activo = False
    db.commit()


# ── Endpoints Códigos de Barra ─────────────────────────────────────────────────

@router.get("/productos/{producto_id}/codigos-barra", response_model=List[CodigoBarraOut])
def listar_codigos_barra(
    tenant_id: int,
    producto_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    return (
        db.query(ProductoCodigoBarra)
        .filter(
            ProductoCodigoBarra.producto_id == producto_id,
            ProductoCodigoBarra.tenant_id == tenant_id,
            ProductoCodigoBarra.activo == True,
        )
        .order_by(ProductoCodigoBarra.es_principal.desc())
        .all()
    )


class CodigoBarraCreate(BaseModel):
    codigo: str
    tipo: str = "EAN13"
    es_principal: bool = False


@router.post("/productos/{producto_id}/codigos-barra", response_model=CodigoBarraOut, status_code=201)
def agregar_codigo_barra(
    tenant_id: int,
    producto_id: int,
    data: CodigoBarraCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    # Verificar que el código no esté en uso en el tenant
    existente = db.query(ProductoCodigoBarra).filter(
        ProductoCodigoBarra.tenant_id == tenant_id,
        ProductoCodigoBarra.codigo == data.codigo,
        ProductoCodigoBarra.activo == True,
    ).first()
    if existente:
        raise HTTPException(409, f"El código '{data.codigo}' ya está asignado a otro producto")

    if data.es_principal:
        db.query(ProductoCodigoBarra).filter(
            ProductoCodigoBarra.producto_id == producto_id,
        ).update({"es_principal": False})

    cb = ProductoCodigoBarra(
        producto_id=producto_id,
        tenant_id=tenant_id,
        **data.model_dump(),
    )
    db.add(cb)
    db.commit()
    db.refresh(cb)
    return cb


@router.delete("/productos/{producto_id}/codigos-barra/{cb_id}", status_code=204)
def eliminar_codigo_barra(
    tenant_id: int,
    producto_id: int,
    cb_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    cb = db.query(ProductoCodigoBarra).filter(
        ProductoCodigoBarra.id == cb_id,
        ProductoCodigoBarra.producto_id == producto_id,
        ProductoCodigoBarra.tenant_id == tenant_id,
    ).first()
    if not cb:
        raise HTTPException(404, "Código de barra no encontrado")
    cb.activo = False
    db.commit()


# ── Endpoints Ubicaciones ──────────────────────────────────────────────────────

@router.get("/ubicaciones", response_model=List[UbicacionOut])
def listar_ubicaciones(
    tenant_id: int,
    establecimiento_id: Optional[int] = None,
    tipo: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    q = db.query(Ubicacion).filter(
        Ubicacion.tenant_id == tenant_id,
        Ubicacion.activo == True,
    )
    if establecimiento_id:
        q = q.filter(Ubicacion.establecimiento_id == establecimiento_id)
    if tipo:
        q = q.filter(Ubicacion.tipo == tipo.upper())
    return q.order_by(Ubicacion.nombre).all()


@router.post("/ubicaciones", response_model=UbicacionOut, status_code=201)
def crear_ubicacion(
    tenant_id: int,
    data: UbicacionCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    ub = Ubicacion(tenant_id=tenant_id, **data.model_dump())
    db.add(ub)
    db.commit()
    db.refresh(ub)
    return ub


@router.patch("/ubicaciones/{ubicacion_id}", response_model=UbicacionOut)
def actualizar_ubicacion(
    tenant_id: int,
    ubicacion_id: int,
    data: UbicacionCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    ub = db.query(Ubicacion).filter(
        Ubicacion.id == ubicacion_id,
        Ubicacion.tenant_id == tenant_id,
    ).first()
    if not ub:
        raise HTTPException(404, "Ubicación no encontrada")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(ub, field, val)
    db.commit()
    db.refresh(ub)
    return ub


# ── Consulta de Stock ──────────────────────────────────────────────────────────

@router.get("/productos/{producto_id}/stock", response_model=List[StockOut])
def stock_por_producto(
    tenant_id: int,
    producto_id: int,
    ubicacion_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    q = db.query(InventarioStock).filter(
        InventarioStock.tenant_id == tenant_id,
        InventarioStock.producto_id == producto_id,
    )
    if ubicacion_id:
        q = q.filter(InventarioStock.ubicacion_id == ubicacion_id)
    return q.all()


# ── Listas de Precio ───────────────────────────────────────────────────────────

class ListaPrecioCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    es_default: bool = False


class ListaPrecioOut(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    es_default: bool
    activo: bool
    model_config = {"from_attributes": True}


class ProductoPrecioSet(BaseModel):
    """Establece (crea o actualiza) el precio de un producto en una lista."""
    lista_precio_id: int
    precio: Decimal
    motivo: Optional[str] = None


class ProductoPrecioOut(BaseModel):
    id: int
    lista_precio_id: int
    precio: Decimal
    updated_at: datetime
    model_config = {"from_attributes": True}


class HistorialPrecioOut(BaseModel):
    id: int
    lista_precio_id: int
    precio_anterior: Optional[Decimal] = None
    precio_nuevo: Decimal
    motivo: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}


@router.get("/listas-precio", response_model=List[ListaPrecioOut])
def listar_listas_precio(
    tenant_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    cached = tenant_cache.get(CacheKeys.listas_precio(tenant_id))
    if cached is not None:
        return cached
    rows = (
        db.query(ListaPrecio)
        .filter(ListaPrecio.tenant_id == tenant_id, ListaPrecio.activo == True)
        .order_by(ListaPrecio.nombre)
        .all()
    )
    result = [ListaPrecioOut.model_validate(r) for r in rows]
    tenant_cache.set(CacheKeys.listas_precio(tenant_id), result)
    return result


@router.post("/listas-precio", response_model=ListaPrecioOut, status_code=201)
def crear_lista_precio(
    tenant_id: int,
    data: ListaPrecioCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    if data.es_default:
        db.query(ListaPrecio).filter(
            ListaPrecio.tenant_id == tenant_id,
        ).update({"es_default": False})

    lp = ListaPrecio(tenant_id=tenant_id, **data.model_dump())
    db.add(lp)
    db.commit()
    db.refresh(lp)
    invalidar_listas_precio(tenant_id)
    return lp


@router.delete("/listas-precio/{lista_id}", status_code=204)
def eliminar_lista_precio(
    tenant_id: int,
    lista_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    lp = db.query(ListaPrecio).filter(
        ListaPrecio.id == lista_id,
        ListaPrecio.tenant_id == tenant_id,
    ).first()
    if not lp:
        raise HTTPException(404, "Lista de precio no encontrada")
    lp.activo = False
    db.commit()
    invalidar_listas_precio(tenant_id)


@router.patch("/listas-precio/{lista_id}", response_model=ListaPrecioOut)
def actualizar_lista_precio(
    tenant_id: int,
    lista_id: int,
    data: ListaPrecioCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    lp = db.query(ListaPrecio).filter(
        ListaPrecio.id == lista_id,
        ListaPrecio.tenant_id == tenant_id,
    ).first()
    if not lp:
        raise HTTPException(404, "Lista de precio no encontrada")

    if data.es_default:
        db.query(ListaPrecio).filter(
            ListaPrecio.tenant_id == tenant_id,
            ListaPrecio.id != lista_id,
        ).update({"es_default": False})

    for field, val in data.model_dump(exclude_none=True).items():
        setattr(lp, field, val)
    db.commit()
    db.refresh(lp)
    invalidar_listas_precio(tenant_id)
    return lp


# ── Precios por Producto ───────────────────────────────────────────────────────

@router.get("/productos/{producto_id}/precios", response_model=List[ProductoPrecioOut])
def listar_precios_producto(
    tenant_id: int,
    producto_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    cache_key = CacheKeys.precios_producto(tenant_id, producto_id)
    cached = tenant_cache.get(cache_key)
    if cached is not None:
        return cached
    rows = (
        db.query(ProductoPrecio)
        .filter(
            ProductoPrecio.tenant_id == tenant_id,
            ProductoPrecio.producto_id == producto_id,
            ProductoPrecio.activo == True,
        )
        .all()
    )
    result = [ProductoPrecioOut.model_validate(r) for r in rows]
    tenant_cache.set(cache_key, result)
    return result


@router.put("/productos/{producto_id}/precios", response_model=ProductoPrecioOut)
def establecer_precio(
    tenant_id: int,
    producto_id: int,
    data: ProductoPrecioSet,
    db: Session = Depends(get_db),
    current_user=Depends(get_tenant_user),
):
    """Crea o actualiza el precio de un producto en una lista. Registra historial."""
    pp = db.query(ProductoPrecio).filter(
        ProductoPrecio.tenant_id == tenant_id,
        ProductoPrecio.producto_id == producto_id,
        ProductoPrecio.lista_precio_id == data.lista_precio_id,
    ).first()

    precio_anterior = pp.precio if pp else None

    if pp:
        pp.precio = data.precio
    else:
        pp = ProductoPrecio(
            tenant_id=tenant_id,
            producto_id=producto_id,
            lista_precio_id=data.lista_precio_id,
            precio=data.precio,
        )
        db.add(pp)

    # Registrar en historial
    hist = HistorialPrecioProducto(
        tenant_id=tenant_id,
        producto_id=producto_id,
        lista_precio_id=data.lista_precio_id,
        precio_anterior=precio_anterior,
        precio_nuevo=data.precio,
        usuario_id=current_user.usuario_id,
        motivo=data.motivo,
    )
    db.add(hist)

    # Actualizar costo_referencia en producto si es la lista default
    lista = db.query(ListaPrecio).filter(ListaPrecio.id == data.lista_precio_id).first()
    if lista and lista.es_default:
        prod = db.query(Producto).filter(Producto.id == producto_id).first()
        if prod:
            prod.precio_venta = data.precio

    db.commit()
    db.refresh(pp)
    invalidar_precios_producto(tenant_id, producto_id)
    return pp


@router.get("/productos/{producto_id}/historial-precios", response_model=List[HistorialPrecioOut])
def historial_precios(
    tenant_id: int,
    producto_id: int,
    lista_precio_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    q = db.query(HistorialPrecioProducto).filter(
        HistorialPrecioProducto.tenant_id == tenant_id,
        HistorialPrecioProducto.producto_id == producto_id,
    )
    if lista_precio_id:
        q = q.filter(HistorialPrecioProducto.lista_precio_id == lista_precio_id)
    return q.order_by(HistorialPrecioProducto.created_at.desc()).all()


# ── Importación masiva desde Excel ────────────────────────────────────────────

class ImportarFilaProducto(BaseModel):
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    categoria_id: Optional[int] = None
    tipo_item: int = 1                   # CAT-011
    unidad_medida_id: int = 36           # 36=Unidad por defecto
    metodo_costo: str = "PROMEDIO"
    precio_venta: Optional[Decimal] = None
    costo_referencia: Optional[Decimal] = None
    stock_minimo: Optional[Decimal] = None
    stock_maximo: Optional[Decimal] = None
    exento: bool = False
    no_sujeto: bool = False
    usa_lotes: bool = False
    usa_vencimiento: bool = False
    codigo_barra: Optional[str] = None   # código de barra principal
    tipo_barra: str = "EAN13"


class ImportarResultado(BaseModel):
    importados: int
    omitidos: int
    errores: List[str]


@router.post("/productos/importar", response_model=ImportarResultado)
def importar_productos(
    tenant_id: int,
    filas: List[ImportarFilaProducto],
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    """
    Importación masiva de productos desde Excel (el frontend parsea el Excel
    y envía las filas como JSON). Omite filas con código duplicado.
    """
    importados = 0
    omitidos = 0
    errores: List[str] = []

    for i, fila in enumerate(filas, start=2):  # start=2 porque fila 1 es encabezado
        if not fila.codigo or not fila.nombre:
            errores.append(f"Fila {i}: código y nombre son obligatorios")
            omitidos += 1
            continue

        existente = db.query(Producto).filter(
            Producto.tenant_id == tenant_id,
            Producto.codigo == fila.codigo.strip(),
        ).first()

        if existente:
            omitidos += 1
            errores.append(f"Fila {i}: código '{fila.codigo}' ya existe — omitido")
            continue

        try:
            p = Producto(
                tenant_id=tenant_id,
                codigo=fila.codigo.strip(),
                nombre=fila.nombre.strip(),
                descripcion=fila.descripcion,
                categoria_id=fila.categoria_id,
                tipo_item=fila.tipo_item,
                unidad_medida_id=fila.unidad_medida_id,
                metodo_costo=fila.metodo_costo.upper(),
                precio_venta=fila.precio_venta,
                costo_referencia=fila.costo_referencia,
                stock_minimo=fila.stock_minimo,
                stock_maximo=fila.stock_maximo,
                exento=fila.exento,
                no_sujeto=fila.no_sujeto,
                usa_lotes=fila.usa_lotes,
                usa_vencimiento=fila.usa_vencimiento,
            )
            db.add(p)
            db.flush()  # obtener p.id sin commit

            if fila.codigo_barra:
                cb = ProductoCodigoBarra(
                    producto_id=p.id,
                    tenant_id=tenant_id,
                    codigo=fila.codigo_barra.strip(),
                    tipo=fila.tipo_barra.upper(),
                    es_principal=True,
                )
                db.add(cb)

            importados += 1
        except Exception as e:
            errores.append(f"Fila {i}: error al guardar — {str(e)}")
            omitidos += 1
            db.rollback()
            continue

    db.commit()
    # Invalida todo el caché del tenant tras importación masiva
    invalidar_tenant(tenant_id)
    return ImportarResultado(importados=importados, omitidos=omitidos, errores=errores)


# ── Cache admin ────────────────────────────────────────────────────────────────

@router.post("/cache/invalidar", tags=["Admin"], status_code=204)
def invalidar_cache_tenant(
    tenant_id: int,
    _=Depends(get_tenant_user),
):
    """Fuerza recarga de todo el caché del tenant. Útil tras cambios manuales en BD."""
    invalidar_tenant(tenant_id)


@router.get("/cache/stats", tags=["Admin"])
def stats_cache(
    _=Depends(get_tenant_user),
):
    """Estadísticas del caché en memoria (global + tenant)."""
    from cache.manager import global_cache, tenant_cache
    return {
        "global_cache": global_cache.stats(),
        "tenant_cache": tenant_cache.stats(),
    }
