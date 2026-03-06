from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel

from database import get_db
from models.inventario import Producto, RecetaItem, ComboGrupo, ComboGrupoOpcion
from auth.deps import get_tenant_user

router = APIRouter(prefix="/tenants/{tenant_id}", tags=["Recetas & Combos"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class RecetaItemCreate(BaseModel):
    insumo_id: int
    cantidad: Decimal
    unidad_medida_id: Optional[int] = None
    notas: Optional[str] = None


class RecetaItemOut(BaseModel):
    id: int
    insumo_id: int
    insumo_nombre: str
    insumo_codigo: str
    cantidad: Decimal
    unidad_medida_id: Optional[int] = None
    notas: Optional[str] = None


class ComboGrupoCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    orden: int = 0
    es_requerido: bool = False
    min_selecciones: int = 0
    max_selecciones: int = 1


class ComboOpcionCreate(BaseModel):
    producto_id: int
    cantidad: Decimal = Decimal("1")
    es_default: bool = False
    es_opcional: bool = True
    precio_extra: Decimal = Decimal("0")


class ComboOpcionOut(BaseModel):
    id: int
    producto_id: int
    producto_nombre: str
    producto_codigo: str
    cantidad: Decimal
    es_default: bool
    es_opcional: bool
    precio_extra: Decimal
    activo: bool


class ComboGrupoOut(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    orden: int
    es_requerido: bool
    min_selecciones: int
    max_selecciones: int
    activo: bool
    opciones: List[ComboOpcionOut] = []


# ── Recetas ────────────────────────────────────────────────────────────────────

@router.get("/recetas/{producto_id}", response_model=List[RecetaItemOut])
def obtener_receta(
    tenant_id: int,
    producto_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    rows = db.execute(text("""
        SELECT r.id, r.insumo_id, p.nombre AS insumo_nombre, p.codigo AS insumo_codigo,
               r.cantidad, r.unidad_medida_id, r.notas
        FROM receta_items r
        JOIN productos p ON p.id = r.insumo_id
        WHERE r.tenant_id = :tenant AND r.producto_id = :prod
        ORDER BY p.nombre
    """), {"tenant": tenant_id, "prod": producto_id}).fetchall()

    return [RecetaItemOut(
        id=r.id, insumo_id=r.insumo_id,
        insumo_nombre=r.insumo_nombre, insumo_codigo=r.insumo_codigo,
        cantidad=r.cantidad, unidad_medida_id=r.unidad_medida_id, notas=r.notas,
    ) for r in rows]


@router.post("/recetas/{producto_id}/items", response_model=RecetaItemOut, status_code=201)
def agregar_ingrediente(
    tenant_id: int,
    producto_id: int,
    data: RecetaItemCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    # Verificar que el producto e insumo pertenecen al tenant
    prod = db.query(Producto).filter(Producto.id == producto_id, Producto.tenant_id == tenant_id).first()
    if not prod:
        raise HTTPException(404, "Producto no encontrado")
    insumo = db.query(Producto).filter(Producto.id == data.insumo_id, Producto.tenant_id == tenant_id).first()
    if not insumo:
        raise HTTPException(404, "Insumo no encontrado")
    if producto_id == data.insumo_id:
        raise HTTPException(400, "Un producto no puede ser ingrediente de sí mismo")

    # Verificar duplicado
    existe = db.query(RecetaItem).filter(
        RecetaItem.tenant_id == tenant_id,
        RecetaItem.producto_id == producto_id,
        RecetaItem.insumo_id == data.insumo_id,
    ).first()
    if existe:
        raise HTTPException(409, "Este insumo ya está en la receta. Edita la cantidad.")

    item = RecetaItem(
        tenant_id=tenant_id,
        producto_id=producto_id,
        insumo_id=data.insumo_id,
        cantidad=data.cantidad,
        unidad_medida_id=data.unidad_medida_id,
        notas=data.notas,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return RecetaItemOut(
        id=item.id, insumo_id=item.insumo_id,
        insumo_nombre=insumo.nombre, insumo_codigo=insumo.codigo,
        cantidad=item.cantidad, unidad_medida_id=item.unidad_medida_id, notas=item.notas,
    )


@router.patch("/recetas/items/{item_id}", response_model=RecetaItemOut)
def actualizar_ingrediente(
    tenant_id: int,
    item_id: int,
    data: RecetaItemCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    item = db.query(RecetaItem).filter(RecetaItem.id == item_id, RecetaItem.tenant_id == tenant_id).first()
    if not item:
        raise HTTPException(404, "Ingrediente no encontrado")
    item.cantidad = data.cantidad
    item.unidad_medida_id = data.unidad_medida_id
    item.notas = data.notas
    db.commit()
    db.refresh(item)
    insumo = db.query(Producto).get(item.insumo_id)
    return RecetaItemOut(
        id=item.id, insumo_id=item.insumo_id,
        insumo_nombre=insumo.nombre, insumo_codigo=insumo.codigo,
        cantidad=item.cantidad, unidad_medida_id=item.unidad_medida_id, notas=item.notas,
    )


@router.delete("/recetas/items/{item_id}", status_code=204)
def eliminar_ingrediente(
    tenant_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    item = db.query(RecetaItem).filter(RecetaItem.id == item_id, RecetaItem.tenant_id == tenant_id).first()
    if not item:
        raise HTTPException(404, "Ingrediente no encontrado")
    db.delete(item)
    db.commit()


# ── Combos ─────────────────────────────────────────────────────────────────────

def _build_grupo_out(grupo: ComboGrupo, db: Session) -> ComboGrupoOut:
    opciones = db.query(ComboGrupoOpcion).filter(
        ComboGrupoOpcion.grupo_id == grupo.id,
        ComboGrupoOpcion.activo == True,
    ).all()
    opciones_out = []
    for op in opciones:
        prod = db.query(Producto).get(op.producto_id)
        opciones_out.append(ComboOpcionOut(
            id=op.id, producto_id=op.producto_id,
            producto_nombre=prod.nombre if prod else f"#{op.producto_id}",
            producto_codigo=prod.codigo if prod else "",
            cantidad=op.cantidad, es_default=op.es_default,
            es_opcional=op.es_opcional, precio_extra=op.precio_extra, activo=op.activo,
        ))
    return ComboGrupoOut(
        id=grupo.id, nombre=grupo.nombre, descripcion=grupo.descripcion,
        orden=grupo.orden, es_requerido=grupo.es_requerido,
        min_selecciones=grupo.min_selecciones, max_selecciones=grupo.max_selecciones,
        activo=grupo.activo, opciones=opciones_out,
    )


@router.get("/combos/{producto_id}", response_model=List[ComboGrupoOut])
def obtener_combo(
    tenant_id: int,
    producto_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    grupos = db.query(ComboGrupo).filter(
        ComboGrupo.tenant_id == tenant_id,
        ComboGrupo.combo_producto_id == producto_id,
        ComboGrupo.activo == True,
    ).order_by(ComboGrupo.orden, ComboGrupo.id).all()
    return [_build_grupo_out(g, db) for g in grupos]


@router.post("/combos/{producto_id}/grupos", response_model=ComboGrupoOut, status_code=201)
def crear_grupo(
    tenant_id: int,
    producto_id: int,
    data: ComboGrupoCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    prod = db.query(Producto).filter(Producto.id == producto_id, Producto.tenant_id == tenant_id).first()
    if not prod:
        raise HTTPException(404, "Producto no encontrado")
    grupo = ComboGrupo(
        tenant_id=tenant_id, combo_producto_id=producto_id,
        **data.model_dump(),
    )
    db.add(grupo)
    db.commit()
    db.refresh(grupo)
    return _build_grupo_out(grupo, db)


@router.patch("/combos/grupos/{grupo_id}", response_model=ComboGrupoOut)
def actualizar_grupo(
    tenant_id: int,
    grupo_id: int,
    data: ComboGrupoCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    grupo = db.query(ComboGrupo).filter(ComboGrupo.id == grupo_id, ComboGrupo.tenant_id == tenant_id).first()
    if not grupo:
        raise HTTPException(404, "Grupo no encontrado")
    for field, val in data.model_dump().items():
        setattr(grupo, field, val)
    db.commit()
    db.refresh(grupo)
    return _build_grupo_out(grupo, db)


@router.delete("/combos/grupos/{grupo_id}", status_code=204)
def eliminar_grupo(
    tenant_id: int,
    grupo_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    grupo = db.query(ComboGrupo).filter(ComboGrupo.id == grupo_id, ComboGrupo.tenant_id == tenant_id).first()
    if not grupo:
        raise HTTPException(404, "Grupo no encontrado")
    # Soft-delete grupo y sus opciones
    db.query(ComboGrupoOpcion).filter(ComboGrupoOpcion.grupo_id == grupo_id).update({"activo": False})
    grupo.activo = False
    db.commit()


@router.post("/combos/grupos/{grupo_id}/opciones", response_model=ComboOpcionOut, status_code=201)
def agregar_opcion(
    tenant_id: int,
    grupo_id: int,
    data: ComboOpcionCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    grupo = db.query(ComboGrupo).filter(ComboGrupo.id == grupo_id, ComboGrupo.tenant_id == tenant_id).first()
    if not grupo:
        raise HTTPException(404, "Grupo no encontrado")
    prod = db.query(Producto).filter(Producto.id == data.producto_id, Producto.tenant_id == tenant_id).first()
    if not prod:
        raise HTTPException(404, "Producto no encontrado")

    opcion = ComboGrupoOpcion(tenant_id=tenant_id, grupo_id=grupo_id, **data.model_dump())
    db.add(opcion)
    db.commit()
    db.refresh(opcion)
    return ComboOpcionOut(
        id=opcion.id, producto_id=opcion.producto_id,
        producto_nombre=prod.nombre, producto_codigo=prod.codigo,
        cantidad=opcion.cantidad, es_default=opcion.es_default,
        es_opcional=opcion.es_opcional, precio_extra=opcion.precio_extra, activo=opcion.activo,
    )


@router.patch("/combos/opciones/{opcion_id}", response_model=ComboOpcionOut)
def actualizar_opcion(
    tenant_id: int,
    opcion_id: int,
    data: ComboOpcionCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    opcion = db.query(ComboGrupoOpcion).filter(
        ComboGrupoOpcion.id == opcion_id, ComboGrupoOpcion.tenant_id == tenant_id
    ).first()
    if not opcion:
        raise HTTPException(404, "Opción no encontrada")
    for field, val in data.model_dump().items():
        setattr(opcion, field, val)
    db.commit()
    db.refresh(opcion)
    prod = db.query(Producto).get(opcion.producto_id)
    return ComboOpcionOut(
        id=opcion.id, producto_id=opcion.producto_id,
        producto_nombre=prod.nombre if prod else "", producto_codigo=prod.codigo if prod else "",
        cantidad=opcion.cantidad, es_default=opcion.es_default,
        es_opcional=opcion.es_opcional, precio_extra=opcion.precio_extra, activo=opcion.activo,
    )


@router.delete("/combos/opciones/{opcion_id}", status_code=204)
def eliminar_opcion(
    tenant_id: int,
    opcion_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    opcion = db.query(ComboGrupoOpcion).filter(
        ComboGrupoOpcion.id == opcion_id, ComboGrupoOpcion.tenant_id == tenant_id
    ).first()
    if not opcion:
        raise HTTPException(404, "Opción no encontrada")
    opcion.activo = False
    db.commit()
