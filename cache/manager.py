"""
Cache en memoria de dos capas:

Capa 1 — GlobalCache:  catálogos estáticos (CAT-011, CAT-014, departamentos, municipios,
                        actividades). TTL 24h. Compartido entre todos los tenants.
                        Se invalida manualmente cuando un admin edita un catálogo.

Capa 2 — TenantCache:  datos específicos de un tenant (listas_precio, categorías,
                        precios por producto). TTL 5 min. Se invalida en mutaciones
                        (POST/PATCH/DELETE) automáticamente.

Ambas capas son thread-safe (TTLCache con RLock).
"""

import threading
import time
import logging

logger = logging.getLogger("cache")


class TTLCache:
    """
    Cache simple con TTL, thread-safe.
    No usa cachetools para evitar dependencias externas, aunque cachetools
    está disponible; esta implementación es más fácil de controlar.
    """

    def __init__(self, ttl_seconds: int, name: str = "cache"):
        self._store: dict[str, tuple[object, float]] = {}   # key → (value, expires_at)
        self._ttl = ttl_seconds
        self._lock = threading.RLock()
        self._name = name

    def get(self, key: str):
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: object) -> None:
        with self._lock:
            self._store[key] = (value, time.monotonic() + self._ttl)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def delete_prefix(self, prefix: str) -> int:
        """Elimina todas las claves que empiezan con `prefix`."""
        with self._lock:
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                del self._store[k]
            if keys:
                logger.debug(f"[{self._name}] invalidadas {len(keys)} claves con prefijo '{prefix}'")
            return len(keys)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def stats(self) -> dict:
        with self._lock:
            now = time.monotonic()
            alive = sum(1 for _, (_, exp) in self._store.items() if exp > now)
            return {
                "total_keys": len(self._store),
                "alive_keys": alive,
                "expired_keys": len(self._store) - alive,
                "ttl_seconds": self._ttl,
            }


# ── Instancias globales ────────────────────────────────────────────────────────

# Catálogos estáticos: 24 horas
global_cache = TTLCache(ttl_seconds=86_400, name="global")

# Datos por tenant: 5 minutos
tenant_cache = TTLCache(ttl_seconds=300, name="tenant")


# ── Claves de caché ────────────────────────────────────────────────────────────
#
# Convención:
#   global_cache  →  "cat:tipo_item", "cat:unidades_medida", "cat:departamentos",
#                    "cat:municipios", "cat:actividades"
#
#   tenant_cache  →  "t{tenant_id}:listas_precio"
#                    "t{tenant_id}:categorias"
#                    "t{tenant_id}:precios:{producto_id}"
#                    "t{tenant_id}:stock:{producto_id}"

class CacheKeys:
    # Globales
    TIPO_ITEM       = "cat:tipo_item"
    UNIDADES_MEDIDA = "cat:unidades_medida"
    DEPARTAMENTOS   = "cat:departamentos"
    MUNICIPIOS      = "cat:municipios"      # todos
    ACTIVIDADES     = "cat:actividades"

    @staticmethod
    def municipios_depto(depto: str) -> str:
        return f"cat:municipios:{depto}"

    # Por tenant
    @staticmethod
    def listas_precio(tenant_id: int) -> str:
        return f"t{tenant_id}:listas_precio"

    @staticmethod
    def categorias(tenant_id: int) -> str:
        return f"t{tenant_id}:categorias"

    @staticmethod
    def precios_producto(tenant_id: int, producto_id: int) -> str:
        return f"t{tenant_id}:precios:{producto_id}"

    @staticmethod
    def stock_producto(tenant_id: int, producto_id: int) -> str:
        return f"t{tenant_id}:stock:{producto_id}"


# ── Helpers de invalidación ────────────────────────────────────────────────────

def invalidar_listas_precio(tenant_id: int) -> None:
    tenant_cache.delete(CacheKeys.listas_precio(tenant_id))

def invalidar_categorias(tenant_id: int) -> None:
    tenant_cache.delete(CacheKeys.categorias(tenant_id))

def invalidar_precios_producto(tenant_id: int, producto_id: int | None = None) -> None:
    if producto_id is not None:
        tenant_cache.delete(CacheKeys.precios_producto(tenant_id, producto_id))
    else:
        # Invalida todos los precios del tenant
        tenant_cache.delete_prefix(f"t{tenant_id}:precios:")

def invalidar_tenant(tenant_id: int) -> None:
    """Invalida TODO el cache de un tenant (útil en operaciones masivas)."""
    tenant_cache.delete_prefix(f"t{tenant_id}:")

def invalidar_catalogo(key: str) -> None:
    """Invalida un catálogo global (útil si un admin edita el catálogo)."""
    global_cache.delete(key)
    # También invalidar variantes (ej. municipios por departamento)
    if key == CacheKeys.MUNICIPIOS:
        global_cache.delete_prefix("cat:municipios:")
