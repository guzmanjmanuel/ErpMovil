# CLAUDE.md — Sistema de Facturación Multi-Tenant + Restaurante

Este archivo le indica a Claude Code cómo debe generar código para este proyecto.
Lee este archivo completo antes de escribir cualquier línea de código.

---

## 1. CONTEXTO DEL SISTEMA

Eres el asistente de desarrollo de un **sistema multi-tenant** que sirve como:
1. **Proveedor de facturación electrónica** (DTE El Salvador — Ministerio de Hacienda)
2. **POS para restaurantes** (salón, delivery, pickup)

El sistema corre sobre **PostgreSQL** con Row Level Security (RLS).
Cada empresa cliente es un "tenant". El aislamiento de datos es crítico.

---

## 2. STACK TECNOLÓGICO

```
Backend:    Node.js + TypeScript + Fastify
ORM:        Kysely  (query builder tipado — NO usar Prisma ni TypeORM)
Base datos: PostgreSQL 15+  con RLS habilitado
Auth:       JWT (access token 15min + refresh token 7 días)
Caché:      Redis  (sesiones, permisos, rate limiting)
Validación: Zod
Testing:    Vitest
```

**Regla de stack:** Si el usuario no especifica alternativa, usa siempre este stack.
No sugerir ni usar Express, Sequelize, Drizzle, Mongoose ni ningún otro a menos que el usuario lo pida explícitamente.

---

## 3. ESTRUCTURA DE CARPETAS

```
src/
├── modules/              ← Un módulo por dominio
│   ├── auth/
│   │   ├── auth.routes.ts
│   │   ├── auth.service.ts
│   │   ├── auth.schema.ts    ← Zod schemas
│   │   └── auth.types.ts
│   ├── usuarios/
│   ├── pedidos/
│   ├── dte/
│   ├── caja/
│   └── restaurante/
├── db/
│   ├── client.ts             ← Instancia de Kysely
│   ├── types.ts              ← Tipos inferidos de la DB
│   └── migrations/
├── middleware/
│   ├── auth.middleware.ts     ← Verificar JWT + set_tenant()
│   ├── permisos.middleware.ts ← Verificar permiso por ruta
│   └── turno.middleware.ts    ← Verificar turno abierto
├── lib/
│   ├── redis.ts
│   ├── jwt.ts
│   └── password.ts
└── app.ts
```

---

## 4. BASE DE DATOS — REGLAS CRÍTICAS

### 4.1 Activar el tenant en CADA transacción

**SIEMPRE** la primera línea de cualquier transacción o query debe activar el tenant:

```typescript
// ✅ CORRECTO — siempre al inicio
await db.transaction().execute(async (trx) => {
  await trx.executeQuery(
    sql`SELECT set_tenant(${tenantId})`.compile(trx)
  );
  // resto de queries...
});

// ❌ INCORRECTO — nunca hacer queries sin set_tenant
const pedidos = await db.selectFrom('pedidos').selectAll().execute();
```

### 4.2 El tenant_id siempre viene del JWT, nunca del body

```typescript
// ✅ CORRECTO
const tenantId = request.user.tenantId; // del JWT verificado

// ❌ INCORRECTO — nunca confiar en el body
const tenantId = request.body.tenantId;
```

### 4.3 Kysely — patrones obligatorios

```typescript
// Selects con tipos explícitos
const pedido = await db
  .selectFrom('pedidos')
  .select(['id', 'estado', 'total', 'canal'])
  .where('id', '=', pedidoId)
  .executeTakeFirstOrThrow();

// Inserts siempre con returning
const nuevo = await db
  .insertInto('pedidos')
  .values({ tenant_id: tenantId, canal: 'salon', ...datos })
  .returningAll()
  .executeTakeFirstOrThrow();

// Updates con optimistic locking cuando sea crítico
await db
  .updateTable('pedidos')
  .set({ estado: 'cerrado', updated_at: new Date() })
  .where('id', '=', pedidoId)
  .where('estado', '=', 'entregado') // estado previo esperado
  .executeTakeFirstOrThrow();
```

---

## 5. AUTENTICACIÓN — REGLAS

### 5.1 Flujo de login

