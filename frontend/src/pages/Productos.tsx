import { useEffect, useState, useRef, type FormEvent, type ChangeEvent } from 'react'
import * as XLSX from 'xlsx'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

// ── Tipos ─────────────────────────────────────────────────────────────────────

interface Producto {
  id: number
  codigo: string
  nombre: string
  descripcion: string | null
  categoria_id: number | null
  tipo_item: number
  unidad_medida_id: number
  usa_lotes: boolean
  usa_vencimiento: boolean
  metodo_costo: string
  stock_minimo: string | null
  stock_maximo: string | null
  precio_venta: string | null
  costo_referencia: string | null
  exento: boolean
  no_sujeto: boolean
  activo: boolean
  created_at: string
  updated_at: string
}

interface Categoria  { id: number; nombre: string; padre_id: number | null }
interface TipoItem   { codigo: number; descripcion: string }
interface UnidadMed  { codigo: number; descripcion: string }

interface FilaImport {
  _fila: number
  codigo: string
  nombre: string
  descripcion?: string
  categoria_id?: number | null
  _cat_nombre?: string       // nombre legible para preview
  tipo_item: number
  unidad_medida_id: number
  metodo_costo: string
  precio_venta?: number
  costo_referencia?: number
  stock_minimo?: number
  stock_maximo?: number
  exento: boolean
  no_sujeto: boolean
  usa_lotes: boolean
  usa_vencimiento: boolean
  codigo_barra?: string
  tipo_barra: string
  _error?: string
  _warn?: string             // advertencia no bloqueante (ej: categoría no encontrada)
}

const METODOS = ['PROMEDIO', 'FIFO', 'LIFO']

// ── Página principal ──────────────────────────────────────────────────────────

