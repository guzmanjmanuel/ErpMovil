-- Migración: actualizar tabla productos al esquema de inventario ERP
-- Ejecutar UNA sola vez.
-- Renombra columnas existentes y agrega las nuevas del modelo de inventario.

BEGIN;

-- ── 1. Renombrar columnas que cambiaron de nombre ──────────────────────────────
ALTER TABLE productos RENAME COLUMN uni_medida      TO unidad_medida_id;
ALTER TABLE productos RENAME COLUMN precio_unitario TO precio_venta;
ALTER TABLE productos RENAME COLUMN es_exento       TO exento;
ALTER TABLE productos RENAME COLUMN es_no_sujeto    TO no_sujeto;

-- ── 2. Agregar columnas nuevas del modelo de inventario ────────────────────────
ALTER TABLE productos
    ADD COLUMN IF NOT EXISTS nombre           VARCHAR(250),
    ADD COLUMN IF NOT EXISTS usa_lotes        BOOLEAN      NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS usa_vencimiento  BOOLEAN      NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS metodo_costo     VARCHAR(10)  NOT NULL DEFAULT 'PROMEDIO',
    ADD COLUMN IF NOT EXISTS stock_minimo     NUMERIC(14,4),
    ADD COLUMN IF NOT EXISTS stock_maximo     NUMERIC(14,4),
    ADD COLUMN IF NOT EXISTS costo_referencia NUMERIC(14,4);

-- ── 3. Migrar datos: poblar nombre con los primeros 250 chars de descripcion ───
UPDATE productos
SET nombre = LEFT(descripcion, 250)
WHERE nombre IS NULL OR nombre = '';

-- ── 4. Hacer nombre NOT NULL (ya tiene datos) ─────────────────────────────────
ALTER TABLE productos ALTER COLUMN nombre SET NOT NULL;

-- ── 5. Hacer descripcion nullable (el modelo lo permite) ──────────────────────
ALTER TABLE productos ALTER COLUMN descripcion DROP NOT NULL;

-- ── 6. Hacer codigo NOT NULL si aun es nullable ───────────────────────────────
UPDATE productos SET codigo = 'PROD-' || id::text WHERE codigo IS NULL;
ALTER TABLE productos ALTER COLUMN codigo SET NOT NULL;

-- ── 7. Ajustar precio_venta: nullable en el nuevo modelo ──────────────────────
-- precio_unitario era NOT NULL en el viejo esquema; el nuevo modelo lo permite nulo.
-- Dejamos los valores existentes y solo removemos el NOT NULL.
ALTER TABLE productos ALTER COLUMN precio_venta DROP NOT NULL;

COMMIT;