```
POST /auth/login
  → Verificar email + password (bcrypt, 12 rounds)
  → Verificar usuario activo y no bloqueado
  → Registrar acceso_log (login_ok o login_fallido)
  → Si login_ok:
      - Cargar permisos con permisos_usuario(userId, tenantId)
      - Guardar permisos en Redis (TTL 15min, key: perms:{userId}:{tenantId})
      - Generar access_token JWT (15min)
      - Generar refresh_token JWT (7 días)
      - Guardar refresh_token hash en tabla sesiones
      - Devolver { accessToken, refreshToken, usuario, permisos }
```

### 5.2 Estructura del JWT payload

```typescript
interface JWTPayload {
  sub: number;          // usuario_id
  tenantId: number;     // tenant_id activo
  rolId: number;
  rolNivel: number;     // 1=superadmin, 5=admin, 10=cajero...
  establecimientoId: number | null;
  esSuperadmin: boolean;
  sessionId: number;    // id en tabla sesiones
  iat: number;
  exp: number;
}
```

### 5.3 Middleware de autenticación — siempre en este orden

```typescript
// 1. Verificar JWT
// 2. Verificar que la sesión esté activa en DB (no revocada)
// 3. Llamar set_tenant() en la conexión
// 4. Adjuntar user al request
fastify.addHook('onRequest', authMiddleware);
```

### 5.4 Refresh token

```
POST /auth/refresh
  → Verificar refresh_token JWT
  → Buscar en tabla sesiones por token_hash
  → Verificar que esté activa y no expirada
  → Generar nuevo access_token
  → NO rotar refresh_token (solo rotarlo si es política del negocio)
```

### 5.5 Seguridad obligatoria

- Passwords: `bcrypt` con 12 rounds mínimo. Nunca SHA o MD5.
- JWT secret: mínimo 256 bits, desde variable de entorno.
- Rate limiting en `/auth/login`: máximo 10 intentos por IP en 15 minutos (Redis).
- Después de 5 intentos fallidos por usuario: bloquear 15 minutos (ya manejado por trigger DB).
- Nunca devolver información de si el email existe o no (mensaje genérico).
- Tokens de refresh: guardar solo el hash (SHA-256), nunca el valor raw.

---

## 6. PERMISOS — CÓMO PROTEGER RUTAS

### 6.1 Middleware de permisos

```typescript
// Uso en routes
fastify.post('/pedidos',
  {
    preHandler: [
      authMiddleware,
      requirePermiso('pedidos:crear'),
      // Si la acción requiere turno abierto:
      // requireTurno()
    ]
  },
  pedidoController.crear
);
```

### 6.2 Lógica del middleware

```typescript
// Los permisos vienen cacheados en Redis desde el login
// Solo consultar DB si el caché expiró
async function requirePermiso(clave: string) {
  return async (request, reply) => {
    const permisos = await getPermisosFromCache(
      request.user.sub,
      request.user.tenantId
    );
    if (!permisos.includes(clave)) {
      return reply.code(403).send({ error: 'Sin permiso: ' + clave });
    }
  };
}
```

### 6.3 Restricción por establecimiento

```typescript
// En cualquier query que filtre por establecimiento:
if (user.establecimientoId !== null) {
  query = query.where('establecimiento_id', '=', user.establecimientoId);
}
```

---

## 7. MANEJO DE ERRORES

### 7.1 Formato de error estándar

```typescript
// Todos los errores deben seguir este formato
interface ErrorResponse {
  error: string;          // Mensaje legible para el usuario
  code: string;           // Código interno: 'PERMISO_DENEGADO', 'TURNO_CERRADO'
  details?: unknown;      // Solo en desarrollo
}
```

### 7.2 Errores de negocio — usar clases tipadas

```typescript
// Definir en src/lib/errors.ts
export class PermisoError extends Error {
  code = 'PERMISO_DENEGADO';
  statusCode = 403;
}
export class TurnoError extends Error {
  code = 'TURNO_CERRADO';
  statusCode = 409;
}
export class TenantError extends Error {
  code = 'TENANT_INACTIVO';
  statusCode = 403;
}
export class NotFoundError extends Error {
  code = 'NO_ENCONTRADO';
  statusCode = 404;
}
```

### 7.3 Nunca exponer stack traces en producción

