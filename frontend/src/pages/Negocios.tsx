import { useEffect, useState, useRef, type FormEvent } from 'react'
import { api } from '../api/client'

interface Tenant {
  id: number
  nombre: string
  tipo: string
  plan: string
  ambiente: string
  activo: boolean
  total_usuarios: number
}

interface Emisor {
  contribuyente_id: number
  nombre: string
  nombre_comercial: string | null
  nit: string | null
  nrc: string | null
  cod_actividad: string | null
  desc_actividad: string | null
  telefono: string | null
  correo: string | null
  tipo_establecimiento: string | null
  cod_estable_mh: string | null
  cod_estable: string | null
  cod_punto_venta_mh: string | null
  cod_punto_venta: string | null
  regimen: string | null
}

interface Actividad {
  codigo: string
  descripcion: string
}

const TIPO_LABEL: Record<string, string> = { restaurante: 'Restaurante', pos: 'Punto de Venta' }
const TIPO_COLOR: Record<string, string> = { restaurante: 'bg-orange-100 text-orange-700', pos: 'bg-indigo-100 text-indigo-700' }
const PLAN_COLOR: Record<string, string> = { basico: 'bg-gray-100 text-gray-600', profesional: 'bg-blue-100 text-blue-700', enterprise: 'bg-purple-100 text-purple-700' }

export default function Negocios() {
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [emisorTenant, setEmisorTenant] = useState<Tenant | null>(null)

  async function reload() {
    const data = await api.get<Tenant[]>('/tenants')
    setTenants(data)
    setLoading(false)
  }

  useEffect(() => { reload() }, [])

  async function handleToggle(t: Tenant) {
    await api.patch(`/tenants/${t.id}/toggle`, {})
    reload()
  }

  async function handleAmbiente(t: Tenant) {
    if (t.ambiente === '01') {
      const ok = confirm(`¿Cambiar "${t.nombre}" a MODO PRUEBA?\nLos DTEs se enviarán al ambiente de pruebas del MH.`)
      if (!ok) return
    } else {
      const ok = confirm(`¿Cambiar "${t.nombre}" a MODO PRODUCCION?\nLos DTEs se enviarán al MH en produccion. Esta accion es irreversible en operacion real.`)
      if (!ok) return
    }
    await api.patch(`/tenants/${t.id}/ambiente`, {})
    reload()
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-800">Negocios</h2>
          <p className="text-xs text-gray-500 mt-0.5">Todos los tenants registrados en el sistema</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="btn-primary"
        >
          + Nuevo negocio
        </button>
      </div>

      {loading ? (
        <div className="text-gray-400 text-sm">Cargando...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {tenants.map(t => (
            <div key={t.id} className={`bg-white rounded-xl shadow p-5 border-l-4 ${t.activo ? 'border-green-400' : 'border-gray-200'}`}>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-gray-800">{t.nombre}</h3>
                  <p className="text-xs text-gray-400 mt-0.5">ID: {t.id}</p>
                </div>
                <button
                  onClick={() => handleToggle(t)}
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${t.activo ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'}`}
                >
                  {t.activo ? 'Activo' : 'Inactivo'}
                </button>
              </div>

              <div className="flex flex-wrap gap-1.5 mb-4">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${TIPO_COLOR[t.tipo] ?? 'bg-gray-100 text-gray-600'}`}>
                  {TIPO_LABEL[t.tipo] ?? t.tipo}
                </span>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PLAN_COLOR[t.plan] ?? 'bg-gray-100 text-gray-600'}`}>
                  {t.plan}
                </span>
                <button
                  onClick={() => handleAmbiente(t)}
                  title="CAT-001 Ambiente de destino MH — clic para cambiar"
                  className={`text-xs px-2 py-0.5 rounded-full font-medium border ${
                    t.ambiente === '01'
                      ? 'bg-green-600 text-white border-green-700'
                      : 'bg-yellow-100 text-yellow-800 border-yellow-300'
                  }`}
                >
                  {t.ambiente === '01' ? '01 Produccion' : '00 Prueba'}
                </button>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  {t.total_usuarios} usuario{t.total_usuarios !== 1 ? 's' : ''}
                </div>
                <button
                  onClick={() => setEmisorTenant(t)}
                  className="text-xs px-2 py-1 bg-indigo-50 text-indigo-700 rounded-lg hover:bg-indigo-100 font-medium"
                >
                  Datos fiscales
                </button>
              </div>
            </div>
          ))}

          {tenants.length === 0 && (
            <div className="col-span-3 py-16 text-center text-gray-400">
              <p className="text-4xl mb-3">🏪</p>
              <p className="font-medium">Sin negocios registrados</p>
              <p className="text-sm mt-1">Crea el primer negocio con el boton de arriba</p>
            </div>
          )}
        </div>
      )}

      {showForm && (
        <ModalNuevoNegocio
          onClose={() => setShowForm(false)}
          onSave={() => { setShowForm(false); reload() }}
        />
      )}

      {emisorTenant && (
        <ModalEmisor
          tenant={emisorTenant}
          onClose={() => setEmisorTenant(null)}
        />
      )}
    </div>
  )
}


