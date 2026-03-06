from sqlalchemy import (
    Boolean, Column, Date, ForeignKey, Integer, Numeric,
    SmallInteger, String, Text, DateTime,
)
from sqlalchemy.sql import func
from database import Base


class CategoriaProducto(Base):
    __tablename__ = "categorias_producto"

    id        = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    nombre    = Column(String(100), nullable=False)
    padre_id  = Column(Integer, ForeignKey("categorias_producto.id"))   # jerarquía
    activo    = Column(Boolean, nullable=False, default=True)


class Producto(Base):
    __tablename__ = "productos"

    id               = Column(Integer, primary_key=True)
    tenant_id        = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    codigo           = Column(String(50), nullable=False)
    nombre           = Column(String(250), nullable=False)
    descripcion      = Column(Text)
    categoria_id     = Column(Integer, ForeignKey("categorias_producto.id"))
    tipo_item        = Column(SmallInteger, ForeignKey("cat_tipo_item.codigo"), nullable=False)
    unidad_medida_id = Column(SmallInteger, ForeignKey("cat_unidad_medida.codigo"), nullable=False)
    # Inventario
    usa_lotes        = Column(Boolean, nullable=False, default=False)
    usa_vencimiento  = Column(Boolean, nullable=False, default=False)
    metodo_costo     = Column(String(10), nullable=False, default="PROMEDIO")   # FIFO | LIFO | PROMEDIO
    stock_minimo     = Column(Numeric(14, 4), default=0)
    stock_maximo     = Column(Numeric(14, 4))
    # Precios
    precio_venta     = Column(Numeric(14, 4))
    costo_referencia = Column(Numeric(14, 4))
    # Fiscal
    exento           = Column(Boolean, nullable=False, default=False)
    no_sujeto        = Column(Boolean, nullable=False, default=False)
    # Tipo restaurante
    tipo_producto    = Column(String(20), nullable=False, default="PRODUCTO")  # PRODUCTO | COMBO | INSUMO | SERVICIO
    # Control
    activo           = Column(Boolean, nullable=False, default=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ProductoCodigoBarra(Base):
    __tablename__ = "producto_codigos_barra"

    id           = Column(Integer, primary_key=True)
    producto_id  = Column(Integer, ForeignKey("productos.id"), nullable=False)
    tenant_id    = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    codigo       = Column(String(100), nullable=False)
    tipo         = Column(String(20), nullable=False, default="EAN13")   # EAN13 | UPC | QR | INTERNO
    es_principal = Column(Boolean, nullable=False, default=False)
    activo       = Column(Boolean, nullable=False, default=True)


class Ubicacion(Base):
    __tablename__ = "ubicaciones"

    id                 = Column(Integer, primary_key=True)
    tenant_id          = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=False)
    nombre             = Column(String(100), nullable=False)
    codigo             = Column(String(30))
    tipo               = Column(String(20), nullable=False, default="BODEGA")   # BODEGA | PASILLO | ESTANTE | CASILLA | VIRTUAL
    padre_id           = Column(Integer, ForeignKey("ubicaciones.id"))
    permite_picking    = Column(Boolean, nullable=False, default=True)
    activo             = Column(Boolean, nullable=False, default=True)


class Lote(Base):
    __tablename__ = "lotes"

    id                = Column(Integer, primary_key=True)
    tenant_id         = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    producto_id       = Column(Integer, ForeignKey("productos.id"), nullable=False)
    numero_lote       = Column(String(100), nullable=False)
    fecha_fabricacion = Column(Date)
    fecha_vencimiento = Column(Date)
    proveedor_id      = Column(Integer, ForeignKey("directorio_clientes.id"))
    notas             = Column(Text)
    activo            = Column(Boolean, nullable=False, default=True)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())


