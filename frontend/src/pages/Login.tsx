import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth, type AuthUser } from '../context/AuthContext'
import { api } from '../api/client'

interface TenantOpcion { id: number; nombre: string; tipo: string }

export default function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [tenantId, setTenantId] = useState('2')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  // Paso 2 para superadmin
  const [superToken, setSuperToken]     = useState<string | null>(null)
  const [tenants, setTenants]           = useState<TenantOpcion[]>([])
  const [tenantSel, setTenantSel]       = useState<string>('')
  const [superData, setSuperData]       = useState<AuthUser | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const resp = await login(email, password, Number(tenantId) || undefined)
      if (resp.is_superadmin && !resp.tenant_id) {
        // Superadmin sin tenant: cargar lista de negocios
        setSuperData(resp)
        setSuperToken(resp.access_token)
        const lista = await api.get<TenantOpcion[]>('/auth/tenants', resp.access_token)
        setTenants(lista)
        if (lista.length > 0) setTenantSel(String(lista[0].id))
      }
      // Si tiene tenant_id ya se guardó la sesión en login() y useEffect navegará
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  async function handleSeleccionarTenant(e: FormEvent) {
    e.preventDefault()
    if (!tenantSel || !superData) return
    setError('')
    setLoading(true)
    try {
      await login(superData.email, password, Number(tenantSel))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (user?.tenant_id) navigate('/')
  }, [user, navigate])

  const inputCls = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500'

  // ── Paso 2: selector de negocio para superadmin ────────────────────────────
  if (superToken && tenants.length > 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-900 to-indigo-700 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8">
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-14 h-14 bg-purple-100 rounded-2xl mb-3">
              <svg className="w-7 h-7 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-2 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-gray-800">Selecciona el negocio</h2>
            <p className="text-sm text-gray-500 mt-1">
              Bienvenido, <span className="font-medium text-purple-700">{superData?.nombre}</span>
              <span className="ml-2 text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">Superadmin</span>
            </p>
          </div>

          <form onSubmit={handleSeleccionarTenant} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Negocio</label>
              <select
                value={tenantSel}
                onChange={e => setTenantSel(e.target.value)}
                className={inputCls}
                required
              >
                {tenants.map(t => (
                  <option key={t.id} value={t.id}>
                    {t.nombre} — {t.tipo === 'restaurante' ? 'Restaurante' : 'Punto de Venta'}
                  </option>
                ))}
              </select>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-3 py-2">{error}</div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-purple-300 text-white font-medium py-2.5 rounded-lg transition text-sm"
            >
              {loading ? 'Ingresando...' : 'Entrar al negocio'}
            </button>
            <button
              type="button"
              onClick={() => { setSuperToken(null); setTenants([]); setSuperData(null) }}
              className="w-full text-sm text-gray-500 hover:text-gray-700"
            >
              Volver
            </button>
          </form>
        </div>
      </div>
    )
  }

  // ── Paso 1: login normal ───────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 to-indigo-700 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-indigo-100 rounded-2xl mb-4">
            <svg className="w-8 h-8 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-800">ErpMovil</h1>
          <p className="text-sm text-gray-500 mt-1">Sistema POS para restaurantes</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className={inputCls}
              placeholder="admin@erpmovil.com"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className={inputCls}
              placeholder="••••••••"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">ID de Negocio</label>
            <input
              type="number"
              value={tenantId}
              onChange={e => setTenantId(e.target.value)}
              className={inputCls}
              placeholder="Deja en 0 si eres superadmin"
            />
            <p className="text-xs text-gray-400 mt-1">Superadmins: ingresa 0 para ver todos los negocios</p>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-3 py-2">{error}</div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white font-medium py-2.5 rounded-lg transition text-sm"
          >
            {loading ? 'Ingresando...' : 'Ingresar'}
          </button>
        </form>
      </div>
    </div>
  )
}