function ModalEmisor({ tenant, onClose }: { tenant: Tenant; onClose: () => void }) {
  const empty: Omit<Emisor, 'contribuyente_id'> = {
    nombre: tenant.nombre, nombre_comercial: null, nit: null, nrc: null,
    cod_actividad: null, desc_actividad: null, telefono: null, correo: null,
    tipo_establecimiento: '02', cod_estable_mh: null, cod_estable: null,
    cod_punto_venta_mh: null, cod_punto_venta: null, regimen: 'GEN',
  }
  const [form, setForm] = useState(empty)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [ok, setOk] = useState(false)
  const [actividades, setActividades] = useState<Actividad[]>([])
  const [actQuery, setActQuery] = useState('')
  const [actOpen, setActOpen] = useState(false)
  const actRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.get<Actividad[]>('/catalogos/actividades').then(setActividades).catch(() => {})
  }, [])

  useEffect(() => {
    api.get<Emisor>(`/tenants/${tenant.id}/emisor`)
      .then(d => {
        setForm({ ...d })
        if (d.cod_actividad && d.desc_actividad) {
          setActQuery(`${d.cod_actividad} - ${d.desc_actividad}`)
        }
      })
      .catch(() => {/* no existe aún, usar valores vacíos */})
      .finally(() => setLoading(false))
  }, [tenant.id])

  // Cerrar dropdown al hacer clic fuera
  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (actRef.current && !actRef.current.contains(e.target as Node)) setActOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
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

  function set(key: keyof typeof form, val: string) {
    setForm(f => ({ ...f, [key]: val || null }))
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault()
    setSaving(true); setError(''); setOk(false)
    try {
      await api.post(`/tenants/${tenant.id}/emisor`, form)
      setOk(true)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="font-semibold text-gray-800">Datos fiscales — {tenant.nombre}</h3>
            <p className="text-xs text-gray-500 mt-0.5">Emisor DTE para facturación electrónica</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>

        {loading ? (
          <p className="text-sm text-gray-400 py-8 text-center">Cargando...</p>
        ) : (
          <form onSubmit={handleSave} className="space-y-5">

            {/* Identificacion */}
            <section className="bg-gray-50 rounded-xl p-4 space-y-3">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Identificacion tributaria</p>
              <div className="grid grid-cols-2 gap-3">
                <Field label="NIT *">
                  <input
                    required
                    value={form.nit ?? ''}
                    onChange={e => set('nit', e.target.value)}
                    className="input"
                    placeholder="06140000000000 (14 digitos)"
                  />
                  <p className="text-xs text-gray-400 mt-0.5">9 o 14 digitos, sin guiones</p>
                </Field>
                <Field label="NRC">
                  <input value={form.nrc ?? ''} onChange={e => set('nrc', e.target.value)} className="input" placeholder="1234567 (1-8 digitos)" />
                  <p className="text-xs text-gray-400 mt-0.5">Sin guion, solo numeros</p>
                </Field>
              </div>
              <Field label="Razon social">
                <input required value={form.nombre} onChange={e => set('nombre', e.target.value)} className="input" />
              </Field>
              <Field label="Nombre comercial">
                <input value={form.nombre_comercial ?? ''} onChange={e => set('nombre_comercial', e.target.value)} className="input" />
              </Field>
              <Field label="Actividad económica (CAT-019)">
                <div ref={actRef} className="relative">
                  <input
                    value={actQuery}
                    onChange={e => { setActQuery(e.target.value); setActOpen(true) }}
                    onFocus={() => { if (actQuery.length >= 2) setActOpen(true) }}
                    className="input"
                    placeholder="Escriba código o descripción (ej: 56101 o Restaurante)"
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
                        <li
                          key={a.codigo}
                          onMouseDown={() => seleccionarActividad(a)}
                          className="px-3 py-2 hover:bg-indigo-50 cursor-pointer flex gap-2"
                        >
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
              <div className="grid grid-cols-2 gap-3">
                <Field label="Telefono">
                  <input value={form.telefono ?? ''} onChange={e => set('telefono', e.target.value)} className="input" placeholder="2222-0000" />
                </Field>
                <Field label="Correo electronico">
                  <input type="email" value={form.correo ?? ''} onChange={e => set('correo', e.target.value)} className="input" placeholder="facturacion@negocio.com" />
                </Field>
              </div>
            </section>

            {/* Establecimiento */}
            <section className="bg-gray-50 rounded-xl p-4 space-y-3">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Establecimiento MH</p>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Tipo establecimiento">
                  <select value={form.tipo_establecimiento ?? '02'} onChange={e => set('tipo_establecimiento', e.target.value)} className="input">
                    <option value="01">01 — Sucursal / Agencia</option>
                    <option value="02">02 — Casa Matriz</option>
                    <option value="04">04 — Bodega</option>
                    <option value="07">07 — Vendedor Ambulante</option>
                    <option value="20">20 — Establecimiento Virtual</option>
                  </select>
                </Field>
                <Field label="Regimen">
                  <select value={form.regimen ?? 'GEN'} onChange={e => set('regimen', e.target.value)} className="input">
                    <option value="GEN">General</option>
                    <option value="EXE">Exento</option>
                    <option value="EXP">Exportacion</option>
                  </select>
                </Field>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Cod. establecimiento MH">
                  <input value={form.cod_estable_mh ?? ''} onChange={e => set('cod_estable_mh', e.target.value)} className="input" placeholder="0001" />
                </Field>
                <Field label="Cod. establecimiento propio">
                  <input value={form.cod_estable ?? ''} onChange={e => set('cod_estable', e.target.value)} className="input" placeholder="0001" />
                </Field>
                <Field label="Cod. punto venta MH">
                  <input value={form.cod_punto_venta_mh ?? ''} onChange={e => set('cod_punto_venta_mh', e.target.value)} className="input" placeholder="0001" />
                </Field>
                <Field label="Cod. punto venta propio">
                  <input value={form.cod_punto_venta ?? ''} onChange={e => set('cod_punto_venta', e.target.value)} className="input" placeholder="0001" />
                </Field>
              </div>
            </section>

            {error && <p className="text-xs text-red-600">{error}</p>}
            {ok    && <p className="text-xs text-green-600">Datos guardados correctamente.</p>}

            <div className="flex justify-end gap-2">
              <button type="button" onClick={onClose} className="btn-secondary">Cerrar</button>
              <button type="submit" disabled={saving} className="btn-primary">
                {saving ? 'Guardando...' : 'Guardar datos fiscales'}
              </button>
            </div>
          </form>
        )}
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

function ModalNuevoNegocio({ onClose, onSave }: { onClose: () => void; onSave: () => void }) {
  const [form, setForm] = useState({
    nombre: '',
    tipo: 'restaurante',
    plan: 'profesional',
    admin_nombre: '',
    admin_email: '',
    admin_password: '',
  })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await api.post('/tenants', form)
      onSave()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al crear negocio')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg mx-4">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-semibold text-gray-800">Nuevo negocio</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Datos del negocio */}
          <div className="bg-gray-50 rounded-xl p-4 space-y-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Datos del negocio</p>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Nombre del negocio</label>
              <input
                required
                value={form.nombre}
                onChange={e => setForm(f => ({ ...f, nombre: e.target.value }))}
                className="input"
                placeholder="Ej: Restaurante El Buen Sabor"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Tipo</label>
                <select
                  value={form.tipo}
                  onChange={e => setForm(f => ({ ...f, tipo: e.target.value }))}
                  className="input"
                >
                  <option value="restaurante">Restaurante</option>
                  <option value="pos">Punto de Venta</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Plan</label>
                <select
                  value={form.plan}
                  onChange={e => setForm(f => ({ ...f, plan: e.target.value }))}
                  className="input"
                >
                  <option value="basico">Basico</option>
                  <option value="profesional">Profesional</option>
                  <option value="enterprise">Enterprise</option>
                </select>
              </div>
            </div>
          </div>

          {/* Admin del negocio */}
          <div className="bg-gray-50 rounded-xl p-4 space-y-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Usuario administrador</p>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Nombre</label>
              <input
                required
                value={form.admin_nombre}
                onChange={e => setForm(f => ({ ...f, admin_nombre: e.target.value }))}
                className="input"
                placeholder="Nombre del administrador"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Email</label>
              <input
                required type="email"
                value={form.admin_email}
                onChange={e => setForm(f => ({ ...f, admin_email: e.target.value }))}
                className="input"
                placeholder="admin@negocio.com"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Contrasena</label>
              <input
                required type="password"
                value={form.admin_password}
                onChange={e => setForm(f => ({ ...f, admin_password: e.target.value }))}
                className="input"
                placeholder="Minimo 6 caracteres"
                minLength={6}
              />
            </div>
          </div>

          {error && <p className="text-xs text-red-600">{error}</p>}

          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? 'Creando...' : 'Crear negocio'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
