from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP

from routers import auth, menu, mesas, pedidos, caja, kds, facturacion, clientes, usuarios, tenants, establecimientos, catalogos, productos, inventario

app = FastAPI(
    title="ErpMovil API",
    description="Backend POS multitenant para restaurantes con DTE (El Salvador)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tenants.router)
app.include_router(menu.router)
app.include_router(mesas.router)
app.include_router(pedidos.router)
app.include_router(caja.router)
app.include_router(kds.router)
app.include_router(clientes.router)
app.include_router(facturacion.router)
app.include_router(usuarios.router)
app.include_router(establecimientos.router)
app.include_router(catalogos.router)
app.include_router(productos.router)
app.include_router(inventario.router)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "app": "ErpMovil API v1.0"}


# MCP server derivado de la app FastAPI
mcp = FastMCP.from_fastapi(app, name="ErpMovil")

if __name__ == "__main__":
    mcp.run()
