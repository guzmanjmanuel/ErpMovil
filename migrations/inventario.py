"""
Migración: Sistema de Inventario — 11 tablas
Ejecutar: python migrations/inventario.py
"""
import psycopg2

conn = psycopg2.connect(
    host="31.97.43.150", port=5433, dbname="MasErp",
    user="postgres", password="Mas=2025", connect_timeout=10
)
conn.autocommit = True
cur = conn.cursor()

tables = [
    ("categorias_producto", """
        CREATE TABLE IF NOT EXISTS categorias_producto (
            id        SERIAL PRIMARY KEY,
            tenant_id INT NOT NULL REFERENCES tenants(id),
            nombre    VARCHAR(100) NOT NULL,
            padre_id  INT REFERENCES categorias_producto(id),
            activo    BOOLEAN NOT NULL DEFAULT TRUE
        )
    """),

    ("productos", """
        CREATE TABLE IF NOT EXISTS productos (
            id               SERIAL PRIMARY KEY,
            tenant_id        INT NOT NULL REFERENCES tenants(id),
            codigo           VARCHAR(50) NOT NULL,
            nombre           VARCHAR(250) NOT NULL,
            descripcion      TEXT,
            categoria_id     INT REFERENCES categorias_producto(id),
            tipo_item        SMALLINT NOT NULL REFERENCES cat_tipo_item(codigo),
            unidad_medida_id SMALLINT NOT NULL REFERENCES cat_unidad_medida(codigo),
            usa_lotes        BOOLEAN NOT NULL DEFAULT FALSE,
            usa_vencimiento  BOOLEAN NOT NULL DEFAULT FALSE,
            metodo_costo     VARCHAR(10) NOT NULL DEFAULT 'PROMEDIO',
            stock_minimo     NUMERIC(14,4) DEFAULT 0,
            stock_maximo     NUMERIC(14,4),
            precio_venta     NUMERIC(14,4),
            costo_referencia NUMERIC(14,4),
            exento           BOOLEAN NOT NULL DEFAULT FALSE,
            no_sujeto        BOOLEAN NOT NULL DEFAULT FALSE,
            activo           BOOLEAN NOT NULL DEFAULT TRUE,
            created_at       TIMESTAMPTZ DEFAULT NOW(),
            updated_at       TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (tenant_id, codigo)
        )
    """),

    ("producto_codigos_barra", """
        CREATE TABLE IF NOT EXISTS producto_codigos_barra (
            id           SERIAL PRIMARY KEY,
            producto_id  INT NOT NULL REFERENCES productos(id),
            tenant_id    INT NOT NULL REFERENCES tenants(id),
            codigo       VARCHAR(100) NOT NULL,
            tipo         VARCHAR(20) NOT NULL DEFAULT 'EAN13',
            es_principal BOOLEAN NOT NULL DEFAULT FALSE,
            activo       BOOLEAN NOT NULL DEFAULT TRUE,
            UNIQUE (tenant_id, codigo)
        )
    """),

    ("ubicaciones", """
        CREATE TABLE IF NOT EXISTS ubicaciones (
            id                 SERIAL PRIMARY KEY,
            tenant_id          INT NOT NULL REFERENCES tenants(id),
            establecimiento_id INT NOT NULL REFERENCES establecimientos(id),
            nombre             VARCHAR(100) NOT NULL,
            codigo             VARCHAR(30),
            tipo               VARCHAR(20) NOT NULL DEFAULT 'BODEGA',
            padre_id           INT REFERENCES ubicaciones(id),
            permite_picking    BOOLEAN NOT NULL DEFAULT TRUE,
            activo             BOOLEAN NOT NULL DEFAULT TRUE
        )
    """),

    ("lotes", """
        CREATE TABLE IF NOT EXISTS lotes (
            id                SERIAL PRIMARY KEY,
            tenant_id         INT NOT NULL REFERENCES tenants(id),
            producto_id       INT NOT NULL REFERENCES productos(id),
            numero_lote       VARCHAR(100) NOT NULL,
            fecha_fabricacion DATE,
            fecha_vencimiento DATE,
            proveedor_id      INT REFERENCES directorio_clientes(id),
            notas             TEXT,
            activo            BOOLEAN NOT NULL DEFAULT TRUE,
            created_at        TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (tenant_id, producto_id, numero_lote)
        )
    """),

    ("inventario_stock", """
        CREATE TABLE IF NOT EXISTS inventario_stock (
            id                 SERIAL PRIMARY KEY,
            tenant_id          INT NOT NULL REFERENCES tenants(id),
            producto_id        INT NOT NULL REFERENCES productos(id),
            ubicacion_id       INT NOT NULL REFERENCES ubicaciones(id),
            lote_id            INT REFERENCES lotes(id),
            cantidad           NUMERIC(14,4) NOT NULL DEFAULT 0,
            cantidad_reservada NUMERIC(14,4) NOT NULL DEFAULT 0,
            costo_promedio     NUMERIC(14,6) DEFAULT 0,
            updated_at         TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (tenant_id, producto_id, ubicacion_id, lote_id)
        )
    """),

    ("inventario_movimientos", """
        CREATE TABLE IF NOT EXISTS inventario_movimientos (
            id                   SERIAL PRIMARY KEY,
            tenant_id            INT NOT NULL REFERENCES tenants(id),
            tipo_movimiento      VARCHAR(30) NOT NULL,
            producto_id          INT NOT NULL REFERENCES productos(id),
            ubicacion_origen_id  INT REFERENCES ubicaciones(id),
            ubicacion_destino_id INT REFERENCES ubicaciones(id),
            lote_id              INT REFERENCES lotes(id),
            cantidad             NUMERIC(14,4) NOT NULL,
            costo_unitario       NUMERIC(14,6) NOT NULL DEFAULT 0,
            costo_total          NUMERIC(14,6) GENERATED ALWAYS AS (cantidad * costo_unitario) STORED,
            referencia_tipo      VARCHAR(30),
            referencia_id        INT,
            usuario_id           INT REFERENCES usuarios(id),
            notas                TEXT,
            created_at           TIMESTAMPTZ DEFAULT NOW()
        )
    """),

    ("inventario_capas_costo", """
        CREATE TABLE IF NOT EXISTS inventario_capas_costo (
            id                  SERIAL PRIMARY KEY,
            tenant_id           INT NOT NULL REFERENCES tenants(id),
            producto_id         INT NOT NULL REFERENCES productos(id),
            ubicacion_id        INT NOT NULL REFERENCES ubicaciones(id),
            lote_id             INT REFERENCES lotes(id),
            movimiento_id       INT NOT NULL REFERENCES inventario_movimientos(id),
            fecha_entrada       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            cantidad_inicial    NUMERIC(14,4) NOT NULL,
            cantidad_disponible NUMERIC(14,4) NOT NULL,
            costo_unitario      NUMERIC(14,6) NOT NULL,
            cerrada             BOOLEAN NOT NULL DEFAULT FALSE
        )
    """),

    ("historial_costos_producto", """
        CREATE TABLE IF NOT EXISTS historial_costos_producto (
            id             SERIAL PRIMARY KEY,
            tenant_id      INT NOT NULL REFERENCES tenants(id),
            producto_id    INT NOT NULL REFERENCES productos(id),
            costo_anterior NUMERIC(14,6),
            costo_nuevo    NUMERIC(14,6) NOT NULL,
            metodo         VARCHAR(10) NOT NULL,
            movimiento_id  INT REFERENCES inventario_movimientos(id),
            usuario_id     INT REFERENCES usuarios(id),
            motivo         VARCHAR(200),
            created_at     TIMESTAMPTZ DEFAULT NOW()
        )
    """),

    ("ajustes_inventario", """
        CREATE TABLE IF NOT EXISTS ajustes_inventario (
            id           SERIAL PRIMARY KEY,
            tenant_id    INT NOT NULL REFERENCES tenants(id),
            ubicacion_id INT REFERENCES ubicaciones(id),
            motivo       VARCHAR(200) NOT NULL,
            estado       VARCHAR(20) NOT NULL DEFAULT 'BORRADOR',
            usuario_id   INT REFERENCES usuarios(id),
            aplicado_en  TIMESTAMPTZ,
            created_at   TIMESTAMPTZ DEFAULT NOW()
        )
    """),

    ("ajustes_inventario_detalle", """
        CREATE TABLE IF NOT EXISTS ajustes_inventario_detalle (
            id               SERIAL PRIMARY KEY,
            ajuste_id        INT NOT NULL REFERENCES ajustes_inventario(id),
            producto_id      INT NOT NULL REFERENCES productos(id),
            ubicacion_id     INT NOT NULL REFERENCES ubicaciones(id),
            lote_id          INT REFERENCES lotes(id),
            cantidad_sistema NUMERIC(14,4) NOT NULL,
            cantidad_fisica  NUMERIC(14,4) NOT NULL,
            diferencia       NUMERIC(14,4) GENERATED ALWAYS AS (cantidad_fisica - cantidad_sistema) STORED,
            costo_unitario   NUMERIC(14,6) NOT NULL DEFAULT 0
        )
    """),
]

for name, sql in tables:
    cur.execute(sql)
    print(f"  {name} OK")

cur.close()
conn.close()
print("Migración completada — 11 tablas creadas.")
