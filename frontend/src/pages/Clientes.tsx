import { useEffect, useState, useRef, type FormEvent } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

// ── Tipos ─────────────────────────────────────────────────────────────────────

interface Contacto {
  id: number
  nombre: string
  correo: string | null
  telefono: string | null
  cargo: string | null
  principal: boolean
  created_at: string
}

interface Cliente {
  id: number
  nombre: string
  nombre_comercial: string | null
  tipo_contribuyente: string | null
  tipo_documento_id: string | null
  num_documento: string | null
  nit: string | null
  nrc: string | null
  dui: string | null
  cod_actividad: string | null
  desc_actividad: string | null
  correo_factura: string | null
  telefono: string | null
  cod_pais: string | null
  departamento: string | null
  municipio: string | null
  complemento_direccion: string | null
  activo: boolean
  created_at: string
  contactos: Contacto[]
}

interface Actividad    { codigo: string; descripcion: string }
interface Departamento { codigo: string; nombre: string }
interface Municipio    { codigo: string; departamento_id: string; nombre: string }

const TIPO_DOC_LABEL: Record<string, string> = {
  '13': 'DUI', '36': 'NIT', '03': 'Pasaporte', '02': 'Carné de residente', '37': 'Otro',
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function Clientes() {
  const { user } = useAuth()
  const tenantId = user?.tenant_id
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [loading, setLoading] = useState(true)
  const [buscar, setBuscar] = useState('')
  const [editando, setEditando] = useState<Cliente | null>(null)
  const [showForm, setShowForm] = useState(false)

  async function reload(q?: string) {
    if (!tenantId) return
    setLoading(true)
    const path = q
      ? `/tenants/${tenantId}/clientes?buscar=${encodeURIComponent(q)}`
      : `/tenants/${tenantId}/clientes`
    const data = await api.get<Cliente[]>(path)
    setClientes(data)
    setLoading(false)
  }

  useEffect(() => { reload() }, [tenantId])

  function handleSearch(e: FormEvent) { e.preventDefault(); reload(buscar) }

  async function handleDesactivar(c: Cliente) {
    if (!confirm(`¿Desactivar a "${c.nombre}"?`)) return
    await api.delete(`/tenants/${tenantId}/clientes/${c.id}`)
    reload(buscar || undefined)
  }

  function docPrincipal(c: Cliente) {
    if (c.tipo_contribuyente === 'juridico') return c.nit ? `NIT: ${c.nit}` : '—'
    if (c.num_documento) return `${TIPO_DOC_LABEL[c.tipo_documento_id ?? ''] ?? c.tipo_documento_id}: ${c.num_documento}`
    if (c.dui) return `DUI: ${c.dui}`
    return '—'
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-800">Clientes</h2>
          <p className="text-xs text-gray-500 mt-0.5">Directorio de clientes para facturación</p>
        </div>
        <button onClick={() => { setEditando(null); setShowForm(true) }} className="btn-primary">
          + Nuevo cliente
        </button>
      </div>

      <form onSubmit={handleSearch} className="flex gap-2 mb-5">
        <input
          value={buscar}
          onChange={e => setBuscar(e.target.value)}
          placeholder="Buscar por nombre, NIT, DUI, documento o correo..."
          className="input flex-1 max-w-md"
        />
        <button type="submit" className="btn-primary">Buscar</button>
        {buscar && (
          <button type="button" onClick={() => { setBuscar(''); reload() }} className="btn-secondary">
            Limpiar
          </button>
        )}
      </form>

      {loading ? (
        <p className="text-gray-400 text-sm">Cargando...</p>
      ) : clientes.length === 0 ? (
        <div className="py-16 text-center text-gray-400">
          <p className="text-4xl mb-3">👥</p>
          <p className="font-medium">Sin clientes registrados</p>
          <p className="text-sm mt-1">Agrega el primer cliente con el botón de arriba</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-4 py-3 text-left">Nombre</th>
                <th className="px-4 py-3 text-left">Tipo</th>
                <th className="px-4 py-3 text-left">Documento</th>
                <th className="px-4 py-3 text-left">Correo / Teléfono</th>
                <th className="px-4 py-3 text-left">Contactos</th>
                <th className="px-4 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {clientes.map(c => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-800">{c.nombre}</p>
                    {c.nombre_comercial && <p className="text-xs text-gray-400">{c.nombre_comercial}</p>}
                  </td>
                  <td className="px-4 py-3">
                    {c.tipo_contribuyente === 'juridico' ? (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium">Jurídico</span>
                    ) : c.tipo_contribuyente === 'natural' ? (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">Natural</span>
                    ) : <span className="text-xs text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-600 font-mono">{docPrincipal(c)}</td>
                  <td className="px-4 py-3">
                    {c.correo_factura && <p className="text-xs text-gray-600">{c.correo_factura}</p>}
                    {c.telefono && <p className="text-xs text-gray-400">{c.telefono}</p>}
                  </td>
                  <td className="px-4 py-3">
                    {c.contactos.length > 0 ? (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                        {c.contactos.length} contacto{c.contactos.length !== 1 ? 's' : ''}
                      </span>
                    ) : <span className="text-xs text-gray-300">—</span>}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => { setEditando(c); setShowForm(true) }}
                        className="text-xs px-2 py-1 bg-indigo-50 text-indigo-700 rounded-lg hover:bg-indigo-100 font-medium"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => handleDesactivar(c)}
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

      {showForm && (
        <ModalCliente
          tenantId={tenantId!}
          cliente={editando}
          onClose={() => setShowForm(false)}
          onSave={() => { setShowForm(false); reload(buscar || undefined) }}
        />
      )}
    </div>
  )
}


// ── Modal crear / editar ──────────────────────────────────────────────────────

type FormData = {
  nombre: string; nombre_comercial: string; tipo_contribuyente: string
  tipo_documento_id: string; num_documento: string
  nit: string; nrc: string; dui: string
  cod_actividad: string; desc_actividad: string
  correo_factura: string; telefono: string
  departamento: string; municipio: string; complemento_direccion: string
}

const EMPTY: FormData = {
  nombre: '', nombre_comercial: '', tipo_contribuyente: 'natural',
  tipo_documento_id: '13', num_documento: '', nit: '', nrc: '', dui: '',
  cod_actividad: '', desc_actividad: '', correo_factura: '', telefono: '',
  departamento: '', municipio: '', complemento_direccion: '',
}

// Contacto pendiente (local, sin id = nuevo, con id = ya existe)
type ContactoPendiente = {
  _key: string          // clave local única
  id?: number           // si ya existe en backend
  nombre: string
  correo: string
  telefono: string
  cargo: string
  principal: boolean
  _eliminar?: boolean   // marcado para eliminar al guardar
}

function ModalCliente({
  tenantId, cliente, onClose, onSave,
}: {
  tenantId: number
  cliente: Cliente | null
  onClose: () => void
  onSave: () => void
}) {
  const [form, setForm] = useState<FormData>(() =>
    cliente ? {
      nombre: cliente.nombre, nombre_comercial: cliente.nombre_comercial ?? '',
      tipo_contribuyente: cliente.tipo_contribuyente ?? 'natural',
      tipo_documento_id: cliente.tipo_documento_id ?? '13',
      num_documento: cliente.num_documento ?? '', nit: cliente.nit ?? '',
      nrc: cliente.nrc ?? '', dui: cliente.dui ?? '',
      cod_actividad: cliente.cod_actividad ?? '', desc_actividad: cliente.desc_actividad ?? '',
      correo_factura: cliente.correo_factura ?? '', telefono: cliente.telefono ?? '',
      departamento: cliente.departamento ?? '', municipio: cliente.municipio ?? '',
      complemento_direccion: cliente.complemento_direccion ?? '',
    } : EMPTY
  )

  // Catálogos
  const [actividades, setActividades]     = useState<Actividad[]>([])
  const [departamentos, setDepartamentos] = useState<Departamento[]>([])
  const [municipios, setMunicipios]       = useState<Municipio[]>([])

  // Autocomplete actividades
  const [actQuery, setActQuery] = useState(
    cliente?.cod_actividad && cliente?.desc_actividad
      ? `${cliente.cod_actividad} - ${cliente.desc_actividad}` : ''
  )
  const [actOpen, setActOpen] = useState(false)
  const actRef = useRef<HTMLDivElement>(null)

  // Contactos
  const [contactos, setContactos] = useState<ContactoPendiente[]>([])
  const [nuevoContacto, setNuevoContacto] = useState({ nombre: '', correo: '', telefono: '', cargo: '', principal: false })
  const [cargandoContactos, setCargandoContactos] = useState(false)

  const [saving, setSaving] = useState(false)
  const [error, setError]   = useState('')

  // Cargar catálogos
  useEffect(() => {
    api.get<Actividad[]>('/catalogos/actividades').then(setActividades).catch(() => {})
    api.get<Departamento[]>('/catalogos/departamentos').then(setDepartamentos).catch(() => {})
  }, [])

  // Cargar municipios cuando cambia el departamento
  useEffect(() => {
    if (!form.departamento) { setMunicipios([]); return }
    api.get<Municipio[]>(`/catalogos/municipios?departamento=${form.departamento}`)
      .then(setMunicipios).catch(() => {})
  }, [form.departamento])

  // Cargar contactos existentes (si estamos editando)
  useEffect(() => {
    if (!cliente) return
    setCargandoContactos(true)
    api.get<Contacto[]>(`/tenants/${tenantId}/clientes/${cliente.id}/contactos`)
      .then(data => {
        setContactos(data.map(ct => ({
          _key: String(ct.id),
          id: ct.id, nombre: ct.nombre, correo: ct.correo ?? '',
          telefono: ct.telefono ?? '', cargo: ct.cargo ?? '',
          principal: ct.principal,
        })))
      })
      .catch(() => {})
      .finally(() => setCargandoContactos(false))
  }, [cliente?.id])

  // Cerrar dropdown fuera
  useEffect(() => {
    function h(e: MouseEvent) {
      if (actRef.current && !actRef.current.contains(e.target as Node)) setActOpen(false)
    }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])

  const actFiltradas = actQuery.length >= 2
    ? actividades.filter(a =>
        a.codigo.startsWith(actQuery) ||
        a.descripcion.toLowerCase().includes(actQuery.toLowerCase()) ||
        `${a.codigo} - ${a.descripcion}`.toLowerCase().includes(actQuery.toLowerCase())
      ).slice(0, 30)
    : []

  function seleccionarActividad(a: Actividad) {
    setForm(f => ({ ...f, cod_actividad: a.codigo, desc_actividad: a.descripcion }))
    setActQuery(`${a.codigo} - ${a.descripcion}`)
    setActOpen(false)
  }

  function set(key: keyof FormData, val: string) {
    setForm(f => {
      const next = { ...f, [key]: val }
      if (key === 'departamento') next.municipio = ''
      return next
    })
  }

  // ── Gestión de contactos local ──

  function agregarContacto() {
    if (!nuevoContacto.nombre.trim()) return
    setContactos(prev => [
      ...prev,
      { _key: `new-${Date.now()}`, ...nuevoContacto },
    ])
    setNuevoContacto({ nombre: '', correo: '', telefono: '', cargo: '', principal: false })
  }

  function marcarPrincipal(key: string) {
    setContactos(prev => prev.map(c => ({ ...c, principal: c._key === key })))
  }

  function quitarContacto(key: string) {
    setContactos(prev =>
      prev.map(c => c._key === key ? { ...c, _eliminar: true } : c)
    )
  }

  // ── Guardar ──

  function payload() {
    const p: Record<string, string | null> = {}
    for (const [k, v] of Object.entries(form)) p[k] = v === '' ? null : v
    return p
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault()
    setSaving(true); setError('')
    try {
      let clienteId = cliente?.id

      // 1. Guardar datos principales del cliente
      if (cliente) {
        await api.patch(`/tenants/${tenantId}/clientes/${clienteId}`, payload())
      } else {
        const nuevo = await api.post<Cliente>(`/tenants/${tenantId}/clientes`, payload())
        clienteId = nuevo.id
      }

      // 2. Sincronizar contactos
      for (const ct of contactos) {
        if (ct._eliminar && ct.id) {
          await api.delete(`/tenants/${tenantId}/clientes/${clienteId}/contactos/${ct.id}`)
        } else if (!ct._eliminar && !ct.id) {
          await api.post(`/tenants/${tenantId}/clientes/${clienteId}/contactos`, {
            nombre: ct.nombre, correo: ct.correo || null,
            telefono: ct.telefono || null, cargo: ct.cargo || null,
            principal: ct.principal,
          })
        } else if (!ct._eliminar && ct.id) {
          // Actualizar si cambió el estado de principal
          await api.patch(
            `/tenants/${tenantId}/clientes/${clienteId}/contactos/${ct.id}`,
            { principal: ct.principal }
          )
        }
      }

      onSave()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  const esJuridico  = form.tipo_contribuyente === 'juridico'
  const visibles    = contactos.filter(c => !c._eliminar)
  const deptoActual = departamentos.find(d => d.codigo === form.departamento?.trim())
  const munActual   = municipios.find(m => m.codigo === form.municipio?.trim())

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="font-semibold text-gray-800">
              {cliente ? 'Editar cliente' : 'Nuevo cliente'}
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">Datos del receptor para DTE</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>

        <form onSubmit={handleSave} className="space-y-5">

          {/* Tipo de contribuyente */}
          <section className="bg-gray-50 rounded-xl p-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Tipo de contribuyente</p>
            <div className="flex gap-4">
              {(['natural', 'juridico'] as const).map(tipo => (
                <label key={tipo} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio" name="tipo_contribuyente" value={tipo}
                    checked={form.tipo_contribuyente === tipo}
                    onChange={() => set('tipo_contribuyente', tipo)}
                    className="accent-indigo-600"
                  />
                  <span className="text-sm text-gray-700">
                    {tipo === 'natural' ? 'Persona Natural' : 'Persona Jurídica'}
                  </span>
                </label>
              ))}
            </div>
          </section>

          {/* Identificación */}
          <section className="bg-gray-50 rounded-xl p-4 space-y-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Identificación</p>
            {esJuridico ? (
              <div className="grid grid-cols-2 gap-3">
                <Field label="NIT *">
                  <input required value={form.nit} onChange={e => set('nit', e.target.value)}
                    className="input" placeholder="06140000000000 (9 o 14 dígitos)" />
                </Field>
                <Field label="NRC">
                  <input value={form.nrc} onChange={e => set('nrc', e.target.value)}
                    className="input" placeholder="1234567 (1-8 dígitos)" />
                </Field>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                <Field label="Tipo de documento (CAT-022)">
                  <select value={form.tipo_documento_id} onChange={e => set('tipo_documento_id', e.target.value)} className="input">
                    <option value="13">13 — DUI</option>
                    <option value="36">36 — NIT</option>
                    <option value="03">03 — Pasaporte</option>
                    <option value="02">02 — Carné de residente</option>
                    <option value="37">37 — Otro</option>
                  </select>
                </Field>
                <Field label="Número de documento *">
                  <input required value={form.num_documento} onChange={e => set('num_documento', e.target.value)}
                    className="input" placeholder="Ej: 01234567-8" />
                </Field>
              </div>
            )}
          </section>

          {/* Datos generales */}
          <section className="bg-gray-50 rounded-xl p-4 space-y-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Datos generales</p>
            <Field label={esJuridico ? 'Razón social *' : 'Nombre completo *'}>
              <input required value={form.nombre} onChange={e => set('nombre', e.target.value)}
                className="input" placeholder={esJuridico ? 'Razón social del negocio' : 'Nombre completo'} />
            </Field>
            <Field label="Nombre comercial">
              <input value={form.nombre_comercial} onChange={e => set('nombre_comercial', e.target.value)}
                className="input" placeholder="Nombre comercial (opcional)" />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Correo para factura">
                <input type="email" value={form.correo_factura} onChange={e => set('correo_factura', e.target.value)}
                  className="input" placeholder="correo@ejemplo.com" />
              </Field>
              <Field label="Teléfono">
                <input value={form.telefono} onChange={e => set('telefono', e.target.value)}
                  className="input" placeholder="2222-0000" />
              </Field>
            </div>
          </section>

          {/* Actividad económica — solo jurídicos */}
          {esJuridico && (
            <section className="bg-gray-50 rounded-xl p-4 space-y-3">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Actividad económica (CAT-019)</p>
              <Field label="Actividad">
                <div ref={actRef} className="relative">
                  <input
                    value={actQuery}
                    onChange={e => { setActQuery(e.target.value); setActOpen(true) }}
                    onFocus={() => { if (actQuery.length >= 2) setActOpen(true) }}
                    className="input" placeholder="Escriba código o descripción (ej: 56101 o Restaurante)"
                    autoComplete="off"
                  />
                  {form.cod_actividad && (
                    <span className="absolute right-2 top-2 text-xs bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded font-mono">
                      {form.cod_actividad}
                    </span>
                  )}
                  {actOpen && actFiltradas.length > 0 && (
                    <ul className="absolute z-50 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto text-xs">
                      {actFiltradas.map(a => (
                        <li key={a.codigo} onMouseDown={() => seleccionarActividad(a)}
                          className="px-3 py-2 hover:bg-indigo-50 cursor-pointer flex gap-2">
                          <span className="font-mono text-indigo-600 shrink-0">{a.codigo}</span>
                          <span className="text-gray-700">{a.descripcion}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <p className="text-xs text-gray-400 mt-0.5">
                  {form.desc_actividad ? form.desc_actividad : 'Escriba al menos 2 caracteres para buscar'}
                </p>
              </Field>
            </section>
          )}

          {/* Dirección */}
          <section className="bg-gray-50 rounded-xl p-4 space-y-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Dirección</p>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Departamento (CAT-012)">
                <select value={form.departamento} onChange={e => set('departamento', e.target.value)} className="input">
                  <option value="">— Seleccione —</option>
                  {departamentos.map(d => (
                    <option key={d.codigo} value={d.codigo}>{d.codigo} — {d.nombre}</option>
                  ))}
                </select>
                {deptoActual && (
                  <p className="text-xs text-gray-400 mt-0.5">{deptoActual.nombre}</p>
                )}
              </Field>
              <Field label="Municipio (CAT-013)">
                <select
                  value={form.municipio}
                  onChange={e => set('municipio', e.target.value)}
                  className="input"
                  disabled={!form.departamento}
                >
                  <option value="">— Seleccione —</option>
                  {municipios.map(m => (
                    <option key={m.codigo} value={m.codigo}>{m.nombre}</option>
                  ))}
                </select>
                {munActual && (
                  <p className="text-xs text-gray-400 mt-0.5">{munActual.nombre}</p>
                )}
              </Field>
            </div>
            <Field label="Complemento de dirección">
              <input value={form.complemento_direccion} onChange={e => set('complemento_direccion', e.target.value)}
                className="input" placeholder="Calle, colonia, referencia..." />
            </Field>
          </section>

          {/* Contactos */}
          <section className="bg-gray-50 rounded-xl p-4 space-y-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Contactos</p>

            {cargandoContactos ? (
              <p className="text-xs text-gray-400">Cargando contactos...</p>
            ) : (
              <>
                {/* Lista de contactos actuales */}
                {visibles.length > 0 && (
                  <div className="space-y-2">
                    {visibles.map(ct => (
                      <div key={ct._key} className="flex items-center gap-2 bg-white rounded-lg border border-gray-200 px-3 py-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-medium text-gray-800">{ct.nombre}</span>
                            {ct.cargo && <span className="text-xs text-gray-400">{ct.cargo}</span>}
                            {ct.principal && (
                              <span className="text-xs px-1.5 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-medium">Principal</span>
                            )}
                          </div>
                          <div className="flex gap-3 mt-0.5 flex-wrap">
                            {ct.correo   && <span className="text-xs text-gray-500">{ct.correo}</span>}
                            {ct.telefono && <span className="text-xs text-gray-400">{ct.telefono}</span>}
                          </div>
                        </div>
                        <div className="flex gap-1 shrink-0">
                          {!ct.principal && (
                            <button type="button" onClick={() => marcarPrincipal(ct._key)}
                              className="text-xs px-1.5 py-0.5 bg-indigo-50 text-indigo-600 rounded hover:bg-indigo-100"
                              title="Marcar como principal">
                              Principal
                            </button>
                          )}
                          <button type="button" onClick={() => quitarContacto(ct._key)}
                            className="text-xs px-1.5 py-0.5 bg-red-50 text-red-500 rounded hover:bg-red-100"
                            title="Quitar contacto">
                            ✕
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Formulario para agregar contacto */}
                <div className="border border-dashed border-gray-300 rounded-xl p-3 space-y-2">
                  <p className="text-xs font-medium text-gray-500">Agregar contacto</p>
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      value={nuevoContacto.nombre}
                      onChange={e => setNuevoContacto(n => ({ ...n, nombre: e.target.value }))}
                      placeholder="Nombre *" className="input text-xs" />
                    <input
                      value={nuevoContacto.cargo}
                      onChange={e => setNuevoContacto(n => ({ ...n, cargo: e.target.value }))}
                      placeholder="Cargo (ej: Contador)" className="input text-xs" />
                    <input
                      type="email"
                      value={nuevoContacto.correo}
                      onChange={e => setNuevoContacto(n => ({ ...n, correo: e.target.value }))}
                      placeholder="Correo electrónico" className="input text-xs" />
                    <input
                      value={nuevoContacto.telefono}
                      onChange={e => setNuevoContacto(n => ({ ...n, telefono: e.target.value }))}
                      placeholder="Teléfono" className="input text-xs" />
                  </div>
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={nuevoContacto.principal}
                        onChange={e => setNuevoContacto(n => ({ ...n, principal: e.target.checked }))}
                        className="accent-indigo-600"
                      />
                      Contacto principal
                    </label>
                    <button
                      type="button"
                      onClick={agregarContacto}
                      disabled={!nuevoContacto.nombre.trim()}
                      className="text-xs px-3 py-1 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-40 font-medium"
                    >
                      + Agregar
                    </button>
                  </div>
                </div>
              </>
            )}
          </section>

          {error && <p className="text-xs text-red-600">{error}</p>}

          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? 'Guardando...' : cliente ? 'Actualizar cliente' : 'Crear cliente'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}


function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  )
}
