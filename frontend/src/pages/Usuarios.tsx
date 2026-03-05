import { useEffect, useState, type FormEvent } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

interface UsuarioTenant {
  id: number
  email: string
  nombre: string
  activo: boolean
  rol: string
  establecimiento_id: number | null
  establecimiento_nombre: string | null
  permisos: string[]
  created_at: string
}

interface Establecimiento {
  id: number
  nombre: string
  tipo: string
  tipo_descripcion: string | null
}

interface Rol {
  id: number
  nombre: string
  descripcion: string
  tipo_negocio: string
  permisos: string[]
}

interface Permiso {
  id: number
  codigo: string
  modulo: string
  accion: string
  descripcion: string
}

interface TenantInfo {
  id: number
  nombre: string
  tipo: string
  plan: string
  activo: boolean
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

export default function Usuarios() {
  const { user } = useAuth()
  const tid = user?.tenant_id!

  const [usuarios, setUsuarios] = useState<UsuarioTenant[]>([])
  const [roles, setRoles] = useState<Rol[]>([])
  const [permisos, setPermisos] = useState<Permiso[]>([])
  const [tenant, setTenant] = useState<TenantInfo | null>(null)
  const [establecimientos, setEstablecimientos] = useState<Establecimiento[]>([])
  const [loading, setLoading] = useState(true)

  const [showCreate, setShowCreate] = useState(false)
  const [editUsuario, setEditUsuario] = useState<UsuarioTenant | null>(null)
  const [showPermisos, setShowPermisos] = useState<UsuarioTenant | null>(null)
  const [showTenant, setShowTenant] = useState(false)

  async function reload() {
    const [u, r, p, t, e] = await Promise.all([
      api.get<UsuarioTenant[]>(`/tenants/${tid}/usuarios`),
      api.get<Rol[]>(`/tenants/${tid}/roles`),
      api.get<Permiso[]>(`/tenants/${tid}/permisos`),
      api.get<TenantInfo>(`/tenants/${tid}/info`),
      api.get<Establecimiento[]>(`/tenants/${tid}/establecimientos`),
    ])
    setUsuarios(u)
    setRoles(r)
    setPermisos(p)
    setTenant(t)
    setEstablecimientos(e)
    setLoading(false)
  }

  useEffect(() => { reload() }, [tid])

  async function handleToggleActivo(u: UsuarioTenant) {
    await api.patch(`/tenants/${tid}/usuarios/${u.id}`, { activo: !u.activo })
    reload()
  }

  const modulosAgrupados = permisos.reduce<Record<string, Permiso[]>>((acc, p) => {
    if (!acc[p.modulo]) acc[p.modulo] = []
    acc[p.modulo].push(p)
    return acc
  }, {})

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-800">Usuarios y Roles</h2>
          {tenant && (
            <p className="text-sm text-gray-500 mt-0.5">
              {tenant.nombre} &mdash;
              <span className={`ml-1 font-medium ${tenant.tipo === 'pos' ? 'text-indigo-600' : 'text-orange-600'}`}>
                {tenant.tipo === 'pos' ? 'Punto de Venta' : 'Restaurante'}
              </span>
            </p>
          )}
        </div>
        <div className="flex gap-2">
          {user?.rol === 'admin' && (
            <button
              onClick={() => setShowTenant(true)}
              className="px-3 py-1.5 text-sm bg-white border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-700"
            >
              Config. negocio
            </button>
          )}
          <button
            onClick={() => setShowCreate(true)}
            className="px-4 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            + Nuevo usuario
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-gray-400 text-sm">Cargando...</div>
      ) : (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
              <tr>
                <th className="px-4 py-3 text-left">Usuario</th>
                <th className="px-4 py-3 text-left">Email</th>
                <th className="px-4 py-3 text-left">Rol</th>
                <th className="px-4 py-3 text-left">Establecimiento</th>
                <th className="px-4 py-3 text-left">Estado</th>
                <th className="px-4 py-3 text-left">Permisos</th>
                <th className="px-4 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {usuarios.map(u => (
                <tr key={u.id} className="hover:bg-gray-50/50">
                  <td className="px-4 py-3 font-medium text-gray-800">{u.nombre}</td>
                  <td className="px-4 py-3 text-gray-500">{u.email}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${ROL_COLOR[u.rol] ?? 'bg-gray-100 text-gray-600'}`}>
                      {u.rol}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs">
                    {u.establecimiento_nombre
                      ? <span className="text-indigo-700 font-medium">{u.establecimiento_nombre}</span>
                      : <span className="text-gray-400 italic">Todos</span>
                    }
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleToggleActivo(u)}
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${u.activo ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'}`}
                    >
                      {u.activo ? 'Activo' : 'Inactivo'}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{u.permisos.length} permisos</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-1">
                      <button
                        onClick={() => setShowPermisos(u)}
                        className="px-2 py-1 text-xs bg-purple-50 text-purple-700 rounded hover:bg-purple-100"
                      >
                        Permisos
                      </button>
                      <button
                        onClick={() => setEditUsuario(u)}
                        className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200"
                      >
                        Editar
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {usuarios.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-400">Sin usuarios registrados</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <ModalCrear
          tid={tid}
          roles={roles}
          establecimientos={establecimientos}
          onClose={() => setShowCreate(false)}
          onSave={() => { setShowCreate(false); reload() }}
        />
      )}

      {editUsuario && (
        <ModalEditar
          tid={tid}
          usuario={editUsuario}
          roles={roles}
          establecimientos={establecimientos}
          onClose={() => setEditUsuario(null)}
          onSave={() => { setEditUsuario(null); reload() }}
        />
      )}

      {showPermisos && (
        <ModalPermisos
          tid={tid}
          usuario={showPermisos}
          modulosAgrupados={modulosAgrupados}
          onClose={() => setShowPermisos(null)}
          onSave={() => { setShowPermisos(null); reload() }}
        />
      )}

      {showTenant && tenant && (
        <ModalTenant
          tid={tid}
          tenant={tenant}
          onClose={() => setShowTenant(false)}
          onSave={() => { setShowTenant(false); reload() }}
        />
      )}
    </div>
  )
}