class InventarioStock(Base):
    __tablename__ = "inventario_stock"

    id                 = Column(Integer, primary_key=True)
    tenant_id          = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    producto_id        = Column(Integer, ForeignKey("productos.id"), nullable=False)
    ubicacion_id       = Column(Integer, ForeignKey("ubicaciones.id"), nullable=False)
    lote_id            = Column(Integer, ForeignKey("lotes.id"))
    cantidad           = Column(Numeric(14, 4), nullable=False, default=0)
    cantidad_reservada = Column(Numeric(14, 4), nullable=False, default=0)
    costo_promedio     = Column(Numeric(14, 6), default=0)
    updated_at         = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class InventarioMovimiento(Base):
    __tablename__ = "inventario_movimientos"

    id                   = Column(Integer, primary_key=True)
    tenant_id            = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tipo_movimiento      = Column(String(30), nullable=False)
    # COMPRA | VENTA | AJUSTE_POSITIVO | AJUSTE_NEGATIVO |
    # TRANSFERENCIA_SALIDA | TRANSFERENCIA_ENTRADA |
    # DEVOLUCION_COMPRA | DEVOLUCION_VENTA | APERTURA
    producto_id          = Column(Integer, ForeignKey("productos.id"), nullable=False)
    ubicacion_origen_id  = Column(Integer, ForeignKey("ubicaciones.id"))
    ubicacion_destino_id = Column(Integer, ForeignKey("ubicaciones.id"))
    lote_id              = Column(Integer, ForeignKey("lotes.id"))
    cantidad             = Column(Numeric(14, 4), nullable=False)
    costo_unitario       = Column(Numeric(14, 6), nullable=False, default=0)
    # costo_total es columna generada en DB (no se mapea como Column normal)
    referencia_tipo      = Column(String(30))   # DTE | PEDIDO | AJUSTE | TRANSFERENCIA
    referencia_id        = Column(Integer)
    usuario_id           = Column(Integer, ForeignKey("usuarios.id"))
    notas                = Column(Text)
    created_at           = Column(DateTime(timezone=True), server_default=func.now())


class InventarioCapa(Base):
    __tablename__ = "inventario_capas_costo"

    id                  = Column(Integer, primary_key=True)
    tenant_id           = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    producto_id         = Column(Integer, ForeignKey("productos.id"), nullable=False)
    ubicacion_id        = Column(Integer, ForeignKey("ubicaciones.id"), nullable=False)
    lote_id             = Column(Integer, ForeignKey("lotes.id"))
    movimiento_id       = Column(Integer, ForeignKey("inventario_movimientos.id"), nullable=False)
    fecha_entrada       = Column(DateTime(timezone=True), server_default=func.now())
    cantidad_inicial    = Column(Numeric(14, 4), nullable=False)
    cantidad_disponible = Column(Numeric(14, 4), nullable=False)
    costo_unitario      = Column(Numeric(14, 6), nullable=False)
    cerrada             = Column(Boolean, nullable=False, default=False)


class HistorialCostoProducto(Base):
    __tablename__ = "historial_costos_producto"

    id             = Column(Integer, primary_key=True)
    tenant_id      = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    producto_id    = Column(Integer, ForeignKey("productos.id"), nullable=False)
    costo_anterior = Column(Numeric(14, 6))
    costo_nuevo    = Column(Numeric(14, 6), nullable=False)
    metodo         = Column(String(10), nullable=False)
    movimiento_id  = Column(Integer, ForeignKey("inventario_movimientos.id"))
    usuario_id     = Column(Integer, ForeignKey("usuarios.id"))
    motivo         = Column(String(200))
    created_at     = Column(DateTime(timezone=True), server_default=func.now())


class AjusteInventario(Base):
    __tablename__ = "ajustes_inventario"

    id           = Column(Integer, primary_key=True)
    tenant_id    = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    ubicacion_id = Column(Integer, ForeignKey("ubicaciones.id"))
    motivo       = Column(String(200), nullable=False)
    estado       = Column(String(20), nullable=False, default="BORRADOR")   # BORRADOR | APLICADO | CANCELADO
    usuario_id   = Column(Integer, ForeignKey("usuarios.id"))
    aplicado_en  = Column(DateTime(timezone=True))
    created_at   = Column(DateTime(timezone=True), server_default=func.now())


