"""
Migración: POS + Caja — ajustes y columnas faltantes
Ejecutar: python migrations/pos_caja.py

Qué hace:
  1. Agrega numero_pedido a pedidos (si no existe)
  2. Agrega turno_id a pedido_pagos (si no existe)
  3. Backfill numero_pedido para pedidos existentes
"""
import psycopg2

conn = psycopg2.connect(
    host="31.97.43.150", port=5433, dbname="MasErp",
    user="postgres", password="Mas=2025", connect_timeout=10
)
conn.autocommit = True
cur = conn.cursor()

pasos = [
    (
        "numero_pedido en pedidos",
        """
        ALTER TABLE pedidos
            ADD COLUMN IF NOT EXISTS numero_pedido VARCHAR(20)
        """,
    ),
    (
        "turno_id en pedido_pagos",
        """
        ALTER TABLE pedido_pagos
            ADD COLUMN IF NOT EXISTS turno_id INT REFERENCES turnos_caja(id)
        """,
    ),
    (
        "referencia_pos en pedido_pagos",
        """
        ALTER TABLE pedido_pagos
            ADD COLUMN IF NOT EXISTS referencia_pos VARCHAR(100)
        """,
    ),
    (
        "ultimos_4 en pedido_pagos",
        """
        ALTER TABLE pedido_pagos
            ADD COLUMN IF NOT EXISTS ultimos_4 VARCHAR(4)
        """,
    ),
    (
        "backfill numero_pedido",
        """
        UPDATE pedidos
        SET numero_pedido = 'P-' || LPAD(id::TEXT, 6, '0')
        WHERE numero_pedido IS NULL
        """,
    ),
]

for nombre, sql in pasos:
    cur.execute(sql)
    print(f"  {nombre} OK")

cur.close()
conn.close()
print("Migración POS + Caja completada.")