```typescript
// En el error handler global de Fastify:
const isDev = process.env.NODE_ENV === 'development';
reply.send({
  error: err.message,
  code: err.code ?? 'ERROR_INTERNO',
  details: isDev ? err.stack : undefined
});
```

---

## 8. ESQUEMA DE RESPUESTAS API

### 8.1 Respuesta exitosa con datos

```typescript
// GET /pedidos/:id
{
  "data": { ...pedido },
  "meta": null
}

// GET /pedidos (lista paginada)
{
  "data": [...pedidos],
  "meta": {
    "total": 150,
    "pagina": 1,
    "porPagina": 20,
    "totalPaginas": 8
  }
}
```

### 8.2 Respuesta de creación

```typescript
// POST /pedidos → 201 Created
{
  "data": { ...pedidoCreado },
  "meta": null
}
```

---

## 9. VARIABLES DE ENTORNO

El código debe leer estas variables. Nunca hardcodear valores:

```env
# Base de datos
DATABASE_URL=postgresql://app_dte:password@localhost:5432/dte_db
DATABASE_POOL_MIN=2
DATABASE_POOL_MAX=10

# JWT
JWT_SECRET=...                    # mínimo 64 chars
JWT_REFRESH_SECRET=...            # diferente al access secret
JWT_ACCESS_EXPIRES=15m
JWT_REFRESH_EXPIRES=7d

# Redis
REDIS_URL=redis://localhost:6379

# Entorno
NODE_ENV=development|production
PORT=3000

# MH (Ministerio de Hacienda)
MH_URL_PRUEBAS=https://apitest.dtes.mh.gob.sv
MH_URL_PRODUCCION=https://api.dtes.mh.gob.sv
```

---

## 10. CONVENCIONES DE CÓDIGO

### 10.1 Nombrado

```typescript
// Archivos:        kebab-case       → auth.service.ts
// Clases:          PascalCase       → AuthService
// Funciones:       camelCase        → verificarPassword()
// Variables:       camelCase        → tenantId
// Constantes:      UPPER_SNAKE      → JWT_SECRET
// Tablas DB:       snake_case       → pedido_items
// Columnas DB:     snake_case       → fecha_emision
// Rutas API:       kebab-case       → /pedido-items
```

### 10.2 Async/await — nunca callbacks ni .then()

```typescript
// ✅ CORRECTO
const usuario = await usuarioService.findById(id);

// ❌ INCORRECTO
usuarioService.findById(id).then(usuario => { ... });
```

### 10.3 Validación con Zod — siempre en el schema del módulo

```typescript
// auth.schema.ts
export const LoginSchema = z.object({
  email:    z.string().email(),
  password: z.string().min(8).max(100),
  tenantId: z.number().int().positive()
});

export type LoginInput = z.infer<typeof LoginSchema>;
```

### 10.4 Tipos de DB — generar con Kysely

```typescript
// db/types.ts — generado con kysely-codegen
// Usar estos tipos en todos los servicios
import type { DB } from '../db/types';
```

---

## 11. SEGURIDAD — CHECKLIST OBLIGATORIO

Antes de generar cualquier endpoint verifica:

- [ ] ¿El endpoint requiere `authMiddleware`?
- [ ] ¿Requiere un permiso específico (`requirePermiso`)?
- [ ] ¿El `tenant_id` viene del JWT, no del body?
- [ ] ¿Se llama `set_tenant()` antes de cualquier query?
- [ ] ¿Los inputs pasan por validación Zod?
- [ ] ¿Se filtran resultados por `establecimiento_id` si el usuario tiene restricción?
- [ ] ¿Los errores no exponen información sensible?
- [ ] ¿Las acciones de caja verifican turno abierto?

---

## 12. LO QUE NUNCA DEBES HACER

- ❌ Nunca usar `SELECT *` en producción — siempre seleccionar columnas específicas
- ❌ Nunca guardar passwords en texto plano ni en JWT
- ❌ Nunca hacer queries sin haber llamado `set_tenant()` primero
- ❌ Nunca devolver el campo `password_hash` en ninguna respuesta
- ❌ Nunca confiar en `tenant_id` o `usuario_id` que vengan del request body
- ❌ Nunca deshabilitar RLS con `SET row_security = off` en código de la app
- ❌ Nunca usar `console.log` en producción — usar el logger de Fastify (`request.log`)
- ❌ Nunca hacer N+1 queries — usar JOINs o cargar relaciones en una sola query
- ❌ Nunca manejar el certificado de firma (.p12) sin encriptar

