"""
Migración: CAT-016 Condición de la Operación + CAT-017 Forma de Pago
Ejecutar: python migrations/cat_016_017.py

Qué hace:
  1. Crea tabla cat_condicion_operacion (CAT-016) y siembra datos
  2. Crea tabla cat_forma_pago (CAT-017) y siembra datos
  3. Agrega columna condicion_operacion a pedidos (default 1 = Contado)
  4. Modifica pedido_pagos.forma_pago a VARCHAR(2) para códigos CAT-017
  5. Agrega forma_pago_referencia a pedido_pagos
"""
import psycopg2

conn = psycopg2.connect(
    host="31.97.43.150", port=5433, dbname="MasErp",
    user="postgres", password="Mas=2025", connect_timeout=10
)
conn.autocommit = True
cur = conn.cursor()

pasos = [
    # ── CAT-016 ──────────────────────────────────────────────────────────────
    (
        "Crear tabla cat_condicion_operacion",
        """
        CREATE TABLE IF NOT EXISTS cat_condicion_operacion (
            codigo      SMALLINT PRIMARY KEY,
            descripcion VARCHAR(50) NOT NULL
        )
        """,
    ),
    (
        "Seed CAT-016",
        """
        INSERT INTO cat_condicion_operacion (codigo, descripcion) VALUES
            (1, 'Contado'),
            (2, 'A crédito'),
            (3, 'Otro')
        ON CONFLICT (codigo) DO UPDATE SET descripcion = EXCLUDED.descripcion
        """,
    ),

    # ── CAT-017 ──────────────────────────────────────────────────────────────
    (
        "Crear tabla cat_forma_pago",
        """
        CREATE TABLE IF NOT EXISTS cat_forma_pago (
            codigo               VARCHAR(2)   PRIMARY KEY,
            descripcion          VARCHAR(100) NOT NULL,
            requiere_referencia  BOOLEAN      NOT NULL DEFAULT FALSE
        )
        """,
    ),
    (
        "Seed CAT-017",
        """
        INSERT INTO cat_forma_pago (codigo, descripcion, requiere_referencia) VALUES
            ('01', 'Billetes y monedas',              FALSE),
            ('02', 'Tarjeta Débito',                  FALSE),
            ('03', 'Tarjeta Crédito',                 FALSE),
            ('04', 'Cheque',                          FALSE),
            ('05', 'Transferencia-Depósito Bancario', FALSE),
            ('08', 'Dinero electrónico',              FALSE),
            ('09', 'Monedero electrónico',            FALSE),
            ('11', 'Bitcoin',                         FALSE),
            ('12', 'Otras Criptomonedas',             FALSE),
            ('13', 'Cuentas por pagar del receptor',  FALSE),
            ('14', 'Giro bancario',                   FALSE),
            ('99', 'Otros',                           TRUE)
        ON CONFLICT (codigo) DO UPDATE
            SET descripcion         = EXCLUDED.descripcion,
                requiere_referencia = EXCLUDED.requiere_referencia
        """,
    ),

    # ── Pedidos: agregar condicion_operacion ──────────────────────────────────
    (
        "Agregar condicion_operacion a pedidos",
        """
        ALTER TABLE pedidos
            ADD COLUMN IF NOT EXISTS condicion_operacion SMALLINT
                NOT NULL DEFAULT 1
                REFERENCES cat_condicion_operacion(codigo)
        """,
    ),

    # ── Pedido_pagos: migrar forma_pago a código CAT-017 ─────────────────────
    (
        "Agregar forma_pago_referencia a pedido_pagos",
        """
        ALTER TABLE pedido_pagos
            ADD COLUMN IF NOT EXISTS forma_pago_referencia VARCHAR(200)
        """,
    ),
    (
        "Ampliar forma_pago a VARCHAR(200) para backfill",
        """
        ALTER TABLE pedido_pagos
            ALTER COLUMN forma_pago TYPE VARCHAR(200)
        """,
    ),
    (
        "Backfill forma_pago: efectivo → 01",
        """
        UPDATE pedido_pagos SET forma_pago = '01' WHERE forma_pago = 'efectivo'
        """,
    ),
    (
        "Backfill forma_pago: tarjeta → 02 (débito por defecto)",
        """
        UPDATE pedido_pagos SET forma_pago = '02' WHERE forma_pago = 'tarjeta'
        """,
    ),
    (
        "Backfill forma_pago: qr → 08 (dinero electrónico)",
        """
        UPDATE pedido_pagos SET forma_pago = '08' WHERE forma_pago = 'qr'
        """,
    ),
    (
        "Limitar forma_pago a VARCHAR(2) con FK",
        """
        ALTER TABLE pedido_pagos
            ALTER COLUMN forma_pago TYPE VARCHAR(2)
        """,
    ),
    (
        "Agregar FK forma_pago → cat_forma_pago",
        """
        ALTER TABLE pedido_pagos
            DROP CONSTRAINT IF EXISTS fk_pedido_pagos_forma_pago,
            ADD CONSTRAINT fk_pedido_pagos_forma_pago
                FOREIGN KEY (forma_pago) REFERENCES cat_forma_pago(codigo)
        """,
    ),
]

for nombre, sql in pasos:
    cur.execute(sql)
    print(f"  ✓ {nombre}")

cur.close()
conn.close()
print("\nMigración CAT-016 + CAT-017 completada.")
