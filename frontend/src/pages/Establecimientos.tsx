import { useEffect, useState, type FormEvent } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

// ── Types ─────────────────────────────────────────────────────────────────────

interface TipoEstab {
  codigo: string
  descripcion: string
}

interface Establecimiento {
  id: number
  tenant_id: number
  contribuyente_id: number
  nombre: string
  tipo: string
  tipo_descripcion: string | null
  cod_estable_mh: string | null
  cod_estable: string | null
  cod_punto_venta_mh: string | null
  cod_punto_venta: string | null
  telefono: string | null
  es_principal: boolean
  activo: boolean
}

interface Usuario {
  id: number
  nombre: string
  email: string
  rol: string
  establecimiento_id: number | null
  establecimiento_nombre: string | null
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const TIPO_COLOR: Record<string, string> = {
  '01': 'bg-blue-100 text-blue-700',
  '02': 'bg-indigo-100 text-indigo-700',
  '04': 'bg-yellow-100 text-yellow-700',
  '07': 'bg-orange-100 text-orange-700',
  '20': 'bg-purple-100 text-purple-700',
}

const ROL_COLOR: Record<string, string> = {
  admin: 'bg-red-100 text-red-700',
  supervisor: 'bg-purple-100 text-purple-700',
  cajero: 'bg-blue-100 text-blue-700',
  mesero: 'bg-green-100 text-green-700',
  cocinero: 'bg-orange-100 text-orange-700',
  vendedor: 'bg-teal-100 text-teal-700',
  consulta: 'bg-gray-100 text-gray-600',
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Establecimientos() {
  const { user } = useAuth()
  const tid = user?.tenant_id!

  const [establecimientos, setEstablecimientos] = useState<Establecimiento[]>([])
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [tipos, setTipos] = useState<TipoEstab[]>([])
  const [loading, setLoading] = useState(true)

  const [showForm, setShowForm] = useState(false)
  const [editEstab, setEditEstab] = useState<Establecimiento | null>(null)
  const [asignarEstab, setAsignarEstab] = useState<Establecimiento | null>(null)

  async function reload() {
    const [e, u, t] = await Promise.all([
      api.get<Establecimiento[]>(`/tenants/${tid}/establecimientos`),
      api.get<Usuario[]>(`/tenants/${tid}/usuarios`),
      api.get<TipoEstab[]>(`/tenants/${tid}/establecimientos/tipos`),
    ])
    setEstablecimientos(e)
    setUsuarios(u)
    setTipos(t)
    setLoading(false)
  }

  useEffect(() => { reload() }, [tid])

  async function handleDelete(e: Establecimiento) {
    if (!confirm(`¿Desactivar "${e.nombre}"?`)) return
    await api.delete(`/tenants/${tid}/establecimientos/${e.id}`)
    reload()
  }

  async function handlePrincipal(e: Establecimiento) {
    if (e.es_principal) return
    if (!confirm(`¿Marcar "${e.nombre}" como establecimiento principal?\nEl actual principal perderá ese estado.`)) return
    await api.patch(`/tenants/${tid}/establecimientos/${e.id}`, { es_principal: true })
    reload()
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-800">Establecimientos</h2>
          <p className="text-xs text-gray-500 mt-0.5">Sucursales, casa matriz, bodegas y puntos de venta</p>
        </div>
        <button onClick={() => setShowForm(true)} className="btn-primary">
          + Nuevo establecimiento
        </button>
      </div>

      {loading ? (
        <div className="text-gray-400 text-sm">Cargando...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* ── Lista de establecimientos ── */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-600">
              {establecimientos.length} establecimiento{establecimientos.length !== 1 ? 's' : ''}
            </h3>

            {establecimientos.map(e => {
              const usuariosAsignados = usuarios.filter(u => u.establecimiento_id === e.id)
              return (
                <div
                  key={e.id}
                  className={`bg-white rounded-xl shadow p-4 border-l-4 ${e.es_principal ? 'border-indigo-500' : 'border-gray-200'}`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-gray-800">{e.nombre}</span>
                      {e.es_principal && (
                        <span className="text-xs px-2 py-0.5 bg-indigo-600 text-white rounded-full font-medium">
                          Principal
                        </span>
                      )}
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${TIPO_COLOR[e.tipo] ?? 'bg-gray-100 text-gray-600'}`}>
                        {e.tipo} — {e.tipo_descripcion}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-500 mb-3">
                    {e.cod_estable_mh && <span>Cod. MH: <b className="text-gray-700">{e.cod_estable_mh}</b></span>}
                    {e.cod_estable    && <span>Cod. Interno: <b className="text-gray-700">{e.cod_estable}</b></span>}
                    {e.cod_punto_venta_mh && <span>PV MH: <b className="text-gray-700">{e.cod_punto_venta_mh}</b></span>}
                    {e.cod_punto_venta    && <span>PV: <b className="text-gray-700">{e.cod_punto_venta}</b></span>}
                    {e.telefono && <span>Tel: <b className="text-gray-700">{e.telefono}</b></span>}
                  </div>

                  {/* Usuarios asignados */}
                  <div className="flex flex-wrap gap-1 mb-3">
                    {usuariosAsignados.length === 0 ? (
                      <span className="text-xs text-gray-400 italic">Sin usuarios asignados</span>
                    ) : usuariosAsignados.map(u => (
                      <span
                        key={u.id}
                        className={`text-xs px-1.5 py-0.5 rounded font-medium ${ROL_COLOR[u.rol] ?? 'bg-gray-100 text-gray-600'}`}
                      >
                        {u.nombre}
                      </span>
                    ))}
                  </div>

                  <div className="flex gap-2">
                    {!e.es_principal && (
                      <button
                        onClick={() => handlePrincipal(e)}
                        className="text-xs px-2 py-1 bg-indigo-50 text-indigo-700 rounded hover:bg-indigo-100"
                      >
                        Marcar principal
                      </button>
                    )}
                    <button
                      onClick={() => setAsignarEstab(e)}
                      className="text-xs px-2 py-1 bg-green-50 text-green-700 rounded hover:bg-green-100"
                    >
                      Asignar usuarios
                    </button>
                    <button
                      onClick={() => setEditEstab(e)}
                      className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded hover:bg-gray-200"
                    >
                      Editar
                    </button>
                    {!e.es_principal && (
                      <button
                        onClick={() => handleDelete(e)}
                        className="text-xs px-2 py-1 bg-red-50 text-red-600 rounded hover:bg-red-100"
                      >
                        Desactivar
                      </button>
                    )}
                  </div>
                </div>
              )
            })}

            {establecimientos.length === 0 && (
              <div className="bg-white rounded-xl shadow p-8 text-center text-gray-400">
                <p className="text-3xl mb-2">🏢</p>
                <p className="font-medium">Sin establecimientos</p>
                <p className="text-sm mt-1">Crea el primero con el boton de arriba</p>
              </div>
            )}
          </div>

          {/* ── Usuarios sin establecimiento ── */}
          <div>
            <h3 className="text-sm font-semibold text-gray-600 mb-3">
              Usuarios sin establecimiento asignado
            </h3>
            <div className="bg-white rounded-xl shadow divide-y divide-gray-50">
              {usuarios.filter(u => u.establecimiento_id === null).map(u => (
                <div key={u.id} className="flex items-center justify-between px-4 py-3">
                  <div>
                    <p className="text-sm font-medium text-gray-800">{u.nombre}</p>
                    <p className="text-xs text-gray-400">{u.email}</p>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${ROL_COLOR[u.rol] ?? 'bg-gray-100 text-gray-600'}`}>
                    {u.rol}
                  </span>
                </div>
              ))}
              {usuarios.filter(u => u.establecimiento_id === null).length === 0 && (
                <p className="px-4 py-6 text-sm text-gray-400 text-center">
                  Todos los usuarios tienen establecimiento asignado
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {showForm && (
        <ModalEstablecimiento
          tid={tid}
          tipos={tipos}
          onClose={() => setShowForm(false)}
          onSave={() => { setShowForm(false); reload() }}
        />
      )}

      {editEstab && (
        <ModalEstablecimiento
          tid={tid}
          tipos={tipos}
          inicial={editEstab}
          onClose={() => setEditEstab(null)}
          onSave={() => { setEditEstab(null); reload() }}
        />
      )}

      {asignarEstab && (
        <ModalAsignar
          tid={tid}
          establecimiento={asignarEstab}
          usuarios={usuarios}
          onClose={() => setAsignarEstab(null)}
          onSave={() => { setAsignarEstab(null); reload() }}
        />
      )}
    </div>
  )
}

// ── Modal crear / editar establecimiento ──────────────────────────────────────

function ModalEstablecimiento({ tid, tipos, inicial, onClose, onSave }: {
  tid: number
  tipos: TipoEstab[]
  inicial?: Establecimiento
  onClose: () => void
  onSave: () => void
}) {
  const [form, setForm] = useState({
    nombre:             inicial?.nombre             ?? '',
    tipo:               inicial?.tipo               ?? tipos[0]?.codigo ?? '02',
    cod_estable_mh:     inicial?.cod_estable_mh     ?? '',
    cod_estable:        inicial?.cod_estable         ?? '',
    cod_punto_venta_mh: inicial?.cod_punto_venta_mh ?? '',
    cod_punto_venta:    inicial?.cod_punto_venta     ?? '',
    telefono:           inicial?.telefono            ?? '',
    es_principal:       inicial?.es_principal        ?? false,
  })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  function set(key: keyof typeof form, val: string | boolean) {
    setForm(f => ({ ...f, [key]: val }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true); setError('')
    const payload = {
      ...form,
      cod_estable_mh:     form.cod_estable_mh     || null,
      cod_estable:        form.cod_estable         || null,
      cod_punto_venta_mh: form.cod_punto_venta_mh || null,
      cod_punto_venta:    form.cod_punto_venta     || null,
      telefono:           form.telefono            || null,
    }
    try {
      if (inicial) {
        await api.patch(`/tenants/${tid}/establecimientos/${inicial.id}`, payload)
      } else {
        await api.post(`/tenants/${tid}/establecimientos`, payload)
      }
      onSave()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal title={inicial ? `Editar: ${inicial.nombre}` : 'Nuevo establecimiento'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">

        <Field label="Nombre del establecimiento">
          <input
            required
            value={form.nombre}
            onChange={e => set('nombre', e.target.value)}
            className="input"
            placeholder="Ej: Sucursal Centro, Casa Matriz"
          />
        </Field>

        <Field label="Tipo (CAT-009)">
          <select value={form.tipo} onChange={e => set('tipo', e.target.value)} className="input">
            {tipos.map(t => (
              <option key={t.codigo} value={t.codigo}>{t.codigo} — {t.descripcion}</option>
            ))}
          </select>
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Cod. establecimiento MH">
            <input
              value={form.cod_estable_mh}
              onChange={e => set('cod_estable_mh', e.target.value)}
              className="input"
              placeholder="0001"
              maxLength={4}
            />
          </Field>
          <Field label="Cod. establecimiento interno">
            <input
              value={form.cod_estable}
              onChange={e => set('cod_estable', e.target.value)}
              className="input"
              placeholder="0001"
            />
          </Field>
          <Field label="Cod. punto de venta MH">
            <input
              value={form.cod_punto_venta_mh}
              onChange={e => set('cod_punto_venta_mh', e.target.value)}
              className="input"
              placeholder="0001"
              maxLength={4}
            />
          </Field>
          <Field label="Cod. punto de venta interno">
            <input
              value={form.cod_punto_venta}
              onChange={e => set('cod_punto_venta', e.target.value)}
              className="input"
              placeholder="0001"
            />
          </Field>
        </div>

        <Field label="Telefono">
          <input
            value={form.telefono}
            onChange={e => set('telefono', e.target.value)}
            className="input"
            placeholder="2222-0000"
          />
        </Field>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={form.es_principal}
            onChange={e => set('es_principal', e.target.checked)}
            className="w-4 h-4 rounded accent-indigo-600"
          />
          <span className="text-sm text-gray-700">Marcar como establecimiento principal (DTE)</span>
        </label>

        {error && <p className="text-xs text-red-600">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? 'Guardando...' : inicial ? 'Guardar cambios' : 'Crear establecimiento'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

// ── Modal asignar usuarios a establecimiento ──────────────────────────────────

function ModalAsignar({ tid, establecimiento, usuarios, onClose, onSave }: {
  tid: number
  establecimiento: Establecimiento
  usuarios: Usuario[]
  onClose: () => void
  onSave: () => void
}) {
  // Usuarios ya asignados a ESTE establecimiento
  const asignados = new Set(
    usuarios.filter(u => u.establecimiento_id === establecimiento.id).map(u => u.id)
  )
  const [seleccionados, setSeleccionados] = useState<Set<number>>(new Set(asignados))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  function toggle(uid: number) {
    setSeleccionados(s => {
      const n = new Set(s)
      if (n.has(uid)) n.delete(uid); else n.add(uid)
      return n
    })
  }

  async function handleSave() {
    setSaving(true); setError('')
    try {
      // Para cada usuario del tenant, actualizar su establecimiento_id
      const promises: Promise<unknown>[] = []

      for (const u of usuarios) {
        const estabaAsignado = asignados.has(u.id)
        const estaSeleccionado = seleccionados.has(u.id)

        if (!estabaAsignado && estaSeleccionado) {
          // Asignar a este establecimiento
          promises.push(api.patch(`/tenants/${tid}/usuarios/${u.id}`, {
            establecimiento_id: establecimiento.id,
          }))
        } else if (estabaAsignado && !estaSeleccionado) {
          // Quitar de este establecimiento (global)
          promises.push(api.patch(`/tenants/${tid}/usuarios/${u.id}`, {
            establecimiento_id: null,
          }))
        }
      }

      await Promise.all(promises)
      onSave()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al guardar')
      setSaving(false)
    }
  }

  // Separar: usuarios libres (global o este estab) y asignados a otro
  const disponibles = usuarios.filter(
    u => u.establecimiento_id === null || u.establecimiento_id === establecimiento.id
  )
  const otroEstab = usuarios.filter(
    u => u.establecimiento_id !== null && u.establecimiento_id !== establecimiento.id
  )

  return (
    <Modal title={`Asignar usuarios — ${establecimiento.nombre}`} onClose={onClose} wide>
      <p className="text-xs text-gray-500 mb-4">
        Marca los usuarios que trabajaran en este establecimiento.
        Los usuarios asignados a otro establecimiento aparecen bloqueados.
      </p>

      <div className="space-y-1 max-h-80 overflow-y-auto pr-1 mb-4">
        {disponibles.map(u => (
          <label
            key={u.id}
            className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-gray-50 cursor-pointer"
          >
            <input
              type="checkbox"
              checked={seleccionados.has(u.id)}
              onChange={() => toggle(u.id)}
              className="w-4 h-4 rounded accent-indigo-600 flex-shrink-0"
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-800">{u.nombre}</p>
              <p className="text-xs text-gray-400">{u.email}</p>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${ROL_COLOR[u.rol] ?? 'bg-gray-100 text-gray-600'}`}>
                {u.rol}
              </span>
              {u.establecimiento_id === establecimiento.id && (
                <span className="text-xs text-indigo-600 font-medium">asignado</span>
              )}
            </div>
          </label>
        ))}

        {otroEstab.length > 0 && (
          <>
            <p className="text-xs text-gray-400 px-2 pt-3 pb-1 font-medium uppercase tracking-wide">
              Asignados a otro establecimiento
            </p>
            {otroEstab.map(u => (
              <div
                key={u.id}
                className="flex items-center gap-3 p-2.5 rounded-lg opacity-50"
              >
                <input type="checkbox" disabled className="w-4 h-4 rounded flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800">{u.nombre}</p>
                  <p className="text-xs text-gray-400">{u.establecimiento_nombre}</p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${ROL_COLOR[u.rol] ?? 'bg-gray-100 text-gray-600'}`}>
                  {u.rol}
                </span>
              </div>
            ))}
          </>
        )}

        {disponibles.length === 0 && otroEstab.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-6">Sin usuarios en este tenant</p>
        )}
      </div>

      {error && <p className="text-xs text-red-600 mb-3">{error}</p>}

      <div className="flex justify-between items-center pt-4 border-t border-gray-100">
        <span className="text-xs text-gray-500">
          {seleccionados.size} usuario{seleccionados.size !== 1 ? 's' : ''} seleccionado{seleccionados.size !== 1 ? 's' : ''}
        </span>
        <div className="flex gap-2">
          <button onClick={onClose} className="btn-secondary">Cancelar</button>
          <button onClick={handleSave} disabled={saving} className="btn-primary">
            {saving ? 'Guardando...' : 'Guardar asignacion'}
          </button>
        </div>
      </div>
    </Modal>
  )
}

// ── Helpers UI ────────────────────────────────────────────────────────────────

function Modal({ title, children, onClose, wide }: {
  title: string; children: React.ReactNode; onClose: () => void; wide?: boolean
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className={`bg-white rounded-2xl shadow-xl p-6 w-full mx-4 ${wide ? 'max-w-xl' : 'max-w-md'}`}>
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-semibold text-gray-800">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>
        {children}
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