// ── Modales ──────────────────────────────────────────────────────────────────

function ModalCrear({ tid, roles, establecimientos, onClose, onSave }: {
  tid: number; roles: Rol[]; establecimientos: Establecimiento[]
  onClose: () => void; onSave: () => void
}) {
  const [form, setForm] = useState({
    nombre: '', email: '', password: '',
    rol: roles[0]?.nombre ?? 'consulta',
    establecimiento_id: '' as string | number,
  })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const payload = {
        ...form,
        establecimiento_id: form.establecimiento_id !== '' ? Number(form.establecimiento_id) : null,
      }
      await api.post(`/tenants/${tid}/usuarios`, payload)
      onSave()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al crear usuario')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal title="Nuevo usuario" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Nombre">
          <input
            required
            value={form.nombre}
            onChange={e => setForm(f => ({ ...f, nombre: e.target.value }))}
            className="input"
            placeholder="Nombre completo"
          />
        </Field>
        <Field label="Email">
          <input
            required type="email"
            value={form.email}
            onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
            className="input"
            placeholder="correo@ejemplo.com"
          />
        </Field>
        <Field label="Contraseña">
          <input
            required type="password"
            value={form.password}
            onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
            className="input"
            placeholder="Contraseña"
          />
        </Field>
        <Field label="Rol">
          <select value={form.rol} onChange={e => setForm(f => ({ ...f, rol: e.target.value }))} className="input">
            {roles.map(r => (
              <option key={r.id} value={r.nombre}>{r.nombre} — {r.descripcion}</option>
            ))}
          </select>
        </Field>
        <Field label="Establecimiento">
          <select
            value={form.establecimiento_id}
            onChange={e => setForm(f => ({ ...f, establecimiento_id: e.target.value }))}
            className="input"
          >
            <option value="">Todos los establecimientos (global)</option>
            {establecimientos.map(e => (
              <option key={e.id} value={e.id}>{e.nombre} — {e.tipo_descripcion ?? e.tipo}</option>
            ))}
          </select>
          <p className="text-xs text-gray-400 mt-0.5">Dejar en blanco para admin/supervisor con acceso global</p>
        </Field>
        {error && <p className="text-xs text-red-600">{error}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? 'Guardando...' : 'Crear usuario'}
          </button>
        </div>
      </form>
    </Modal>
  )
}


function ModalEditar({ tid, usuario, roles, establecimientos, onClose, onSave }: {
  tid: number; usuario: UsuarioTenant; roles: Rol[]; establecimientos: Establecimiento[]
  onClose: () => void; onSave: () => void
}) {
  const [form, setForm] = useState({
    nombre: usuario.nombre,
    email: usuario.email,
    password: '',
    rol: usuario.rol,
    activo: usuario.activo,
    establecimiento_id: usuario.establecimiento_id ?? ('' as string | number),
  })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError('')
    const payload: Record<string, unknown> = {
      nombre: form.nombre, email: form.email, rol: form.rol, activo: form.activo,
      establecimiento_id: form.establecimiento_id !== '' ? Number(form.establecimiento_id) : null,
    }
    if (form.password) payload.password = form.password
    try {
      await api.patch(`/tenants/${tid}/usuarios/${usuario.id}`, payload)
      onSave()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al actualizar')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal title={`Editar: ${usuario.nombre}`} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Nombre">
          <input required value={form.nombre} onChange={e => setForm(f => ({ ...f, nombre: e.target.value }))} className="input" />
        </Field>
        <Field label="Email">
          <input required type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} className="input" />
        </Field>
        <Field label="Nueva contraseña (dejar en blanco para no cambiar)">
          <input type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} className="input" placeholder="••••••••" />
        </Field>
        <Field label="Rol">
          <select value={form.rol} onChange={e => setForm(f => ({ ...f, rol: e.target.value }))} className="input">
            {roles.map(r => (
              <option key={r.id} value={r.nombre}>{r.nombre} — {r.descripcion}</option>
            ))}
          </select>
        </Field>
        <Field label="Establecimiento">
          <select
            value={form.establecimiento_id}
            onChange={e => setForm(f => ({ ...f, establecimiento_id: e.target.value }))}
            className="input"
          >
            <option value="">Todos los establecimientos (global)</option>
            {establecimientos.map(e => (
              <option key={e.id} value={e.id}>{e.nombre} — {e.tipo_descripcion ?? e.tipo}</option>
            ))}
          </select>
        </Field>
        <Field label="Estado">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.activo} onChange={e => setForm(f => ({ ...f, activo: e.target.checked }))} className="w-4 h-4 rounded" />
            <span className="text-sm text-gray-700">Usuario activo</span>
          </label>
        </Field>
        {error && <p className="text-xs text-red-600">{error}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? 'Guardando...' : 'Guardar cambios'}
          </button>
        </div>
      </form>
    </Modal>
  )
}


