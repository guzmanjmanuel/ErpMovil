import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

interface Pedido { id: number; estado: string; total: string; canal: string; created_at: string }
interface Mesa   { id: number; estado: string }

export default function Dashboard() {
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

  const mesasOcupadas   = mesas.filter(m => m.estado === 'ocupada').length
  const mesasDisponibles = mesas.filter(m => m.estado === 'disponible').length
  const pedidosHoy      = pedidos.filter(p => p.estado !== 'anulado').length
  const ventasHoy       = pedidos
    .filter(p => p.estado === 'pagado')
    .reduce((s, p) => s + parseFloat(p.total), 0)

  const cards = [
    { label: 'Mesas ocupadas',    value: mesasOcupadas,               color: 'bg-orange-500' },
    { label: 'Mesas disponibles', value: mesasDisponibles,            color: 'bg-green-500'  },
    { label: 'Pedidos activos',   value: pedidosHoy,                  color: 'bg-blue-500'   },
    { label: 'Ventas del día',    value: `$${ventasHoy.toFixed(2)}`,  color: 'bg-indigo-500' },
  ]

  return (
    <div className="p-6">
      <h2 className="text-xl font-bold text-gray-800 mb-6">Dashboard</h2>

      {loading ? (
        <div className="text-gray-400 text-sm">Cargando...</div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {cards.map(c => (
              <div key={c.label} className="bg-white rounded-xl shadow p-5">
                <div className={`inline-flex w-10 h-10 ${c.color} rounded-lg items-center justify-center mb-3`}>
                  <div className="w-4 h-4 bg-white/40 rounded" />
                </div>
                <p className="text-2xl font-bold text-gray-800">{c.value}</p>
                <p className="text-xs text-gray-500 mt-1">{c.label}</p>
              </div>
            ))}
          </div>

          <div className="bg-white rounded-xl shadow">
            <div className="px-5 py-4 border-b border-gray-100">
              <h3 className="font-semibold text-gray-700 text-sm">Últimos pedidos</h3>
            </div>
            <div className="divide-y divide-gray-50">
              {pedidos.slice(0, 10).map(p => (
                <div key={p.id} className="flex items-center justify-between px-5 py-3 text-sm">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-gray-400 text-xs">#{p.id}</span>
                    <span className="capitalize text-gray-600">{p.canal}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-gray-800 font-medium">${parseFloat(p.total).toFixed(2)}</span>
                    <EstadoBadge estado={p.estado} />
                  </div>
                </div>
              ))}
              {pedidos.length === 0 && (
                <p className="px-5 py-6 text-sm text-gray-400 text-center">Sin pedidos registrados</p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function EstadoBadge({ estado }: { estado: string }) {
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
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${colors[estado] ?? 'bg-gray-100 text-gray-600'}`}>
      {estado}
    </span>
  )
}
