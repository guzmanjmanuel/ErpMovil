import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

// ── Tipos ──────────────────────────────────────────────────────────────────────
interface Ubicacion {
  id: number; establecimiento_id: number; nombre: string
  codigo: string | null; tipo: string; padre_id: number | null
  permite_picking: boolean; activo: boolean
}
interface Lote {
  id: number; producto_id: number; numero_lote: string
  fecha_fabricacion: string | null; fecha_vencimiento: string | null
  notas: string | null; activo: boolean; created_at: string
}
interface StockRow {
  id: number; producto_id: number; producto_nombre: string; producto_codigo: string
  ubicacion_id: number; ubicacion_nombre: string
  lote_id: number | null; numero_lote: string | null
  cantidad: string; cantidad_reservada: string; costo_promedio: string | null
}
interface Producto { id: number; codigo: string; nombre: string; usa_lotes: boolean }
interface Establecimiento { id: number; nombre: string }

const TIPOS_UBICACION = ['BODEGA', 'PASILLO', 'ESTANTE', 'CASILLA', 'VIRTUAL']
type Tab = 'stock' | 'ubicaciones' | 'lotes' | 'movimientos'

// ── Página principal ───────────────────────────────────────────────────────────
export default function Inventario() {
  const { user } = useAuth()
  const tenantId = user?.tenant_id
  const [tab, setTab] = useState<Tab>('stock')

  const [ubicaciones, setUbicaciones]       = useState<Ubicacion[]>([])
  const [lotes, setLotes]                   = useState<Lote[]>([])
  const [stock, setStock]                   = useState<StockRow[]>([])
  const [movimientos, setMovimientos]       = useState<any[]>([])
  const [productos, setProductos]           = useState<Producto[]>([])
  const [establecimientos, setEstablecimientos] = useState<Establecimiento[]>([])
  const [loading, setLoading]               = useState(false)
  const [buscarStock, setBuscarStock]       = useState('')

  // Modals
  const [showAjuste, setShowAjuste]             = useState(false)
  const [showTransfer, setShowTransfer]         = useState(false)
  const [showNuevaUbic, setShowNuevaUbic]       = useState(false)
  const [showNuevoLote, setShowNuevoLote]       = useState(false)
  const [editUbic, setEditUbic]                 = useState<Ubicacion | null>(null)
  const [editLote, setEditLote]                 = useState<Lote | null>(null)

  async function cargarTodo() {
    if (!tenantId) return
    setLoading(true)
    const [ubics, prods, estabs] = await Promise.all([
      api.get<Ubicacion[]>(`/tenants/${tenantId}/ubicaciones`),
      api.get<Producto[]>(`/tenants/${tenantId}/productos`),
      api.get<Establecimiento[]>(`/tenants/${tenantId}/establecimientos`),
    ])
    setUbicaciones(ubics)
    setProductos(prods)
    setEstablecimientos(estabs)
    setLoading(false)
  }

  async function cargarStock(buscar?: string) {
    if (!tenantId) return
    const path = `/tenants/${tenantId}/stock` + (buscar ? `?buscar=${encodeURIComponent(buscar)}` : '')
    const data = await api.get<StockRow[]>(path)
    setStock(data)
  }

  async function cargarLotes() {
    if (!tenantId) return
    const data = await api.get<Lote[]>(`/tenants/${tenantId}/lotes`)
    setLotes(data)
  }

  async function cargarMovimientos() {
    if (!tenantId) return
    const data = await api.get<any[]>(`/tenants/${tenantId}/stock/movimientos?limit=200`)
    setMovimientos(data)
  }

  useEffect(() => { cargarTodo() }, [tenantId])

  useEffect(() => {
    if (tab === 'stock')        cargarStock()
    if (tab === 'lotes')        cargarLotes()
    if (tab === 'movimientos')  cargarMovimientos()
  }, [tab, tenantId])

  async function eliminarUbicacion(ub: Ubicacion) {
    if (!confirm(`¿Eliminar ubicación "${ub.nombre}"?`)) return
    try {
      await api.delete(`/tenants/${tenantId}/ubicaciones/${ub.id}`)
      setUbicaciones(prev => prev.filter(u => u.id !== ub.id))
    } catch (e: any) { alert(e.message) }
  }

  async function eliminarLote(lote: Lote) {
    if (!confirm(`¿Eliminar lote "${lote.numero_lote}"?`)) return
    try {
      await api.delete(`/tenants/${tenantId}/lotes/${lote.id}`)
      setLotes(prev => prev.filter(l => l.id !== lote.id))
    } catch (e: any) { alert(e.message) }
  }

  const raices = ubicaciones.filter(u => u.padre_id === null)
  const hijosDe = (id: number) => ubicaciones.filter(u => u.padre_id === id)

  const diasParaVencer = (fecha: string | null) => {
    if (!fecha) return null
    const diff = Math.ceil((new Date(fecha).getTime() - Date.now()) / 86400000)
    return diff
  }

  const labelProducto = (id: number) => productos.find(p => p.id === id)?.nombre ?? `Producto #${id}`

  const TAB_CLS = (t: Tab) => `px-4 py-2 text-sm font-medium rounded-lg transition ${tab === t ? 'bg-white text-indigo-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-800">Inventario</h2>
          <p className="text-xs text-gray-500 mt-0.5">Ubicaciones, lotes, stock y movimientos</p>
        </div>
        <div className="flex gap-2">
          {tab === 'stock' && (
            <>
              <button onClick={() => setShowAjuste(true)} className="btn-secondary text-xs">+ Ajuste de stock</button>
              <button onClick={() => setShowTransfer(true)} className="btn-secondary text-xs">⇄ Transferir</button>
            </>
          )}
          {tab === 'ubicaciones' && (
            <button onClick={() => { setEditUbic(null); setShowNuevaUbic(true) }} className="btn-primary text-xs">+ Nueva ubicación</button>
          )}
          {tab === 'lotes' && (
            <button onClick={() => { setEditLote(null); setShowNuevoLote(true) }} className="btn-primary text-xs">+ Nuevo lote</button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-gray-100 rounded-xl p-1 flex gap-1 mb-6 w-fit">
        {([['stock','Stock'], ['ubicaciones','Ubicaciones'], ['lotes','Lotes'], ['movimientos','Movimientos']] as [Tab,string][]).map(([t, label]) => (
          <button key={t} onClick={() => setTab(t)} className={TAB_CLS(t)}>{label}</button>
        ))}
      </div>

      {/* ── Tab Stock ─────────────────────────────────────────────────────────── */}
      {tab === 'stock' && (
        <div>
          <div className="flex gap-2 mb-4">
            <input value={buscarStock} onChange={e => setBuscarStock(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && cargarStock(buscarStock)}
              placeholder="Buscar producto..." className="input max-w-sm" />
            <button onClick={() => cargarStock(buscarStock)} className="btn-primary text-sm">Buscar</button>
            {buscarStock && <button onClick={() => { setBuscarStock(''); cargarStock() }} className="btn-secondary text-sm">Limpiar</button>}
          </div>

          {stock.length === 0 ? (
            <div className="py-16 text-center text-gray-400">
              <p className="text-4xl mb-3">📦</p>
              <p className="font-medium">Sin stock registrado</p>
              <p className="text-sm mt-1">Usa "Ajuste de stock" para ingresar inventario</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                  <tr>
                    <th className="px-4 py-3 text-left">Producto</th>
                    <th className="px-4 py-3 text-left">Ubicación</th>
                    <th className="px-4 py-3 text-left">Lote</th>
                    <th className="px-4 py-3 text-right">Cantidad</th>
                    <th className="px-4 py-3 text-right">Reservado</th>
                    <th className="px-4 py-3 text-right">Costo prom.</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {stock.map(s => (
                    <tr key={s.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <p className="font-medium text-gray-800">{s.producto_nombre}</p>
                        <p className="text-xs text-gray-400 font-mono">{s.producto_codigo}</p>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{s.ubicacion_nombre}</td>
                      <td className="px-4 py-3 text-xs text-gray-500 font-mono">{s.numero_lote ?? '—'}</td>
                      <td className="px-4 py-3 text-right font-mono font-semibold text-gray-800">
                        {parseFloat(s.cantidad).toFixed(4)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-gray-400">
                        {parseFloat(s.cantidad_reservada).toFixed(4)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-gray-600">
                        {s.costo_promedio ? `$${parseFloat(s.costo_promedio).toFixed(4)}` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── Tab Ubicaciones ───────────────────────────────────────────────────── */}
      {tab === 'ubicaciones' && (
        <div className="space-y-3 max-w-2xl">
          {ubicaciones.length === 0 && !loading && (
            <div className="py-16 text-center text-gray-400">
              <p className="text-4xl mb-3">🏭</p>
              <p className="font-medium">Sin ubicaciones creadas</p>
              <p className="text-sm mt-1">Crea bodegas y organiza tu inventario</p>
            </div>
          )}
          {raices.map(raiz => (
            <div key={raiz.id} className="border border-gray-200 rounded-xl overflow-hidden">
              {/* Bodega raíz */}
              <div className="flex items-center gap-3 px-4 py-3 bg-gray-50">
                <span className="text-lg">🏭</span>
                <div className="flex-1">
                  <span className="font-semibold text-gray-800">{raiz.nombre}</span>
                  {raiz.codigo && <span className="ml-2 text-xs text-gray-400 font-mono">[{raiz.codigo}]</span>}
                  <span className="ml-2 text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">{raiz.tipo}</span>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => { setEditUbic(raiz); setShowNuevaUbic(true) }}
                    className="text-xs px-2 py-1 bg-indigo-50 text-indigo-700 rounded hover:bg-indigo-100">Editar</button>
                  <button onClick={() => eliminarUbicacion(raiz)}
                    className="text-xs px-2 py-1 bg-red-50 text-red-600 rounded hover:bg-red-100">Eliminar</button>
                </div>
              </div>
              {/* Hijos */}
              {hijosDe(raiz.id).map(hijo => (
                <div key={hijo.id} className="flex items-center gap-3 px-4 py-2.5 pl-10 border-t border-gray-100 bg-white">
                  <span className="text-sm">📦</span>
                  <div className="flex-1">
                    <span className="text-sm text-gray-700">{hijo.nombre}</span>
                    {hijo.codigo && <span className="ml-2 text-xs text-gray-400 font-mono">[{hijo.codigo}]</span>}
                    <span className="ml-2 text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">{hijo.tipo}</span>
                    {hijo.permite_picking && <span className="ml-1 text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">picking</span>}
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => { setEditUbic(hijo); setShowNuevaUbic(true) }}
                      className="text-xs px-2 py-1 bg-indigo-50 text-indigo-700 rounded hover:bg-indigo-100">Editar</button>
                    <button onClick={() => eliminarUbicacion(hijo)}
                      className="text-xs px-2 py-1 bg-red-50 text-red-600 rounded hover:bg-red-100">Eliminar</button>
                  </div>
                </div>
              ))}
              {/* Agregar hijo rápido */}
              <div className="border-t border-gray-100 px-4 py-2 pl-10">
                <button
                  onClick={() => {
                    setEditUbic({ id: 0, establecimiento_id: raiz.establecimiento_id, nombre: '', codigo: null, tipo: 'ESTANTE', padre_id: raiz.id, permite_picking: true, activo: true })
                    setShowNuevaUbic(true)
                  }}
                  className="text-xs text-indigo-500 hover:text-indigo-700"
                >
                  + Agregar estante / pasillo dentro de {raiz.nombre}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Tab Lotes ─────────────────────────────────────────────────────────── */}
      {tab === 'lotes' && (
        <div>
          {lotes.length === 0 ? (
            <div className="py-16 text-center text-gray-400">
              <p className="text-4xl mb-3">🏷</p>
              <p className="font-medium">Sin lotes registrados</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow overflow-hidden max-w-4xl">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                  <tr>
                    <th className="px-4 py-3 text-left">Producto</th>
                    <th className="px-4 py-3 text-left">N° Lote</th>
                    <th className="px-4 py-3 text-left">Fabricación</th>
                    <th className="px-4 py-3 text-left">Vencimiento</th>
                    <th className="px-4 py-3 text-left">Notas</th>
                    <th className="px-4 py-3 text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {lotes.map(l => {
                    const dias = diasParaVencer(l.fecha_vencimiento)
                    const venceProximo = dias !== null && dias <= 30 && dias >= 0
                    const vencido = dias !== null && dias < 0
                    return (
                      <tr key={l.id} className={vencido ? 'bg-red-50' : venceProximo ? 'bg-amber-50' : ''}>
                        <td className="px-4 py-3 text-gray-700">{labelProducto(l.producto_id)}</td>
                        <td className="px-4 py-3 font-mono font-medium text-gray-800">{l.numero_lote}</td>
                        <td className="px-4 py-3 text-gray-500">{l.fecha_fabricacion ?? '—'}</td>
                        <td className="px-4 py-3">
                          {l.fecha_vencimiento ? (
                            <span className={`font-medium ${vencido ? 'text-red-600' : venceProximo ? 'text-amber-600' : 'text-gray-700'}`}>
                              {l.fecha_vencimiento}
                              {vencido && ' ⚠ Vencido'}
                              {venceProximo && ` ⚠ ${dias}d`}
                            </span>
                          ) : '—'}
                        </td>
                        <td className="px-4 py-3 text-gray-400 text-xs">{l.notas ?? '—'}</td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex justify-end gap-1">
                            <button onClick={() => { setEditLote(l); setShowNuevoLote(true) }}
                              className="text-xs px-2 py-1 bg-indigo-50 text-indigo-700 rounded hover:bg-indigo-100">Editar</button>
                            <button onClick={() => eliminarLote(l)}
                              className="text-xs px-2 py-1 bg-red-50 text-red-600 rounded hover:bg-red-100">Eliminar</button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── Tab Movimientos ───────────────────────────────────────────────────── */}
      {tab === 'movimientos' && (
        <div>
          {movimientos.length === 0 ? (
            <div className="py-16 text-center text-gray-400">
              <p className="text-4xl mb-3">📋</p>
              <p className="font-medium">Sin movimientos registrados</p>
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                  <tr>
                    <th className="px-4 py-3 text-left">Fecha</th>
                    <th className="px-4 py-3 text-left">Tipo</th>
                    <th className="px-4 py-3 text-left">Producto</th>
                    <th className="px-4 py-3 text-left">Origen</th>
                    <th className="px-4 py-3 text-left">Destino</th>
                    <th className="px-4 py-3 text-left">Lote</th>
                    <th className="px-4 py-3 text-right">Cantidad</th>
                    <th className="px-4 py-3 text-right">Costo U.</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {movimientos.map(m => {
                    const colorTipo: Record<string, string> = {
                      AJUSTE_POSITIVO: 'bg-green-100 text-green-700',
                      AJUSTE_NEGATIVO: 'bg-red-100 text-red-700',
                      TRANSFERENCIA_SALIDA: 'bg-orange-100 text-orange-700',
                      TRANSFERENCIA_ENTRADA: 'bg-blue-100 text-blue-700',
                      COMPRA: 'bg-indigo-100 text-indigo-700',
                      VENTA: 'bg-purple-100 text-purple-700',
                    }
                    return (
                      <tr key={m.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-xs text-gray-400 whitespace-nowrap">
                          {new Date(m.created_at).toLocaleString('es-SV')}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${colorTipo[m.tipo_movimiento] ?? 'bg-gray-100 text-gray-600'}`}>
                            {m.tipo_movimiento.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <p className="font-medium text-gray-800 text-xs">{m.producto_nombre}</p>
                          <p className="text-gray-400 text-xs font-mono">{m.producto_codigo}</p>
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-500">{m.ubicacion_origen ?? '—'}</td>
                        <td className="px-4 py-3 text-xs text-gray-500">{m.ubicacion_destino ?? '—'}</td>
                        <td className="px-4 py-3 text-xs font-mono text-gray-500">{m.numero_lote ?? '—'}</td>
                        <td className="px-4 py-3 text-right font-mono font-semibold text-gray-800">
                          {parseFloat(m.cantidad).toFixed(4)}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-gray-500">
                          ${parseFloat(m.costo_unitario).toFixed(4)}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      {showAjuste && (
        <ModalAjuste tenantId={tenantId!} productos={productos} ubicaciones={ubicaciones} lotes={lotes}
          onClose={() => setShowAjuste(false)}
          onSave={() => { setShowAjuste(false); cargarStock() }} />
      )}
      {showTransfer && (
        <ModalTransferencia tenantId={tenantId!} productos={productos} ubicaciones={ubicaciones} lotes={lotes}
          onClose={() => setShowTransfer(false)}
          onSave={() => { setShowTransfer(false); cargarStock() }} />
      )}
      {showNuevaUbic && (
        <ModalUbicacion tenantId={tenantId!} ubicacion={editUbic} ubicaciones={ubicaciones} establecimientos={establecimientos}
          onClose={() => setShowNuevaUbic(false)}
          onSave={async () => {
            const data = await api.get<Ubicacion[]>(`/tenants/${tenantId}/ubicaciones`)
            setUbicaciones(data); setShowNuevaUbic(false)
          }} />
      )}
      {showNuevoLote && (
        <ModalLote tenantId={tenantId!} lote={editLote} productos={productos}
          onClose={() => setShowNuevoLote(false)}
          onSave={async () => { await cargarLotes(); setShowNuevoLote(false) }} />
      )}
    </div>
  )
}