function ModalPermisos({ tid, usuario, modulosAgrupados, onClose, onSave }: {
  tid: number; usuario: UsuarioTenant
  modulosAgrupados: Record<string, Permiso[]>
  onClose: () => void; onSave: () => void
}) {
  const [selected, setSelected] = useState<Set<string>>(new Set(usuario.permisos))
  const [saving, setSaving] = useState(false)

  function toggle(cod: string) {
    setSelected(s => {
      const n = new Set(s)
      if (n.has(cod)) n.delete(cod); else n.add(cod)
      return n
    })
  }

  async function handleSave() {
    setSaving(true)
    await api.post(`/tenants/${tid}/usuarios/${usuario.id}/permisos`, [...selected])
    setSaving(false)
    onSave()
  }

  return (
    <Modal title={`Permisos: ${usuario.nombre}`} onClose={onClose} wide>
      <p className="text-xs text-gray-500 mb-4">
        Rol base: <span className="font-medium">{usuario.rol}</span> — Los permisos marcados son los efectivos (rol + overrides individuales).
      </p>
      <div className="space-y-4 max-h-96 overflow-y-auto pr-1">
        {Object.entries(modulosAgrupados).map(([modulo, perms]) => (
          <div key={modulo}>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{modulo}</p>
            <div className="grid grid-cols-2 gap-1.5">
              {perms.map(p => (
                <label key={p.id} className="flex items-center gap-2 cursor-pointer p-1.5 rounded hover:bg-gray-50">
                  <input
                    type="checkbox"
                    checked={selected.has(p.codigo)}
                    onChange={() => toggle(p.codigo)}
                    className="w-4 h-4 rounded accent-indigo-600"
                  />
                  <span className="text-xs text-gray-700">{p.descripcion || p.codigo}</span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="flex justify-end gap-2 pt-4 border-t border-gray-100 mt-4">
        <button onClick={onClose} className="btn-secondary">Cancelar</button>
        <button onClick={handleSave} disabled={saving} className="btn-primary">
          {saving ? 'Guardando...' : 'Guardar permisos'}
        </button>
      </div>
    </Modal>
  )
}


function ModalTenant({ tid, tenant, onClose, onSave }: {
  tid: number; tenant: TenantInfo
  onClose: () => void; onSave: () => void
}) {
  const [nombre, setNombre] = useState(tenant.nombre)
  const [tipo, setTipo] = useState(tenant.tipo)
  const [saving, setSaving] = useState(false)

  async function handleSave() {
    setSaving(true)
    await api.patch(`/tenants/${tid}/info`, { nombre, tipo })
    setSaving(false)
    onSave()
    window.location.reload()
  }

  return (
    <Modal title="Configuracion del negocio" onClose={onClose}>
      <div className="space-y-4">
        <Field label="Nombre del negocio">
          <input value={nombre} onChange={e => setNombre(e.target.value)} className="input" />
        </Field>
        <Field label="Tipo de negocio">
          <div className="flex gap-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="radio" name="tipo" value="restaurante" checked={tipo === 'restaurante'} onChange={() => setTipo('restaurante')} className="w-4 h-4 accent-orange-600" />
              <span className="text-sm text-gray-700">Restaurante</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="radio" name="tipo" value="pos" checked={tipo === 'pos'} onChange={() => setTipo('pos')} className="w-4 h-4 accent-indigo-600" />
              <span className="text-sm text-gray-700">Punto de Venta (POS)</span>
            </label>
          </div>
        </Field>
        <p className="text-xs text-yellow-700 bg-yellow-50 px-3 py-2 rounded-lg">
          Cambiar el tipo de negocio recargara la pagina para actualizar el menu lateral.
        </p>
        <div className="flex justify-end gap-2 pt-2">
          <button onClick={onClose} className="btn-secondary">Cancelar</button>
          <button onClick={handleSave} disabled={saving} className="btn-primary">
            {saving ? 'Guardando...' : 'Guardar'}
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
      <div className={`bg-white rounded-2xl shadow-xl p-6 w-full mx-4 ${wide ? 'max-w-2xl' : 'max-w-md'}`}>
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