---

## 13. EJEMPLO DE ENDPOINT COMPLETO

Cuando generes un endpoint, sigue exactamente esta estructura:

```typescript
// modules/pedidos/pedidos.routes.ts
import { FastifyInstance } from 'fastify';
import { authMiddleware } from '../../middleware/auth.middleware';
import { requirePermiso } from '../../middleware/permisos.middleware';
import { requireTurno } from '../../middleware/turno.middleware';
import { CrearPedidoSchema } from './pedidos.schema';
import { PedidosService } from './pedidos.service';

export async function pedidosRoutes(fastify: FastifyInstance) {
  const service = new PedidosService(fastify.db);

  fastify.post('/', {
    preHandler: [
      authMiddleware,
      requirePermiso('pedidos:crear'),
      requireTurno(),  // solo si la acción requiere turno
    ],
    schema: {
      body: CrearPedidoSchema,  // Zod → JSON Schema para Fastify
    }
  }, async (request, reply) => {
    const input = CrearPedidoSchema.parse(request.body);
    const pedido = await service.crear(
      request.user.tenantId,
      request.user.sub,
      input
    );
    return reply.code(201).send({ data: pedido, meta: null });
  });
}

// modules/pedidos/pedidos.service.ts
import { Kysely, sql } from 'kysely';
import type { DB } from '../../db/types';
import type { CrearPedidoInput } from './pedidos.schema';

export class PedidosService {
  constructor(private db: Kysely<DB>) {}

  async crear(tenantId: number, usuarioId: number, input: CrearPedidoInput) {
    return this.db.transaction().execute(async (trx) => {
      // SIEMPRE primero
      await sql`SELECT set_tenant(${tenantId})`.execute(trx);

      const pedido = await trx
        .insertInto('pedidos')
        .values({
          tenant_id:  tenantId,
          usuario_id: usuarioId,
          canal:      input.canal,
          mesa_id:    input.mesaId ?? null,
          estado:     'borrador',
        })
        .returning(['id', 'numero_pedido', 'canal', 'estado', 'created_at'])
        .executeTakeFirstOrThrow();

      return pedido;
    });
  }
}
```

---

## 14. FLUJO DE LOGIN — IMPLEMENTACIÓN ESPERADA

Cuando se pida implementar el login, genera exactamente:

```
POST /auth/login
  Body: { email, password, tenantId }

  1. Validar con Zod
  2. Buscar usuario por email (sin filtrar activo aún)
  3. Si no existe → error genérico (no revelar)
  4. Si bloqueado_hasta > NOW() → error con tiempo restante
  5. Verificar bcrypt(password, password_hash)
  6. Si falla → incrementar intentos (trigger lo hace) → error genérico
  7. Verificar usuario.activo = true
  8. Verificar tenant_usuarios donde tenant_id y activo
  9. Cargar permisos con función permisos_usuario()
  10. Cachear permisos en Redis TTL 15min
  11. Generar accessToken (JWT, 15min)
  12. Generar refreshToken (JWT, 7d)
  13. Guardar hash del refreshToken en tabla sesiones
  14. Insertar en acceso_log { accion: 'login_ok' }
  15. Retornar:
      {
        data: {
          accessToken,
          refreshToken,
          usuario: { id, nombre, email, rol, establecimientoId },
          permisos: ['pedidos:crear', 'caja:abrir', ...]
        }
      }

POST /auth/logout
  1. Marcar sesión como inactiva (activa = false)
  2. Eliminar permisos del caché Redis
  3. Insertar en acceso_log { accion: 'logout' }
  4. Retornar 204 No Content

POST /auth/refresh
  1. Verificar refreshToken JWT
  2. Buscar sesión por hash del token
  3. Verificar activa = true y expira_en > NOW()
  4. Generar nuevo accessToken
  5. Actualizar sesion.ultimo_uso
  6. Retornar { data: { accessToken } }
```