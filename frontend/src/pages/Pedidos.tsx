import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

interface PedidoItem { id: number; nombre?: string; cantidad: string; precio_unitario: string; subtotal: string; estado: string; menu_item_id: number }
interface Pedido     { id: number; canal: string; estado: string; total: string; subtotal: string; mesa_id?: number; nombre_pickup?: string; created_at: string; items: PedidoItem[] }

const ESTADOS = ['todos', 'borrador', 'confirmado', 'en_preparacion', 'listo', 'entregado', 'pagado', 'anulado']

const ESTADO_COLOR: Record<string, string> = {
  borrador:       'bg-gray-100 text-gray-600',
  confirmado:     'bg-blue-100 text-blue-700',
  en_preparacion: 'bg-yellow-100 text-yellow-700',
  listo:          'bg-teal-100 text-teal-700',
  entregado:      'bg-green-100 text-green-700',
  pagado:         'bg-indigo-100 text-indigo-700',
  anulado:        'bg-red-100 text-red-700',
}

const NEXT_ESTADO: Record<string, string> = {
  borrador:       'confirmado',
  confirmado:     'en_preparacion',
  en_preparacion: 'listo',
  listo:          'entregado',
  entregado:      'pagado',
}

export default function Pedidos() {
  const { user } = useAuth()
  const tid = user!.tenant_id
  const [pedidos,  setPedidos]  = useState<Pedido[]>([])
  const [filtro,   setFiltro]   = useState('todos')
  const [selected, setSelected] = useState<Pedido | null>(null)
  const [loading,  setLoading]  = useState(true)

  async function cargar() {
    const data = await api.get<Pedido[]>(`/tenants/${tid}/pedidos?limit=50`)
    setPedidos(data)
    setLoading(false)
  }

  useEffect(() => { cargar() }, [])

  async function avanzarEstado(pedido: Pedido) {
    const next = NEXT_ESTADO[pedido.estado]
    if (!next) return
    await api.patch(`/tenants/${tid}/pedidos/${pedido.id}/estado`, { estado: next })
    cargar()
    setSelected(prev => prev?.id === pedido.id ? { ...prev, estado: next } : prev)
  }

  async function anular(pedido: Pedido) {
    if (!confirm('¿Anular este pedido?')) return
    await api.patch(`/tenants/${tid}/pedidos/${pedido.id}/estado`, { estado: 'anulado' })
    cargar()
    setSelected(null)
  }

  const filtrados = filtro === 'todos' ? pedidos : pedidos.filter(p => p.estado === filtro)

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-800">Pedidos</h2>
        <button onClick={cargar} className="text-xs text-indigo-600 hover:underline">Actualizar</button>
      </div>

      {/* Filtros */}
      <div className="flex gap-2 flex-wrap mb-4">
        {ESTADOS.map(e => (
          <button
            key={e}
            onClick={() => setFiltro(e)}
            className={`text-xs px-3 py-1.5 rounded-full border capitalize transition ${
              filtro === e ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-300 hover:border-indigo-400'
            }`}
          >
            {e}
          </button>
        ))}
      </div>

      <div className="flex gap-4 flex-1 min-h-0">
        {/* Lista */}
        <div className="flex-1 overflow-auto space-y-2">
          {loading ? (
            <p className="text-gray-400 text-sm">Cargando...</p>
          ) : filtrados.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-12">Sin pedidos.</p>
          ) : filtrados.map(p => (
            <div
              key={p.id}
              onClick={() => setSelected(p)}
              className={`bg-white rounded-xl p-4 shadow-sm border cursor-pointer hover:shadow-md transition ${
                selected?.id === p.id ? 'border-indigo-400' : 'border-gray-100'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-gray-400">#{p.id}</span>
                  <span className="text-sm font-medium text-gray-700 capitalize">{p.canal}</span>
                  {p.mesa_id && <span className="text-xs text-gray-500">Mesa {p.mesa_id}</span>}
                  {p.nombre_pickup && <span className="text-xs text-gray-500">{p.nombre_pickup}</span>}
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-bold text-gray-800">${parseFloat(p.total).toFixed(2)}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${ESTADO_COLOR[p.estado]}`}>{p.estado}</span>
                </div>
              </div>
              <p className="text-xs text-gray-400 mt-1">{new Date(p.created_at).toLocaleString()}</p>
            </div>
          ))}
        </div>

        {/* Detalle */}
        {selected && (
          <div className="w-72 bg-white rounded-xl shadow border border-gray-100 flex flex-col">
            <div className="p-4 border-b border-gray-100">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-gray-800">Pedido #{selected.id}</h3>
                <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-600">✕</button>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full mt-1 inline-block ${ESTADO_COLOR[selected.estado]}`}>
                {selected.estado}
              </span>
            </div>

            <div className="flex-1 overflow-auto p-4 space-y-2">
              {selected.items.map(item => (
                <div key={item.id} className="flex justify-between text-sm">
                  <span className="text-gray-600">{item.cantidad}x item#{item.menu_item_id}</span>
                  <span className="text-gray-800">${parseFloat(item.subtotal).toFixed(2)}</span>
                </div>
              ))}
            </div>

            <div className="p-4 border-t border-gray-100">
              <div className="flex justify-between text-sm font-bold mb-3">
                <span>Total</span>
                <span>${parseFloat(selected.total).toFixed(2)}</span>
              </div>
              <div className="space-y-2">
                {NEXT_ESTADO[selected.estado] && (
                  <button
                    onClick={() => avanzarEstado(selected)}
                    className="w-full bg-indigo-600 hover:bg-indigo-700 text-white text-sm py-2 rounded-lg capitalize"
                  >
                    → {NEXT_ESTADO[selected.estado]}
                  </button>
                )}
                {!['pagado', 'anulado'].includes(selected.estado) && (
                  <button
                    onClick={() => anular(selected)}
                    className="w-full bg-red-50 hover:bg-red-100 text-red-600 text-sm py-2 rounded-lg"
                  >
                    Anular
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
