-- ============================================================
-- Migración: combos y recetas de producción
-- ============================================================

-- 1. Tipo de producto en catálogo
ALTER TABLE productos
    ADD COLUMN IF NOT EXISTS tipo_producto VARCHAR(20) NOT NULL DEFAULT 'PRODUCTO';
-- Valores: PRODUCTO | COMBO | INSUMO | SERVICIO

COMMENT ON COLUMN productos.tipo_producto IS 'PRODUCTO=simple, COMBO=agrupa componentes, INSUMO=ingrediente de inventario, SERVICIO=no afecta stock';

-- 2. Recetas de producción
-- Cada producto (plato/bebida) puede tener N ingredientes (insumos)
CREATE TABLE IF NOT EXISTS receta_items (
    id               SERIAL PRIMARY KEY,
    tenant_id        INTEGER NOT NULL REFERENCES tenants(id),
    producto_id      INTEGER NOT NULL REFERENCES productos(id),   -- el plato/producto final
    insumo_id        INTEGER NOT NULL REFERENCES productos(id),   -- el ingrediente (tipo INSUMO)
    cantidad         NUMERIC(14,4) NOT NULL,
    unidad_medida_id SMALLINT REFERENCES cat_unidad_medida(codigo),
    notas            TEXT,
    UNIQUE (producto_id, insumo_id)
);

-- 3. Grupos de opciones para combos
-- Un combo tiene N grupos (ej: "Bebida", "Complemento", "Proteína")
CREATE TABLE IF NOT EXISTS combo_grupos (
    id                SERIAL PRIMARY KEY,
    tenant_id         INTEGER NOT NULL REFERENCES tenants(id),
    combo_producto_id INTEGER NOT NULL REFERENCES productos(id),
    nombre            VARCHAR(100) NOT NULL,
    descripcion       VARCHAR(300),
    orden             SMALLINT NOT NULL DEFAULT 0,
    es_requerido      BOOLEAN NOT NULL DEFAULT FALSE,  -- debe seleccionarse al menos una opción
    min_selecciones   SMALLINT NOT NULL DEFAULT 0,
    max_selecciones   SMALLINT NOT NULL DEFAULT 1,     -- 1=único, >1=múltiple
    activo            BOOLEAN NOT NULL DEFAULT TRUE
);

-- 4. Opciones dentro de cada grupo
-- Cada opción es un producto que el cliente puede elegir
CREATE TABLE IF NOT EXISTS combo_grupo_opciones (
    id           SERIAL PRIMARY KEY,
    grupo_id     INTEGER NOT NULL REFERENCES combo_grupos(id),
    tenant_id    INTEGER NOT NULL REFERENCES tenants(id),
    producto_id  INTEGER NOT NULL REFERENCES productos(id),
    cantidad     NUMERIC(14,4) NOT NULL DEFAULT 1,
    es_default   BOOLEAN NOT NULL DEFAULT FALSE,   -- viene incluido por defecto en el combo
    es_opcional  BOOLEAN NOT NULL DEFAULT TRUE,    -- el cliente puede rechazarlo
    precio_extra NUMERIC(14,4) NOT NULL DEFAULT 0, -- cargo adicional si se elige este
    activo       BOOLEAN NOT NULL DEFAULT TRUE
);

-- 5. Componentes elegidos por el cliente por línea de pedido
-- Se registra qué hizo el cliente con cada grupo del combo
CREATE TABLE IF NOT EXISTS pedido_item_componentes (
    id                 SERIAL PRIMARY KEY,
    pedido_item_id     INTEGER NOT NULL REFERENCES pedido_items(id),
    tenant_id          INTEGER NOT NULL REFERENCES tenants(id),
    grupo_id           INTEGER NOT NULL,   -- combo_grupos.id
    opcion_original_id INTEGER,            -- combo_grupo_opciones.id (la opción default)
    opcion_elegida_id  INTEGER,            -- combo_grupo_opciones.id (la que pidió; NULL=rechazó)
    cantidad           NUMERIC(14,4) NOT NULL DEFAULT 1,
    accion             VARCHAR(20) NOT NULL DEFAULT 'INCLUIDO',  -- INCLUIDO | RECHAZADO | SUSTITUIDO
    precio_extra       NUMERIC(14,4) NOT NULL DEFAULT 0
);

-- Índices de rendimiento
CREATE INDEX IF NOT EXISTS idx_receta_items_producto ON receta_items(producto_id);
CREATE INDEX IF NOT EXISTS idx_combo_grupos_producto ON combo_grupos(combo_producto_id);
CREATE INDEX IF NOT EXISTS idx_combo_opciones_grupo ON combo_grupo_opciones(grupo_id);
CREATE INDEX IF NOT EXISTS idx_pedido_item_comp ON pedido_item_componentes(pedido_item_id);
