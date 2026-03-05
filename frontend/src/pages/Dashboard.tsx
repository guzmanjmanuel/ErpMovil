import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

interface Pedido {
  id: number; estado: string; total: string; canal: string; created_at: string
}
interface Mesa { id: number; estado: string }

export default function Dashboard() {
  const { user } = useAuth()
  return user?.tipo_negocio === 'pos'
    ? <DashboardPOS />
    : <DashboardRestaurante />
}


// ── Dashboard Restaurante ─────────────────────────────────────────────────────

function DashboardRestaurante() {
  const { user } = useAuth()
  const tid = user?.tenant_id
  const [pedidos, setPedidos] = useState<Pedido[]>([])
  const [mesas,   setMesas]   = useState<Mesa[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!tid) return
    Promise.all([
      api.get<Pedido[]>(`/tenants/${tid}/pedidos?limit=20`),
      api.get<Mesa[]>(`/tenants/${tid}/mesas`),
    ]).then(([p, m]) => { setPedidos(p); setMesas(m) })
      .finally(() => setLoading(false))
  }, [tid])

  const mesasOcupadas    = mesas.filter(m => m.estado === 'ocupada').length
  const mesasDisponibles = mesas.filter(m => m.estado === 'disponible').length
  const pedidosActivos   = pedidos.filter(p => !['pagado','anulado'].includes(p.estado)).length
  const enCocina         = pedidos.filter(p => p.estado === 'en_preparacion').length
  const ventasHoy        = pedidos.filter(p => p.estado === 'pagado').reduce((s, p) => s + parseFloat(p.total), 0)

  const cards = [
    { label: 'Mesas ocupadas',    value: mesasOcupadas,              icon: 'M4 6h16M4 10h16M4 14h16M4 18h16',  color: 'bg-orange-500' },
    { label: 'Mesas disponibles', value: mesasDisponibles,           icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2', color: 'bg-green-500' },
    { label: 'Pedidos activos',   value: pedidosActivos,             icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2', color: 'bg-blue-500' },
    { label: 'En cocina',         value: enCocina,                   icon: 'M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z', color: 'bg-red-500' },
    { label: 'Ventas del dia',    value: `$${ventasHoy.toFixed(2)}`, icon: 'M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z', color: 'bg-indigo-500' },
  ]

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <span className="text-2xl">🍽</span>
        <div>
          <h2 className="text-xl font-bold text-gray-800">Dashboard — Restaurante</h2>
          <p className="text-xs text-gray-500">Vista general del negocio</p>
        </div>
      </div>

      {loading ? (
        <div className="text-gray-400 text-sm">Cargando...</div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
            {cards.map(c => (
              <div key={c.label} className="bg-white rounded-xl shadow p-5">
                <div className={`inline-flex w-10 h-10 ${c.color} rounded-lg items-center justify-center mb-3`}>
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={c.icon} />
                  </svg>
                </div>
                <p className="text-2xl font-bold text-gray-800">{c.value}</p>
                <p className="text-xs text-gray-500 mt-1">{c.label}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <PanelMesas mesas={mesas} />
            <PanelPedidos pedidos={pedidos} />
          </div>
        </>
      )}
    </div>
  )
}


// ── Dashboard POS ─────────────────────────────────────────────────────────────

interface ProductoVenta { nombre: string; cantidad: number; total: number }

function DashboardPOS() {
  const { user } = useAuth()
  const tid = user?.tenant_id
  const [pedidos, setPedidos]   = useState<Pedido[]>([])
  const [loading, setLoading]   = useState(true)

  useEffect(() => {
    if (!tid) return
    api.get<Pedido[]>(`/tenants/${tid}/pedidos?limit=50`)
      .then(p => setPedidos(p))
      .finally(() => setLoading(false))
  }, [tid])

  const pagados       = pedidos.filter(p => p.estado === 'pagado')
  const ventasHoy     = pagados.reduce((s, p) => s + parseFloat(p.total), 0)
  const transacciones = pagados.length
  const ticketProm    = transacciones > 0 ? ventasHoy / transacciones : 0
  const pendientes    = pedidos.filter(p => !['pagado','anulado'].includes(p.estado)).length

  const cards = [
    { label: 'Ventas del dia',   value: `$${ventasHoy.toFixed(2)}`,    color: 'bg-indigo-600', icon: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
    { label: 'Transacciones',    value: transacciones,                  color: 'bg-teal-500',   icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2' },
    { label: 'Ticket promedio',  value: `$${ticketProm.toFixed(2)}`,   color: 'bg-purple-500', icon: 'M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z' },
    { label: 'Ventas pendientes',value: pendientes,                     color: 'bg-yellow-500', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
  ]

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <span className="text-2xl">🏪</span>
        <div>
          <h2 className="text-xl font-bold text-gray-800">Dashboard — Punto de Venta</h2>
          <p className="text-xs text-gray-500">Resumen de ventas del dia</p>
        </div>
      </div>

      {loading ? (
        <div className="text-gray-400 text-sm">Cargando...</div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {cards.map(c => (
              <div key={c.label} className="bg-white rounded-xl shadow p-5">
                <div className={`inline-flex w-10 h-10 ${c.color} rounded-lg items-center justify-center mb-3`}>
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={c.icon} />
                  </svg>
                </div>
                <p className="text-2xl font-bold text-gray-800">{c.value}</p>
                <p className="text-xs text-gray-500 mt-1">{c.label}</p>
              </div>
            ))}
          </div>

          <PanelPedidos pedidos={pedidos} />
        </>
      )}
    </div>
  )
}


// ── Paneles compartidos ───────────────────────────────────────────────────────

function PanelMesas({ mesas }: { mesas: Mesa[] }) {
  const grupos: Record<string, string> = {
    disponible: 'bg-green-100 text-green-700',
    ocupada:    'bg-orange-100 text-orange-700',
    reservada:  'bg-blue-100 text-blue-700',
    cerrada:    'bg-gray-100 text-gray-500',
  }
  return (
    <div className="bg-white rounded-xl shadow">
      <div className="px-5 py-4 border-b border-gray-100">
        <h3 className="font-semibold text-gray-700 text-sm">Estado de mesas ({mesas.length})</h3>
      </div>
      <div className="p-4 grid grid-cols-5 gap-2">
        {mesas.map(m => (
          <div
            key={m.id}
            className={`rounded-lg p-2 text-center text-xs font-medium ${grupos[m.estado] ?? 'bg-gray-100 text-gray-500'}`}
          >
            M{m.id}
          </div>
        ))}
        {mesas.length === 0 && (
          <p className="col-span-5 py-6 text-center text-gray-400 text-sm">Sin mesas configuradas</p>
        )}
      </div>
    </div>
  )
}

function PanelPedidos({ pedidos }: { pedidos: Pedido[] }) {
  const colors: Record<string, string> = {
    borrador:       'bg-gray-100 text-gray-600',
    confirmado:     'bg-blue-100 text-blue-700',
    en_preparacion: 'bg-yellow-100 text-yellow-700',
    listo:          'bg-teal-100 text-teal-700',
    entregado:      'bg-green-100 text-green-700',
    pagado:         'bg-indigo-100 text-indigo-700',
    anulado:        'bg-red-100 text-red-700',
  }
  return (
    <div className="bg-white rounded-xl shadow">
      <div className="px-5 py-4 border-b border-gray-100">
        <h3 className="font-semibold text-gray-700 text-sm">Ultimas ventas</h3>
      </div>
      <div className="divide-y divide-gray-50">
        {pedidos.slice(0, 8).map(p => (
          <div key={p.id} className="flex items-center justify-between px-5 py-3 text-sm">
            <div className="flex items-center gap-3">
              <span className="font-mono text-gray-400 text-xs">#{p.id}</span>
              <span className="capitalize text-gray-600">{p.canal}</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-gray-800 font-medium">${parseFloat(p.total).toFixed(2)}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${colors[p.estado] ?? 'bg-gray-100 text-gray-600'}`}>
                {p.estado}
              </span>
            </div>
          </div>
        ))}
        {pedidos.length === 0 && (
          <p className="px-5 py-6 text-sm text-gray-400 text-center">Sin ventas registradas</p>
        )}
      </div>
    </div>
  )
}
