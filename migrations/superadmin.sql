-- Migración: soporte para superusuario global
-- Ejecutar una sola vez contra la base de datos

-- 1. Agregar columna is_superadmin a la tabla usuarios
ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS is_superadmin BOOLEAN NOT NULL DEFAULT FALSE;

-- 2. Agregar rol 'superadmin' al catálogo de roles (si existe la tabla)
INSERT INTO roles (nombre, descripcion, tipo_negocio, activo)
VALUES ('superadmin', 'Superusuario con acceso total a todos los negocios', 'ambos', true)
ON CONFLICT (nombre) DO NOTHING;

-- 3. Crear el primer superusuario
--    IMPORTANTE: cambiar el hash por uno generado con bcrypt rounds=12
--    Para generar el hash en Python:
--        import bcrypt
--        print(bcrypt.hashpw(b"TuPasswordAqui", bcrypt.gensalt(12)).decode())
INSERT INTO usuarios (email, password_hash, nombre, activo, is_superadmin)
VALUES (
    'superadmin@erpmovil.com',
    '$2b$12$REEMPLAZAR_CON_HASH_REAL',
    'Super Administrador',
    true,
    true
)
ON CONFLICT (email) DO UPDATE SET is_superadmin = true;