export default function Productos() {
  const { user } = useAuth()
  const tenantId = user?.tenant_id

  const [productos, setProductos]     = useState<Producto[]>([])
  const [categorias, setCategorias]   = useState<Categoria[]>([])
  const [tiposItem, setTiposItem]     = useState<TipoItem[]>([])
  const [unidades, setUnidades]       = useState<UnidadMed[]>([])
  const [loading, setLoading]         = useState(true)
  const [buscar, setBuscar]           = useState('')
  const [filtroTipo, setFiltroTipo]   = useState('')
  const [editando, setEditando]       = useState<Producto | null>(null)
  const [showForm, setShowForm]       = useState(false)
  const [showCategorias, setShowCategorias] = useState(false)
  const [showImport, setShowImport]   = useState(false)
  const [filasImport, setFilasImport] = useState<FilaImport[]>([])
  const [importando, setImportando]   = useState(false)
  const [importResult, setImportResult] = useState<{ importados: number; omitidos: number; errores: string[] } | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  async function reloadCategorias() {
    if (!tenantId) return
    const cats = await api.get<Categoria[]>(`/tenants/${tenantId}/categorias-producto`)
    setCategorias(cats)
  }

  async function reload(q?: string) {
    if (!tenantId) return
    setLoading(true)
    let path = `/tenants/${tenantId}/productos`
    const params: string[] = []
    if (q) params.push(`buscar=${encodeURIComponent(q)}`)
    if (filtroTipo) params.push(`tipo_item=${filtroTipo}`)
    if (params.length) path += '?' + params.join('&')
    const data = await api.get<Producto[]>(path)
    setProductos(data)
    setLoading(false)
  }

  useEffect(() => {
    if (!tenantId) return
    Promise.all([
      api.get<Categoria[]>(`/tenants/${tenantId}/categorias-producto`),
      api.get<TipoItem[]>('/catalogos/tipos-item'),
      api.get<UnidadMed[]>('/catalogos/unidades-medida'),
    ]).then(([cats, tipos, uds]) => {
      setCategorias(cats)
      setTiposItem(tipos)
      setUnidades(uds)
    })
  }, [tenantId])

  useEffect(() => { reload() }, [tenantId, filtroTipo])

  function handleSearch(e: FormEvent) { e.preventDefault(); reload(buscar) }

  async function handleDesactivar(p: Producto) {
    if (!confirm(`¿Desactivar "${p.nombre}"?`)) return
    await api.delete(`/tenants/${tenantId}/productos/${p.id}`)
    reload(buscar || undefined)
  }

  // ── Excel: plantilla de descarga ─────────────────────────────────────────────
  function descargarPlantilla() {
    const headers = [
      'codigo', 'nombre', 'descripcion',
      'categoria', 'sub_categoria',
      'tipo_item', 'unidad_medida_id', 'metodo_costo',
      'precio_venta', 'costo_referencia', 'stock_minimo', 'stock_maximo',
      'exento', 'no_sujeto', 'usa_lotes', 'usa_vencimiento',
      'codigo_barra', 'tipo_barra',
    ]

    // Determinar ejemplo de categoría tomando la primera disponible
    const raices = categorias.filter(c => c.padre_id === null)
    const ejCat    = raices[0]?.nombre ?? 'Bebidas'
    const ejSubCat = categorias.find(c => c.padre_id === raices[0]?.id)?.nombre ?? 'Agua'

    const ejemplo = [
      'PROD-001', 'Agua purificada 500ml', 'Botella de agua purificada 500ml',
      ejCat, ejSubCat,
      1, 36, 'PROMEDIO',
      0.75, 0.40, 50, 1000,
      'NO', 'NO', 'NO', 'NO',
      '7501234567890', 'EAN13',
    ]

    const instrucciones = [
      ['Campo', 'Descripción', 'Valores válidos'],
      ['codigo', 'Código único del producto', 'Texto (requerido)'],
      ['nombre', 'Nombre del producto', 'Texto (requerido)'],
      ['descripcion', 'Descripción opcional', 'Texto'],
      ['categoria', 'Nombre exacto de la categoría principal', 'Ver hoja Categorías'],
      ['sub_categoria', 'Nombre exacto de la sub-categoría', 'Ver hoja Categorías'],
      ['tipo_item', 'Tipo de ítem CAT-011', '1=Bienes | 2=Servicios | 3=Ambos | 4=Otros tributos'],
      ['unidad_medida_id', 'Unidad de medida CAT-014', '25=Botella | 26=Kg | 27=Lb | 36=Unidad | 41=Hora | 53=Servicio'],
      ['metodo_costo', 'Método de costeo', 'PROMEDIO | FIFO | LIFO'],
      ['precio_venta', 'Precio de venta (USD)', 'Número decimal (ej: 1.50)'],
      ['costo_referencia', 'Costo de referencia (USD)', 'Número decimal'],
      ['stock_minimo', 'Stock mínimo', 'Número'],
      ['stock_maximo', 'Stock máximo', 'Número'],
      ['exento', 'Exento de IVA', 'SI | NO'],
      ['no_sujeto', 'No sujeto a IVA', 'SI | NO'],
      ['usa_lotes', 'Maneja lotes/batches', 'SI | NO'],
      ['usa_vencimiento', 'Tiene fecha de vencimiento', 'SI | NO'],
      ['codigo_barra', 'Código de barras', 'Texto'],
      ['tipo_barra', 'Tipo de código de barras', 'EAN13 | UPC | QR | INTERNO'],
    ]

    const wb = XLSX.utils.book_new()

    // Hoja Productos
    const ws = XLSX.utils.aoa_to_sheet([headers, ejemplo])
    ws['!cols'] = headers.map(h => ({ wch: ['descripcion', 'categoria', 'sub_categoria'].includes(h) ? 28 : 20 }))
    XLSX.utils.book_append_sheet(wb, ws, 'Productos')

    // Hoja Categorías — listado para referencia
    const catHeaders = ['categoria', 'sub_categoria']
    const catRows: string[][] = []
    for (const raiz of raices) {
      const subs = categorias.filter(c => c.padre_id === raiz.id)
      if (subs.length === 0) {
        catRows.push([raiz.nombre, ''])
      } else {
        for (const sub of subs) {
          catRows.push([raiz.nombre, sub.nombre])
        }
      }
    }
    if (catRows.length === 0) catRows.push(['(Sin categorías registradas — créalas primero)', ''])
    const wsCat = XLSX.utils.aoa_to_sheet([catHeaders, ...catRows])
    wsCat['!cols'] = [{ wch: 30 }, { wch: 30 }]
    XLSX.utils.book_append_sheet(wb, wsCat, 'Categorías')

    // Hoja Instrucciones
    const wsInfo = XLSX.utils.aoa_to_sheet(instrucciones)
    wsInfo['!cols'] = [{ wch: 22 }, { wch: 40 }, { wch: 50 }]
    XLSX.utils.book_append_sheet(wb, wsInfo, 'Instrucciones')

    XLSX.writeFile(wb, 'plantilla_productos.xlsx')
  }

  // ── Excel: leer archivo ───────────────────────────────────────────────────────
  function leerExcel(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      const data = new Uint8Array(ev.target!.result as ArrayBuffer)
      const wb = XLSX.read(data, { type: 'array' })
      const ws = wb.Sheets[wb.SheetNames[0]]
      const rows: Record<string, unknown>[] = XLSX.utils.sheet_to_json(ws, { defval: '' })

      function boolCol(v: unknown): boolean {
        return String(v).trim().toUpperCase() === 'SI' || v === true || v === 1
      }
      function numCol(v: unknown): number | undefined {
        const n = parseFloat(String(v))
        return isNaN(n) ? undefined : n
      }

      // Función para resolver categoria_id por nombre de categoría y sub-categoría
      function resolverCategoria(catNombre: string, subNombre: string): {
        categoria_id: number | null
        _cat_nombre: string
        _warn?: string
      } {
        const cat = catNombre.trim()
        const sub = subNombre.trim()
        if (!cat && !sub) return { categoria_id: null, _cat_nombre: '' }

        // Buscar sub-categoría primero (más específico)
        if (sub) {
          const raiz = categorias.find(c => c.padre_id === null && c.nombre.toLowerCase() === cat.toLowerCase())
          const subCat = categorias.find(c =>
            c.padre_id !== null &&
            c.nombre.toLowerCase() === sub.toLowerCase() &&
            (!raiz || c.padre_id === raiz.id)
          )
          if (subCat) return { categoria_id: subCat.id, _cat_nombre: `${raiz?.nombre ?? cat} > ${subCat.nombre}` }
          return {
            categoria_id: raiz?.id ?? null,
            _cat_nombre: cat + (sub ? ` > ${sub}` : ''),
            _warn: `Sub-categoría "${sub}" no encontrada${raiz ? `, usando "${raiz.nombre}"` : ''}`,
          }
        }

        // Solo categoría raíz
        const raiz = categorias.find(c => c.padre_id === null && c.nombre.toLowerCase() === cat.toLowerCase())
        if (raiz) return { categoria_id: raiz.id, _cat_nombre: raiz.nombre }
        return { categoria_id: null, _cat_nombre: cat, _warn: `Categoría "${cat}" no encontrada` }
      }

      const filas: FilaImport[] = rows.map((row, i) => {
        const codigo = String(row['codigo'] ?? '').trim()
        const nombre = String(row['nombre'] ?? '').trim()
        let _error: string | undefined
        if (!codigo) _error = 'Código vacío'
        else if (!nombre) _error = 'Nombre vacío'

        const { categoria_id, _cat_nombre, _warn } = resolverCategoria(
          String(row['categoria'] ?? ''),
          String(row['sub_categoria'] ?? ''),
        )

        return {
          _fila: i + 2,
          codigo,
          nombre,
          descripcion: String(row['descripcion'] ?? '').trim() || undefined,
          categoria_id,
          _cat_nombre,
          tipo_item: parseInt(String(row['tipo_item'] ?? '1')) || 1,
          unidad_medida_id: parseInt(String(row['unidad_medida_id'] ?? '36')) || 36,
          metodo_costo: ['FIFO', 'LIFO', 'PROMEDIO'].includes(String(row['metodo_costo']).toUpperCase())
            ? String(row['metodo_costo']).toUpperCase()
            : 'PROMEDIO',
          precio_venta: numCol(row['precio_venta']),
          costo_referencia: numCol(row['costo_referencia']),
          stock_minimo: numCol(row['stock_minimo']),
          stock_maximo: numCol(row['stock_maximo']),
          exento: boolCol(row['exento']),
          no_sujeto: boolCol(row['no_sujeto']),
          usa_lotes: boolCol(row['usa_lotes']),
          usa_vencimiento: boolCol(row['usa_vencimiento']),
          codigo_barra: String(row['codigo_barra'] ?? '').trim() || undefined,
          tipo_barra: String(row['tipo_barra'] ?? 'EAN13').trim() || 'EAN13',
          _error,
          _warn,
        }
      })
      setFilasImport(filas)
      setImportResult(null)
      setShowImport(true)
    }
    reader.readAsArrayBuffer(file)
    e.target.value = ''
  }

  async function confirmarImport() {
    const validas = filasImport.filter(f => !f._error)
    if (!validas.length) return
    setImportando(true)
    try {
      const result = await api.post<{ importados: number; omitidos: number; errores: string[] }>(
        `/tenants/${tenantId}/productos/importar`,
        validas.map(({ _fila: _, _error: __, _cat_nombre: ___, _warn: ____, ...rest }) => rest),
      )
      setImportResult(result)
      reload()
    } finally {
      setImportando(false)
    }
  }

  // ── Helpers UI ────────────────────────────────────────────────────────────────
  function labelTipo(codigo: number) {
    return tiposItem.find(t => t.codigo === codigo)?.descripcion ?? `Tipo ${codigo}`
  }
  function labelUnidad(codigo: number) {
    return unidades.find(u => u.codigo === codigo)?.descripcion ?? `UM ${codigo}`
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-800">Productos</h2>
          <p className="text-xs text-gray-500 mt-0.5">Catálogo de productos y servicios</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowCategorias(true)} className="btn-secondary text-xs">
            Categorías
          </button>
          <button onClick={descargarPlantilla} className="btn-secondary text-xs">
            Plantilla Excel
          </button>
          <label className="btn-secondary text-xs cursor-pointer">
            Importar Excel
            <input ref={fileRef} type="file" accept=".xlsx,.xls" className="hidden" onChange={leerExcel} />
          </label>
          <button onClick={() => { setEditando(null); setShowForm(true) }} className="btn-primary">
            + Nuevo producto
          </button>
        </div>
      </div>

      {/* Filtros */}
      <div className="flex gap-2 mb-5">
        <form onSubmit={handleSearch} className="flex gap-2 flex-1">
          <input
            value={buscar}
            onChange={e => setBuscar(e.target.value)}
            placeholder="Buscar por nombre o código..."
            className="input flex-1 max-w-sm"
          />
          <button type="submit" className="btn-primary">Buscar</button>
          {buscar && (
            <button type="button" onClick={() => { setBuscar(''); reload() }} className="btn-secondary">
              Limpiar
            </button>
          )}
        </form>
        <select
          value={filtroTipo}
          onChange={e => setFiltroTipo(e.target.value)}
          className="input w-48"
        >
          <option value="">Todos los tipos</option>
          {tiposItem.map(t => (
            <option key={t.codigo} value={t.codigo}>{t.descripcion}</option>
          ))}
        </select>
      </div>

      {/* Tabla */}
      {loading ? (
        <p className="text-gray-400 text-sm">Cargando...</p>
      ) : productos.length === 0 ? (
        <div className="py-16 text-center text-gray-400">
          <p className="text-4xl mb-3">📦</p>
          <p className="font-medium">Sin productos registrados</p>
          <p className="text-sm mt-1">Agrega productos manualmente o importa desde Excel</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-4 py-3 text-left">Código</th>
                <th className="px-4 py-3 text-left">Nombre</th>
                <th className="px-4 py-3 text-left">Tipo</th>
                <th className="px-4 py-3 text-left">Unidad</th>
                <th className="px-4 py-3 text-right">Precio venta</th>
                <th className="px-4 py-3 text-center">Costo</th>
                <th className="px-4 py-3 text-center">Lotes</th>
                <th className="px-4 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {productos.map(p => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{p.codigo}</td>
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-800">{p.nombre}</p>
                    {p.descripcion && <p className="text-xs text-gray-400 truncate max-w-xs">{p.descripcion}</p>}
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 font-medium">
                      {labelTipo(p.tipo_item)}
                    </span>
                    {p.exento && <span className="ml-1 text-xs px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-700">Exento</span>}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">{labelUnidad(p.unidad_medida_id)}</td>
                  <td className="px-4 py-3 text-right font-mono text-sm">
                    {p.precio_venta ? `$${parseFloat(p.precio_venta).toFixed(2)}` : <span className="text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">{p.metodo_costo}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {p.usa_lotes
                      ? <span className="text-xs text-green-600 font-medium">Si</span>
                      : <span className="text-xs text-gray-300">No</span>}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => { setEditando(p); setShowForm(true) }}
                        className="text-xs px-2 py-1 bg-indigo-50 text-indigo-700 rounded-lg hover:bg-indigo-100 font-medium"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => handleDesactivar(p)}
                        className="text-xs px-2 py-1 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 font-medium"
                      >
                        Quitar
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal categorías */}
      {showCategorias && (
        <ModalCategorias
          tenantId={tenantId!}
          categorias={categorias}
          onClose={() => setShowCategorias(false)}
          onSave={() => reloadCategorias()}
        />
      )}

      {/* Modal crear/editar */}
      {showForm && (
        <ModalProducto
          tenantId={tenantId!}
          producto={editando}
          categorias={categorias}
          tiposItem={tiposItem}
          unidades={unidades}
          onClose={() => setShowForm(false)}
          onSave={() => { setShowForm(false); reload(buscar || undefined) }}
        />
      )}

      {/* Modal importar */}
      {showImport && (
        <ModalImport
          filas={filasImport}
          importando={importando}
          resultado={importResult}
          onConfirmar={confirmarImport}
          onClose={() => { setShowImport(false); setFilasImport([]) }}
        />
      )}
    </div>
  )
}