class AjusteInventarioDetalle(Base):
    __tablename__ = "ajustes_inventario_detalle"

    id               = Column(Integer, primary_key=True)
    ajuste_id        = Column(Integer, ForeignKey("ajustes_inventario.id"), nullable=False)
    producto_id      = Column(Integer, ForeignKey("productos.id"), nullable=False)
    ubicacion_id     = Column(Integer, ForeignKey("ubicaciones.id"), nullable=False)
    lote_id          = Column(Integer, ForeignKey("lotes.id"))
    cantidad_sistema = Column(Numeric(14, 4), nullable=False)
    cantidad_fisica  = Column(Numeric(14, 4), nullable=False)
    # diferencia es columna generada en DB
    costo_unitario   = Column(Numeric(14, 6), nullable=False, default=0)


# ── Listas de Precio ───────────────────────────────────────────────────────────

class ListaPrecio(Base):
    __tablename__ = "listas_precio"

    id          = Column(Integer, primary_key=True)
    tenant_id   = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    nombre      = Column(String(100), nullable=False)
    descripcion = Column(String(250))
    es_default  = Column(Boolean, nullable=False, default=False)
    activo      = Column(Boolean, nullable=False, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class ProductoPrecio(Base):
    """Precio vigente por producto + lista de precio."""
    __tablename__ = "producto_precios"

    id              = Column(Integer, primary_key=True)
    tenant_id       = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    producto_id     = Column(Integer, ForeignKey("productos.id"), nullable=False)
    lista_precio_id = Column(Integer, ForeignKey("listas_precio.id"), nullable=False)
    precio          = Column(Numeric(14, 4), nullable=False)
    activo          = Column(Boolean, nullable=False, default=True)
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ── Recetas de producción ──────────────────────────────────────────────────────

class RecetaItem(Base):
    """Ingredientes/insumos que componen un producto o plato."""
    __tablename__ = "receta_items"

    id               = Column(Integer, primary_key=True)
    tenant_id        = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    producto_id      = Column(Integer, ForeignKey("productos.id"), nullable=False)  # el plato/producto final
    insumo_id        = Column(Integer, ForeignKey("productos.id"), nullable=False)  # el ingrediente
    cantidad         = Column(Numeric(14, 4), nullable=False)
    unidad_medida_id = Column(SmallInteger, ForeignKey("cat_unidad_medida.codigo"))
    notas            = Column(Text)


# ── Combos ─────────────────────────────────────────────────────────────────────

class ComboGrupo(Base):
    """Grupo de opciones dentro de un combo (ej: 'Bebida', 'Complemento')."""
    __tablename__ = "combo_grupos"

    id                = Column(Integer, primary_key=True)
    tenant_id         = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    combo_producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    nombre            = Column(String(100), nullable=False)
    descripcion       = Column(String(300))
    orden             = Column(SmallInteger, nullable=False, default=0)
    es_requerido      = Column(Boolean, nullable=False, default=False)
    min_selecciones   = Column(SmallInteger, nullable=False, default=0)
    max_selecciones   = Column(SmallInteger, nullable=False, default=1)
    activo            = Column(Boolean, nullable=False, default=True)


class ComboGrupoOpcion(Base):
    """Producto disponible como opción dentro de un grupo de combo."""
    __tablename__ = "combo_grupo_opciones"

    id           = Column(Integer, primary_key=True)
    grupo_id     = Column(Integer, ForeignKey("combo_grupos.id"), nullable=False)
    tenant_id    = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    producto_id  = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad     = Column(Numeric(14, 4), nullable=False, default=1)
    es_default   = Column(Boolean, nullable=False, default=False)   # viene incluido por defecto
    es_opcional  = Column(Boolean, nullable=False, default=True)    # el cliente puede rechazarlo
    precio_extra = Column(Numeric(14, 4), nullable=False, default=0)
    activo       = Column(Boolean, nullable=False, default=True)


class HistorialPrecioProducto(Base):
    """Registro inmutable de cada cambio de precio."""
    __tablename__ = "historial_precios_producto"

    id              = Column(Integer, primary_key=True)
    tenant_id       = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    producto_id     = Column(Integer, ForeignKey("productos.id"), nullable=False)
    lista_precio_id = Column(Integer, ForeignKey("listas_precio.id"), nullable=False)
    precio_anterior = Column(Numeric(14, 4))
    precio_nuevo    = Column(Numeric(14, 4), nullable=False)
    usuario_id      = Column(Integer, ForeignKey("usuarios.id"))
    motivo          = Column(String(200))
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