// ── Modal Ajuste de Stock ──────────────────────────────────────────────────────
function ModalAjuste({ tenantId, productos, ubicaciones, lotes, onClose, onSave }: {
  tenantId: number; productos: Producto[]; ubicaciones: Ubicacion[]
  lotes: Lote[]; onClose: () => void; onSave: () => void
}) {
  const [form, setForm] = useState({ producto_id: '', ubicacion_id: '', lote_id: '', cantidad: '', costo_unitario: '0', notas: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const prodSel = productos.find(p => p.id === Number(form.producto_id))
  const lotesDelProd = lotes.filter(l => l.producto_id === Number(form.producto_id))

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!form.producto_id || !form.ubicacion_id || !form.cantidad) { setError('Completa todos los campos requeridos'); return }
    setSaving(true); setError('')
    try {
      await api.post(`/tenants/${tenantId}/stock/ajuste`, {
        producto_id: Number(form.producto_id),
        ubicacion_id: Number(form.ubicacion_id),
        lote_id: form.lote_id ? Number(form.lote_id) : null,
        cantidad: parseFloat(form.cantidad),
        costo_unitario: parseFloat(form.costo_unitario) || 0,
        notas: form.notas || null,
      })
      onSave()
    } catch (e: any) { setError(e.message) } finally { setSaving(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between p-5 border-b">
          <h3 className="font-bold text-gray-800">Ajuste de stock</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl font-bold">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="label">Producto *</label>
            <select value={form.producto_id} onChange={e => setForm(f => ({ ...f, producto_id: e.target.value, lote_id: '' }))} className="input">
              <option value="">Seleccionar...</option>
              {productos.map(p => <option key={p.id} value={p.id}>{p.nombre} ({p.codigo})</option>)}
            </select>
          </div>
          <div>
            <label className="label">Ubicación / Bodega *</label>
            <select value={form.ubicacion_id} onChange={e => setForm(f => ({ ...f, ubicacion_id: e.target.value }))} className="input">
              <option value="">Seleccionar...</option>
              {ubicaciones.map(u => <option key={u.id} value={u.id}>{u.nombre} ({u.tipo})</option>)}
            </select>
          </div>
          {prodSel?.usa_lotes && (
            <div>
              <label className="label">Lote</label>
              <select value={form.lote_id} onChange={e => setForm(f => ({ ...f, lote_id: e.target.value }))} className="input">
                <option value="">Sin lote</option>
                {lotesDelProd.map(l => <option key={l.id} value={l.id}>{l.numero_lote}{l.fecha_vencimiento ? ` — vence ${l.fecha_vencimiento}` : ''}</option>)}
              </select>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Cantidad * <span className="text-gray-400 font-normal">(negativo = salida)</span></label>
              <input type="number" step="0.0001" value={form.cantidad}
                onChange={e => setForm(f => ({ ...f, cantidad: e.target.value }))} className="input" placeholder="Ej: 100 ó -5" />
            </div>
            <div>
              <label className="label">Costo unitario</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">$</span>
                <input type="number" step="0.0001" min="0" value={form.costo_unitario}
                  onChange={e => setForm(f => ({ ...f, costo_unitario: e.target.value }))} className="input pl-7" />
              </div>
            </div>
          </div>
          <div>
            <label className="label">Notas</label>
            <input value={form.notas} onChange={e => setForm(f => ({ ...f, notas: e.target.value }))} className="input" placeholder="Motivo del ajuste..." />
          </div>
          {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}
          <div className="flex justify-end gap-3 pt-2 border-t">
            <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
            <button type="submit" disabled={saving} className="btn-primary">{saving ? 'Guardando...' : 'Aplicar ajuste'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}


// ── Modal Transferencia ────────────────────────────────────────────────────────
function ModalTransferencia({ tenantId, productos, ubicaciones, lotes, onClose, onSave }: {
  tenantId: number; productos: Producto[]; ubicaciones: Ubicacion[]
  lotes: Lote[]; onClose: () => void; onSave: () => void
}) {
  const [form, setForm] = useState({ producto_id: '', origen_id: '', destino_id: '', lote_id: '', cantidad: '', notas: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const prodSel = productos.find(p => p.id === Number(form.producto_id))
  const lotesDelProd = lotes.filter(l => l.producto_id === Number(form.producto_id))

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true); setError('')
    try {
      await api.post(`/tenants/${tenantId}/stock/transferencia`, {
        producto_id: Number(form.producto_id),
        ubicacion_origen_id: Number(form.origen_id),
        ubicacion_destino_id: Number(form.destino_id),
        lote_id: form.lote_id ? Number(form.lote_id) : null,
        cantidad: parseFloat(form.cantidad),
        notas: form.notas || null,
      })
      onSave()
    } catch (e: any) { setError(e.message) } finally { setSaving(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between p-5 border-b">
          <h3 className="font-bold text-gray-800">Transferir entre ubicaciones</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl font-bold">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="label">Producto *</label>
            <select value={form.producto_id} onChange={e => setForm(f => ({ ...f, producto_id: e.target.value, lote_id: '' }))} className="input">
              <option value="">Seleccionar...</option>
              {productos.map(p => <option key={p.id} value={p.id}>{p.nombre}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Bodega origen *</label>
              <select value={form.origen_id} onChange={e => setForm(f => ({ ...f, origen_id: e.target.value }))} className="input">
                <option value="">Seleccionar...</option>
                {ubicaciones.map(u => <option key={u.id} value={u.id}>{u.nombre}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Bodega destino *</label>
              <select value={form.destino_id} onChange={e => setForm(f => ({ ...f, destino_id: e.target.value }))} className="input">
                <option value="">Seleccionar...</option>
                {ubicaciones.filter(u => String(u.id) !== form.origen_id).map(u => <option key={u.id} value={u.id}>{u.nombre}</option>)}
              </select>
            </div>
          </div>
          {prodSel?.usa_lotes && (
            <div>
              <label className="label">Lote</label>
              <select value={form.lote_id} onChange={e => setForm(f => ({ ...f, lote_id: e.target.value }))} className="input">
                <option value="">Sin lote</option>
                {lotesDelProd.map(l => <option key={l.id} value={l.id}>{l.numero_lote}</option>)}
              </select>
            </div>
          )}
          <div>
            <label className="label">Cantidad *</label>
            <input type="number" step="0.0001" min="0.0001" value={form.cantidad}
              onChange={e => setForm(f => ({ ...f, cantidad: e.target.value }))} className="input" />
          </div>
          <div>
            <label className="label">Notas</label>
            <input value={form.notas} onChange={e => setForm(f => ({ ...f, notas: e.target.value }))} className="input" placeholder="Motivo..." />
          </div>
          {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}
          <div className="flex justify-end gap-3 pt-2 border-t">
            <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
            <button type="submit" disabled={saving} className="btn-primary">{saving ? 'Transfiriendo...' : 'Transferir'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}


// ── Modal Ubicación ────────────────────────────────────────────────────────────
function ModalUbicacion({ tenantId, ubicacion, ubicaciones, establecimientos, onClose, onSave }: {
  tenantId: number; ubicacion: Ubicacion | null; ubicaciones: Ubicacion[]
  establecimientos: Establecimiento[]; onClose: () => void; onSave: () => void
}) {
  const isNew = !ubicacion?.id
  const [form, setForm] = useState({
    establecimiento_id: String(ubicacion?.establecimiento_id ?? establecimientos[0]?.id ?? ''),
    nombre: ubicacion?.nombre ?? '',
    codigo: ubicacion?.codigo ?? '',
    tipo: ubicacion?.tipo ?? 'BODEGA',
    padre_id: String(ubicacion?.padre_id ?? ''),
    permite_picking: ubicacion?.permite_picking ?? true,
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!form.nombre.trim()) { setError('El nombre es obligatorio'); return }
    setSaving(true); setError('')
    try {
      const payload = {
        establecimiento_id: Number(form.establecimiento_id),
        nombre: form.nombre.trim(),
        codigo: form.codigo.trim() || null,
        tipo: form.tipo,
        padre_id: form.padre_id ? Number(form.padre_id) : null,
        permite_picking: form.permite_picking,
      }
      if (isNew) {
        await api.post(`/tenants/${tenantId}/ubicaciones`, payload)
      } else {
        await api.patch(`/tenants/${tenantId}/ubicaciones/${ubicacion!.id}`, payload)
      }
      onSave()
    } catch (e: any) { setError(e.message) } finally { setSaving(false) }
  }

  const raices = ubicaciones.filter(u => u.padre_id === null && u.id !== ubicacion?.id)

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between p-5 border-b">
          <h3 className="font-bold text-gray-800">{isNew ? 'Nueva ubicación' : 'Editar ubicación'}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl font-bold">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="label">Sucursal / Establecimiento *</label>
            <select value={form.establecimiento_id} onChange={e => setForm(f => ({ ...f, establecimiento_id: e.target.value }))} className="input">
              {establecimientos.map(e => <option key={e.id} value={e.id}>{e.nombre}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Nombre *</label>
              <input value={form.nombre} onChange={e => setForm(f => ({ ...f, nombre: e.target.value }))} className="input" placeholder="Bodega Central" required />
            </div>
            <div>
              <label className="label">Código</label>
              <input value={form.codigo} onChange={e => setForm(f => ({ ...f, codigo: e.target.value }))} className="input" placeholder="BOD-01" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Tipo *</label>
              <select value={form.tipo} onChange={e => setForm(f => ({ ...f, tipo: e.target.value }))} className="input">
                {TIPOS_UBICACION.map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Ubicación padre</label>
              <select value={form.padre_id} onChange={e => setForm(f => ({ ...f, padre_id: e.target.value }))} className="input">
                <option value="">Raíz (bodega principal)</option>
                {raices.map(u => <option key={u.id} value={u.id}>{u.nombre}</option>)}
              </select>
            </div>
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.permite_picking} onChange={e => setForm(f => ({ ...f, permite_picking: e.target.checked }))} className="w-4 h-4 rounded" />
            <span className="text-sm text-gray-700">Permite picking (despacho directo desde aquí)</span>
          </label>
          {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}
          <div className="flex justify-end gap-3 pt-2 border-t">
            <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
            <button type="submit" disabled={saving} className="btn-primary">{saving ? 'Guardando...' : isNew ? 'Crear' : 'Guardar'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}


// ── Modal Lote ────────────────────────────────────────────────────────────────
function ModalLote({ tenantId, lote, productos, onClose, onSave }: {
  tenantId: number; lote: Lote | null; productos: Producto[]
  onClose: () => void; onSave: () => void
}) {
  const isNew = !lote
  const [form, setForm] = useState({
    producto_id: String(lote?.producto_id ?? ''),
    numero_lote: lote?.numero_lote ?? '',
    fecha_fabricacion: lote?.fecha_fabricacion ?? '',
    fecha_vencimiento: lote?.fecha_vencimiento ?? '',
    notas: lote?.notas ?? '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!form.producto_id || !form.numero_lote.trim()) { setError('Producto y número de lote son obligatorios'); return }
    setSaving(true); setError('')
    try {
      const payload = {
        producto_id: Number(form.producto_id),
        numero_lote: form.numero_lote.trim(),
        fecha_fabricacion: form.fecha_fabricacion || null,
        fecha_vencimiento: form.fecha_vencimiento || null,
        notas: form.notas.trim() || null,
      }
      if (isNew) {
        await api.post(`/tenants/${tenantId}/lotes`, payload)
      } else {
        await api.patch(`/tenants/${tenantId}/lotes/${lote!.id}`, payload)
      }
      onSave()
    } catch (e: any) { setError(e.message) } finally { setSaving(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between p-5 border-b">
          <h3 className="font-bold text-gray-800">{isNew ? 'Nuevo lote' : 'Editar lote'}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl font-bold">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="label">Producto *</label>
            <select value={form.producto_id} onChange={e => setForm(f => ({ ...f, producto_id: e.target.value }))} className="input" disabled={!isNew}>
              <option value="">Seleccionar...</option>
              {productos.map(p => <option key={p.id} value={p.id}>{p.nombre} ({p.codigo})</option>)}
            </select>
          </div>
          <div>
            <label className="label">Número de lote *</label>
            <input value={form.numero_lote} onChange={e => setForm(f => ({ ...f, numero_lote: e.target.value }))} className="input" placeholder="LOT-2024-001" required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Fecha fabricación</label>
              <input type="date" value={form.fecha_fabricacion} onChange={e => setForm(f => ({ ...f, fecha_fabricacion: e.target.value }))} className="input" />
            </div>
            <div>
              <label className="label">Fecha vencimiento</label>
              <input type="date" value={form.fecha_vencimiento} onChange={e => setForm(f => ({ ...f, fecha_vencimiento: e.target.value }))} className="input" />
            </div>
          </div>
          <div>
            <label className="label">Notas</label>
            <textarea value={form.notas} onChange={e => setForm(f => ({ ...f, notas: e.target.value }))} className="input resize-none h-16" placeholder="Observaciones del lote..." />
          </div>
          {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}
          <div className="flex justify-end gap-3 pt-2 border-t">
            <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
            <button type="submit" disabled={saving} className="btn-primary">{saving ? 'Guardando...' : isNew ? 'Crear lote' : 'Guardar'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}