// ── Modal Categorías ──────────────────────────────────────────────────────────

function ModalCategorias({
  tenantId, categorias, onClose, onSave,
}: {
  tenantId: number
  categorias: Categoria[]
  onClose: () => void
  onSave: () => void
}) {
  const [lista, setLista]         = useState<Categoria[]>(categorias)
  const [editId, setEditId]       = useState<number | null>(null)
  const [editNombre, setEditNombre] = useState('')
  const [nuevoRaiz, setNuevoRaiz] = useState('')
  const [nuevoSub, setNuevoSub]   = useState<Record<number, string>>({})
  const [saving, setSaving]       = useState(false)

  const raices   = lista.filter(c => c.padre_id === null)
  const subDe    = (id: number) => lista.filter(c => c.padre_id === id)

  async function refrescar() {
    const data = await api.get<Categoria[]>(`/tenants/${tenantId}/categorias-producto`)
    setLista(data)
    onSave()
  }

  async function crearRaiz() {
    if (!nuevoRaiz.trim()) return
    setSaving(true)
    await api.post(`/tenants/${tenantId}/categorias-producto`, { nombre: nuevoRaiz.trim(), padre_id: null })
    setNuevoRaiz('')
    setSaving(false)
    refrescar()
  }

  async function crearSub(padreId: number) {
    const nombre = nuevoSub[padreId]?.trim()
    if (!nombre) return
    setSaving(true)
    await api.post(`/tenants/${tenantId}/categorias-producto`, { nombre, padre_id: padreId })
    setNuevoSub(prev => ({ ...prev, [padreId]: '' }))
    setSaving(false)
    refrescar()
  }

  async function guardarEdicion(cat: Categoria) {
    if (!editNombre.trim()) return
    setSaving(true)
    await api.patch(`/tenants/${tenantId}/categorias-producto/${cat.id}`, {
      nombre: editNombre.trim(), padre_id: cat.padre_id,
    })
    setEditId(null)
    setSaving(false)
    refrescar()
  }

  async function eliminar(cat: Categoria) {
    const msg = subDe(cat.id).length > 0
      ? `¿Eliminar "${cat.nombre}" y desvincular sus ${subDe(cat.id).length} sub-categorías?`
      : `¿Eliminar "${cat.nombre}"?`
    if (!confirm(msg)) return
    await api.delete(`/tenants/${tenantId}/categorias-producto/${cat.id}`)
    refrescar()
  }

  function iniciarEdicion(cat: Categoria) {
    setEditId(cat.id)
    setEditNombre(cat.nombre)
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b">
          <div>
            <h3 className="text-base font-bold text-gray-800">Categorías y sub-categorías</h3>
            <p className="text-xs text-gray-500 mt-0.5">{raices.length} categorías · {lista.length - raices.length} sub-categorías</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl font-bold">✕</button>
        </div>

        {/* Cuerpo scrollable */}
        <div className="flex-1 overflow-y-auto p-5 space-y-3">

          {/* Crear categoría raíz */}
          <div className="flex gap-2">
            <input
              value={nuevoRaiz}
              onChange={e => setNuevoRaiz(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && crearRaiz()}
              placeholder="Nueva categoría principal..."
              className="input flex-1 text-sm"
            />
            <button
              onClick={crearRaiz}
              disabled={saving || !nuevoRaiz.trim()}
              className="btn-primary text-sm px-3 disabled:opacity-40"
            >
              + Agregar
            </button>
          </div>

          {raices.length === 0 && (
            <p className="text-center text-gray-400 text-sm py-8">Sin categorías. Crea la primera arriba.</p>
          )}

          {/* Árbol de categorías */}
          {raices.map(cat => (
            <div key={cat.id} className="border border-gray-200 rounded-xl overflow-hidden">
              {/* Fila categoría raíz */}
              <div className="flex items-center gap-2 px-3 py-2.5 bg-gray-50">
                <svg className="w-4 h-4 text-indigo-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                {editId === cat.id ? (
                  <input
                    autoFocus
                    value={editNombre}
                    onChange={e => setEditNombre(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') guardarEdicion(cat); if (e.key === 'Escape') setEditId(null) }}
                    className="input flex-1 text-sm py-1"
                  />
                ) : (
                  <span className="flex-1 text-sm font-semibold text-gray-800">{cat.nombre}</span>
                )}
                <span className="text-xs text-gray-400 shrink-0">{subDe(cat.id).length} sub</span>
                {editId === cat.id ? (
                  <div className="flex gap-1">
                    <button onClick={() => guardarEdicion(cat)} disabled={saving} className="text-xs px-2 py-1 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-40">Guardar</button>
                    <button onClick={() => setEditId(null)} className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded hover:bg-gray-200">Cancelar</button>
                  </div>
                ) : (
                  <div className="flex gap-1">
                    <button onClick={() => iniciarEdicion(cat)} className="text-xs px-2 py-1 bg-indigo-50 text-indigo-700 rounded hover:bg-indigo-100">Editar</button>
                    <button onClick={() => eliminar(cat)} className="text-xs px-2 py-1 bg-red-50 text-red-600 rounded hover:bg-red-100">Eliminar</button>
                  </div>
                )}
              </div>

              {/* Sub-categorías */}
              <div className="divide-y divide-gray-100">
                {subDe(cat.id).map(sub => (
                  <div key={sub.id} className="flex items-center gap-2 px-3 py-2 pl-8 bg-white">
                    <svg className="w-3.5 h-3.5 text-gray-300 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    {editId === sub.id ? (
                      <input
                        autoFocus
                        value={editNombre}
                        onChange={e => setEditNombre(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') guardarEdicion(sub); if (e.key === 'Escape') setEditId(null) }}
                        className="input flex-1 text-sm py-1"
                      />
                    ) : (
                      <span className="flex-1 text-sm text-gray-700">{sub.nombre}</span>
                    )}
                    {editId === sub.id ? (
                      <div className="flex gap-1">
                        <button onClick={() => guardarEdicion(sub)} disabled={saving} className="text-xs px-2 py-1 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-40">Guardar</button>
                        <button onClick={() => setEditId(null)} className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded hover:bg-gray-200">Cancelar</button>
                      </div>
                    ) : (
                      <div className="flex gap-1">
                        <button onClick={() => iniciarEdicion(sub)} className="text-xs px-2 py-1 bg-indigo-50 text-indigo-700 rounded hover:bg-indigo-100">Editar</button>
                        <button onClick={() => eliminar(sub)} className="text-xs px-2 py-1 bg-red-50 text-red-600 rounded hover:bg-red-100">Eliminar</button>
                      </div>
                    )}
                  </div>
                ))}

                {/* Input nueva sub-categoría */}
                <div className="flex items-center gap-2 px-3 py-2 pl-8 bg-white">
                  <svg className="w-3.5 h-3.5 text-gray-200 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  <input
                    value={nuevoSub[cat.id] ?? ''}
                    onChange={e => setNuevoSub(prev => ({ ...prev, [cat.id]: e.target.value }))}
                    onKeyDown={e => e.key === 'Enter' && crearSub(cat.id)}
                    placeholder="Nueva sub-categoría..."
                    className="input flex-1 text-xs py-1"
                  />
                  <button
                    onClick={() => crearSub(cat.id)}
                    disabled={saving || !(nuevoSub[cat.id] ?? '').trim()}
                    className="text-xs px-2.5 py-1 bg-gray-100 text-gray-600 rounded hover:bg-gray-200 disabled:opacity-40 shrink-0"
                  >
                    + Sub
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="px-5 py-3 border-t flex justify-end">
          <button onClick={onClose} className="btn-secondary">Cerrar</button>
        </div>
      </div>
    </div>
  )
}


// ── Modal crear / editar ───────────────────────────────────────────────────────

type FormData = {
  codigo: string
  nombre: string
  descripcion: string
  categoria_id: string
  tipo_item: string
  unidad_medida_id: string
  metodo_costo: string
  precio_venta: string
  costo_referencia: string
  stock_minimo: string
  stock_maximo: string
  exento: boolean
  no_sujeto: boolean
  usa_lotes: boolean
  usa_vencimiento: boolean
}

function ModalProducto({
  tenantId, producto, categorias, tiposItem, unidades, onClose, onSave,
}: {
  tenantId: number
  producto: Producto | null
  categorias: Categoria[]
  tiposItem: TipoItem[]
  unidades: UnidadMed[]
  onClose: () => void
  onSave: () => void
}) {
  const isNew = !producto
  const [saving, setSaving] = useState(false)
  const [error, setError]   = useState('')

  const [form, setForm] = useState<FormData>({
    codigo:           producto?.codigo          ?? '',
    nombre:           producto?.nombre          ?? '',
    descripcion:      producto?.descripcion     ?? '',
    categoria_id:     String(producto?.categoria_id ?? ''),
    tipo_item:        String(producto?.tipo_item ?? tiposItem[0]?.codigo ?? 1),
    unidad_medida_id: String(producto?.unidad_medida_id ?? 36),
    metodo_costo:     producto?.metodo_costo    ?? 'PROMEDIO',
    precio_venta:     producto?.precio_venta    ?? '',
    costo_referencia: producto?.costo_referencia ?? '',
    stock_minimo:     producto?.stock_minimo    ?? '',
    stock_maximo:     producto?.stock_maximo    ?? '',
    exento:           producto?.exento          ?? false,
    no_sujeto:        producto?.no_sujeto       ?? false,
    usa_lotes:        producto?.usa_lotes       ?? false,
    usa_vencimiento:  producto?.usa_vencimiento ?? false,
  })

  function set(field: keyof FormData, value: string | boolean) {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!form.codigo.trim() || !form.nombre.trim()) {
      setError('Código y nombre son obligatorios')
      return
    }
    setSaving(true)
    setError('')
    try {
      const payload = {
        codigo:           form.codigo.trim(),
        nombre:           form.nombre.trim(),
        descripcion:      form.descripcion.trim() || null,
        categoria_id:     form.categoria_id ? parseInt(form.categoria_id) : null,
        tipo_item:        parseInt(form.tipo_item),
        unidad_medida_id: parseInt(form.unidad_medida_id),
        metodo_costo:     form.metodo_costo,
        precio_venta:     form.precio_venta ? parseFloat(form.precio_venta) : null,
        costo_referencia: form.costo_referencia ? parseFloat(form.costo_referencia) : null,
        stock_minimo:     form.stock_minimo ? parseFloat(form.stock_minimo) : null,
        stock_maximo:     form.stock_maximo ? parseFloat(form.stock_maximo) : null,
        exento:           form.exento,
        no_sujeto:        form.no_sujeto,
        usa_lotes:        form.usa_lotes,
        usa_vencimiento:  form.usa_vencimiento,
      }
      if (isNew) {
        await api.post(`/tenants/${tenantId}/productos`, payload)
      } else {
        await api.patch(`/tenants/${tenantId}/productos/${producto.id}`, payload)
      }
      onSave()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al guardar'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b sticky top-0 bg-white">
          <h3 className="text-lg font-bold text-gray-800">
            {isNew ? 'Nuevo producto' : 'Editar producto'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl font-bold">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">

          {/* Identificación */}
          <section>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Identificación</h4>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Código *</label>
                <input value={form.codigo} onChange={e => set('codigo', e.target.value)}
                  className="input" placeholder="PROD-001" required disabled={!isNew} />
                {!isNew && <p className="text-xs text-gray-400 mt-1">El código no se puede cambiar</p>}
              </div>
              <div className="col-span-1">
                <label className="label">Categoría</label>
                <select value={form.categoria_id} onChange={e => set('categoria_id', e.target.value)} className="input">
                  <option value="">Sin categoría</option>
                  {categorias.map(c => <option key={c.id} value={c.id}>{c.nombre}</option>)}
                </select>
              </div>
              <div className="col-span-2">
                <label className="label">Nombre *</label>
                <input value={form.nombre} onChange={e => set('nombre', e.target.value)}
                  className="input" placeholder="Nombre del producto" required />
              </div>
              <div className="col-span-2">
                <label className="label">Descripción</label>
                <textarea value={form.descripcion} onChange={e => set('descripcion', e.target.value)}
                  className="input resize-none h-16" placeholder="Descripción opcional" />
              </div>
            </div>
          </section>

          {/* Clasificación */}
          <section>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Clasificación</h4>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Tipo de ítem (CAT-011) *</label>
                <select value={form.tipo_item} onChange={e => set('tipo_item', e.target.value)} className="input">
                  {tiposItem.map(t => <option key={t.codigo} value={t.codigo}>{t.codigo} — {t.descripcion}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Unidad de medida (CAT-014) *</label>
                <select value={form.unidad_medida_id} onChange={e => set('unidad_medida_id', e.target.value)} className="input">
                  {unidades.map(u => <option key={u.codigo} value={u.codigo}>{u.codigo} — {u.descripcion}</option>)}
                </select>
              </div>
            </div>
          </section>

          {/* Precios */}
          <section>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Precios referencia</h4>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Precio de venta</label>
                <input type="number" step="0.0001" min="0" value={form.precio_venta}
                  onChange={e => set('precio_venta', e.target.value)} className="input" placeholder="0.00" />
              </div>
              <div>
                <label className="label">Costo de referencia</label>
                <input type="number" step="0.0001" min="0" value={form.costo_referencia}
                  onChange={e => set('costo_referencia', e.target.value)} className="input" placeholder="0.00" />
              </div>
            </div>
          </section>

          {/* Inventario */}
          <section>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Inventario</h4>
            <div className="grid grid-cols-3 gap-3 mb-3">
              <div>
                <label className="label">Método de costeo</label>
                <select value={form.metodo_costo} onChange={e => set('metodo_costo', e.target.value)} className="input">
                  {METODOS.map(m => <option key={m}>{m}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Stock mínimo</label>
                <input type="number" step="0.0001" min="0" value={form.stock_minimo}
                  onChange={e => set('stock_minimo', e.target.value)} className="input" placeholder="0" />
              </div>
              <div>
                <label className="label">Stock máximo</label>
                <input type="number" step="0.0001" min="0" value={form.stock_maximo}
                  onChange={e => set('stock_maximo', e.target.value)} className="input" placeholder="—" />
              </div>
            </div>
            <div className="flex gap-6">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.usa_lotes} onChange={e => set('usa_lotes', e.target.checked)}
                  className="w-4 h-4 rounded" />
                <span className="text-sm text-gray-700">Maneja lotes / batches</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.usa_vencimiento} onChange={e => set('usa_vencimiento', e.target.checked)}
                  className="w-4 h-4 rounded" />
                <span className="text-sm text-gray-700">Fecha de vencimiento</span>
              </label>
            </div>
          </section>

          {/* Fiscal */}
          <section>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Fiscal (DTE El Salvador)</h4>
            <div className="flex gap-6">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.exento} onChange={e => set('exento', e.target.checked)}
                  className="w-4 h-4 rounded" />
                <span className="text-sm text-gray-700">Exento de IVA</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.no_sujeto} onChange={e => set('no_sujeto', e.target.checked)}
                  className="w-4 h-4 rounded" />
                <span className="text-sm text-gray-700">No sujeto</span>
              </label>
            </div>
          </section>

          {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}

          <div className="flex justify-end gap-3 pt-2 border-t">
            <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? 'Guardando...' : isNew ? 'Crear producto' : 'Guardar cambios'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}


// ── Modal importar Excel ───────────────────────────────────────────────────────

function ModalImport({
  filas, importando, resultado, onConfirmar, onClose,
}: {
  filas: FilaImport[]
  importando: boolean
  resultado: { importados: number; omitidos: number; errores: string[] } | null
  onConfirmar: () => void
  onClose: () => void
}) {
  const validas   = filas.filter(f => !f._error).length
  const invalidas = filas.filter(f => !!f._error).length

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b sticky top-0 bg-white">
          <h3 className="text-lg font-bold text-gray-800">Vista previa de importación</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl font-bold">✕</button>
        </div>

        <div className="p-6">
          {/* Resumen */}
          <div className="flex gap-4 mb-5">
            <div className="flex-1 bg-green-50 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-green-700">{validas}</p>
              <p className="text-xs text-green-600 mt-1">Listas para importar</p>
            </div>
            <div className="flex-1 bg-red-50 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-red-600">{invalidas}</p>
              <p className="text-xs text-red-500 mt-1">Con errores (se omiten)</p>
            </div>
            <div className="flex-1 bg-gray-50 rounded-xl p-4 text-center">
              <p className="text-2xl font-bold text-gray-700">{filas.length}</p>
              <p className="text-xs text-gray-500 mt-1">Total de filas</p>
            </div>
          </div>

          {/* Resultado después de importar */}
          {resultado && (
            <div className="mb-5 bg-indigo-50 rounded-xl p-4">
              <p className="font-semibold text-indigo-800 mb-1">Importación completada</p>
              <p className="text-sm text-indigo-700">✓ {resultado.importados} importados — {resultado.omitidos} omitidos</p>
              {resultado.errores.length > 0 && (
                <ul className="mt-2 text-xs text-red-600 space-y-0.5">
                  {resultado.errores.map((e, i) => <li key={i}>• {e}</li>)}
                </ul>
              )}
            </div>
          )}

          {/* Tabla de filas */}
          <div className="overflow-x-auto rounded-xl border">
            <table className="w-full text-xs">
              <thead className="bg-gray-50 text-gray-500 uppercase">
                <tr>
                  <th className="px-3 py-2 text-left">Fila</th>
                  <th className="px-3 py-2 text-left">Código</th>
                  <th className="px-3 py-2 text-left">Nombre</th>
                  <th className="px-3 py-2 text-left">Categoría</th>
                  <th className="px-3 py-2 text-center">Tipo</th>
                  <th className="px-3 py-2 text-right">Precio</th>
                  <th className="px-3 py-2 text-center">Método</th>
                  <th className="px-3 py-2 text-left">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filas.map(f => (
                  <tr key={f._fila} className={f._error ? 'bg-red-50' : ''}>
                    <td className="px-3 py-2 text-gray-400">{f._fila}</td>
                    <td className="px-3 py-2 font-mono">{f.codigo || '—'}</td>
                    <td className="px-3 py-2 font-medium">{f.nombre || '—'}</td>
                    <td className="px-3 py-2 max-w-[160px]">
                      {f._cat_nombre
                        ? <span className="text-gray-700">{f._cat_nombre}</span>
                        : <span className="text-gray-300">—</span>}
                      {f._warn && (
                        <span className="block text-[10px] text-amber-600 bg-amber-50 rounded px-1 mt-0.5 leading-tight">{f._warn}</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-center">{f.tipo_item}</td>
                    <td className="px-3 py-2 text-right font-mono">
                      {f.precio_venta != null ? `$${f.precio_venta.toFixed(2)}` : '—'}
                    </td>
                    <td className="px-3 py-2 text-center">{f.metodo_costo}</td>
                    <td className="px-3 py-2">
                      {f._error
                        ? <span className="text-red-600">✗ {f._error}</span>
                        : <span className="text-green-600">✓ OK</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex justify-end gap-3 mt-5">
            <button onClick={onClose} className="btn-secondary">Cancelar</button>
            {!resultado && (
              <button
                onClick={onConfirmar}
                disabled={importando || validas === 0}
                className="btn-primary"
              >
                {importando ? 'Importando...' : `Importar ${validas} producto${validas !== 1 ? 's' : ''}`}
              </button>
            )}
            {resultado && (
              <button onClick={onClose} className="btn-primary">Cerrar</button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
