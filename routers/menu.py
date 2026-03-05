from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.menu import MenuCategoria, MenuItem, MenuVariante, ModificadorGrupo, Modificador
from schemas.menu import (
    CategoriaOut, CategoriaCreate,
    MenuItemOut, MenuItemCreate, MenuItemUpdate,
    VarianteOut, ModificadorGrupoOut, ModificadorOut,
)
from auth.deps import get_current_user, get_tenant_user
from models.usuario import Usuario

router = APIRouter(prefix="/tenants/{tenant_id}/menu", tags=["Menu"])


# ── Categorias ────────────────────────────────────────────────────────────────

@router.get("/categorias", response_model=List[CategoriaOut])
def listar_categorias(
    tenant_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    return db.query(MenuCategoria).filter(
        MenuCategoria.tenant_id == tenant_id,
        MenuCategoria.activo == True,
    ).order_by(MenuCategoria.orden).all()


@router.post("/categorias", response_model=CategoriaOut, status_code=201)
def crear_categoria(
    tenant_id: int,
    data: CategoriaCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    cat = MenuCategoria(tenant_id=tenant_id, **data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/categorias/{cat_id}", status_code=204)
def eliminar_categoria(
    tenant_id: int,
    cat_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    cat = db.query(MenuCategoria).filter(
        MenuCategoria.id == cat_id, MenuCategoria.tenant_id == tenant_id
    ).first()
    if not cat:
        raise HTTPException(404, "Categoría no encontrada")
    cat.activo = False
    db.commit()


# ── Items ─────────────────────────────────────────────────────────────────────

@router.get("/items", response_model=List[MenuItemOut])
def listar_items(
    tenant_id: int,
    categoria_id: int | None = None,
    solo_disponibles: bool = False,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    q = db.query(MenuItem).filter(MenuItem.tenant_id == tenant_id, MenuItem.activo == True)
    if categoria_id:
        q = q.filter(MenuItem.categoria_id == categoria_id)
    if solo_disponibles:
        q = q.filter(MenuItem.disponible == True)
    return q.order_by(MenuItem.orden).all()


@router.get("/items/{item_id}", response_model=MenuItemOut)
def obtener_item(
    tenant_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    item = db.query(MenuItem).filter(
        MenuItem.id == item_id, MenuItem.tenant_id == tenant_id
    ).first()
    if not item:
        raise HTTPException(404, "Item no encontrado")
    return item


@router.post("/items", response_model=MenuItemOut, status_code=201)
def crear_item(
    tenant_id: int,
    data: MenuItemCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    item = MenuItem(tenant_id=tenant_id, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/items/{item_id}", response_model=MenuItemOut)
def actualizar_item(
    tenant_id: int,
    item_id: int,
    data: MenuItemUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    item = db.query(MenuItem).filter(
        MenuItem.id == item_id, MenuItem.tenant_id == tenant_id
    ).first()
    if not item:
        raise HTTPException(404, "Item no encontrado")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


# ── Variantes ─────────────────────────────────────────────────────────────────

@router.get("/items/{item_id}/variantes", response_model=List[VarianteOut])
def listar_variantes(
    tenant_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    return db.query(MenuVariante).filter(
        MenuVariante.menu_item_id == item_id,
        MenuVariante.tenant_id == tenant_id,
        MenuVariante.activo == True,
    ).all()


# ── Modificadores ─────────────────────────────────────────────────────────────

@router.get("/modificadores", response_model=List[ModificadorGrupoOut])
def listar_modificadores(
    tenant_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    grupos = db.query(ModificadorGrupo).filter(
        ModificadorGrupo.tenant_id == tenant_id,
        ModificadorGrupo.activo == True,
    ).all()
    result = []
    for g in grupos:
        mods = db.query(Modificador).filter(
            Modificador.grupo_id == g.id,
            Modificador.disponible == True,
        ).all()
        result.append(ModificadorGrupoOut(
            id=g.id,
            nombre=g.nombre,
            requerido=g.requerido,
            seleccion_multiple=g.seleccion_multiple,
            modificadores=[ModificadorOut.model_validate(m) for m in mods],
        ))
    return result
