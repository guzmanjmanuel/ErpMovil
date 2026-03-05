import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

interface AreaCocina { id: number; nombre: string }
interface Comanda { id: number; pedido_id: number; area_cocina_id?: number; estado: string; created_at: string }

const ESTADO_BG: Record<string, string> = {
  pendiente:      'bg-yellow-50  border-yellow-300',
  en_preparacion: 'bg-blue-50    border-blue-300',
  listo:          'bg-green-50   border-green-300',
  entregado:      'bg-gray-50    border-gray-200',
}

const NEXT: Record<string, string> = {
  pendiente:      'en_preparacion',
  en_preparacion: 'listo',
  listo:          'entregado',
}

export default function KDS() {
  const { user } = useAuth()
  const tid = user!.tenant_id
  const [areas,    setAreas]    = useState<AreaCocina[]>([])
  const [comandas, setComandas] = useState<Comanda[]>([])
  const [areaFiltro, setAreaFiltro] = useState<number | null>(null)
  const [loading, setLoading]   = useState(true)

  async function cargar() {
    const [a, c] = await Promise.all([
      api.get<{id:number;nombre:string}[]>(`/tenants/${tid}/kds/areas`),
      api.get<Comanda[]>(`/tenants/${tid}/kds/comandas`),
    ])
    setAreas(a)
    setComandas(c.filter(c => c.estado !== 'entregado'))
    setLoading(false)
  }

  useEffect(() => {
    cargar()
    const interval = setInterval(cargar, 15000)
    return () => clearInterval(interval)
  }, [])

  async function avanzar(comanda: Comanda) {
    const next = NEXT[comanda.estado]
    if (!next) return
    await api.patch(`/tenants/${tid}/kds/comandas/${comanda.id}/estado`, { estado: next })
    cargar()
  }

  const filtradas = areaFiltro
    ? comandas.filter(c => c.area_cocina_id === areaFiltro)
    : comandas

  const tiempoTranscurrido = (fecha: string) => {
    const mins = Math.floor((Date.now() - new Date(fecha).getTime()) / 60000)
    return mins < 1 ? 'Ahora' : `${mins} min`
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-800">Cocina (KDS)</h2>
        <button onClick={cargar} className="text-xs text-indigo-600 hover:underline">Actualizar</button>
      </div>

      {/* Filtro áreas */}
      <div className="flex gap-2 mb-6 flex-wrap">
        <button
          onClick={() => setAreaFiltro(null)}
          className={`text-xs px-3 py-1.5 rounded-full border ${areaFiltro === null ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white border-gray-300 text-gray-600'}`}
        >
          Todas
        </button>
        {areas.map(a => (
          <button
            key={a.id}
            onClick={() => setAreaFiltro(a.id)}
            className={`text-xs px-3 py-1.5 rounded-full border ${areaFiltro === a.id ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white border-gray-300 text-gray-600'}`}
          >
            {a.nombre}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-gray-400 text-sm">Cargando...</p>
      ) : filtradas.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-4xl mb-3">✅</p>
          <p className="text-gray-500">Sin comandas pendientes</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtradas.map(c => (
            <div key={c.id} className={`rounded-xl border-2 p-4 ${ESTADO_BG[c.estado] ?? 'bg-white border-gray-200'}`}>
              <div className="flex items-center justify-between mb-3">
                <div>
                  <span className="font-bold text-gray-800">Pedido #{c.pedido_id}</span>
                  <p className="text-xs text-gray-500 mt-0.5">{tiempoTranscurrido(c.created_at)}</p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${
                  c.estado === 'pendiente'      ? 'bg-yellow-200 text-yellow-800' :
                  c.estado === 'en_preparacion' ? 'bg-blue-200 text-blue-800' :
                  'bg-green-200 text-green-800'
                }`}>
                  {c.estado.replace('_', ' ')}
                </span>
              </div>

              {NEXT[c.estado] && (
                <button
                  onClick={() => avanzar(c)}
                  className="w-full mt-2 bg-white hover:bg-gray-50 border border-gray-300 text-gray-700 text-sm py-1.5 rounded-lg transition capitalize"
                >
                  → {NEXT[c.estado].replace('_', ' ')}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
