import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

interface Area  { id: number; nombre: string }
interface Mesa  { id: number; numero: string; capacidad: number; estado: string; area_id: number | null }

const ESTADO_COLOR: Record<string, string> = {
  disponible: 'bg-green-100 border-green-300 text-green-800',
  ocupada:    'bg-red-100   border-red-300   text-red-800',
  reservada:  'bg-yellow-100 border-yellow-300 text-yellow-800',
}

export default function Mesas() {
  const { user } = useAuth()
  const tid = user!.tenant_id
  const [areas,  setAreas]  = useState<Area[]>([])
  const [mesas,  setMesas]  = useState<Mesa[]>([])
  const [filtro, setFiltro] = useState<string>('todas')
  const [loading, setLoading] = useState(true)

  async function cargar() {
    const [a, m] = await Promise.all([
      api.get<Area[]>(`/tenants/${tid}/mesas/areas`),
      api.get<Mesa[]>(`/tenants/${tid}/mesas`),
    ])
    setAreas(a)
    setMesas(m)
    setLoading(false)
  }

  useEffect(() => { cargar() }, [])

  async function cambiarEstado(mesaId: number, estado: string) {
    await api.patch(`/tenants/${tid}/mesas/${mesaId}/estado`, { estado })
    cargar()
  }

  const mesasFiltradas = filtro === 'todas' ? mesas : mesas.filter(m => m.estado === filtro)

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-gray-800">Mesas</h2>
        <div className="flex gap-2">
          {['todas', 'disponible', 'ocupada', 'reservada'].map(f => (
            <button
              key={f}
              onClick={() => setFiltro(f)}
              className={`text-xs px-3 py-1.5 rounded-full border transition capitalize ${
                filtro === f ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-300 hover:border-indigo-400'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="text-gray-400 text-sm">Cargando...</p>
      ) : (
        <>
          {areas.map(area => {
            const mesasArea = mesasFiltradas.filter(m => m.area_id === area.id)
            if (mesasArea.length === 0) return null
            return (
              <div key={area.id} className="mb-6">
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">{area.nombre}</h3>
                <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-3">
                  {mesasArea.map(mesa => (
                    <MesaCard key={mesa.id} mesa={mesa} onCambiar={cambiarEstado} />
                  ))}
                </div>
              </div>
            )
          })}

          {/* Mesas sin área */}
          {(() => {
            const sinArea = mesasFiltradas.filter(m => m.area_id === null)
            if (sinArea.length === 0) return null
            return (
              <div>
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Sin área</h3>
                <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-3">
                  {sinArea.map(mesa => (
                    <MesaCard key={mesa.id} mesa={mesa} onCambiar={cambiarEstado} />
                  ))}
                </div>
              </div>
            )
          })()}

          {mesasFiltradas.length === 0 && (
            <p className="text-gray-400 text-sm text-center py-12">No hay mesas con este filtro.</p>
          )}
        </>
      )}
    </div>
  )
}

function MesaCard({
  mesa,
  onCambiar,
}: {
  mesa: Mesa
  onCambiar: (id: number, estado: string) => void
}) {
  const nextEstado: Record<string, string> = {
    disponible: 'ocupada',
    ocupada:    'disponible',
    reservada:  'disponible',
  }

  return (
    <div
      className={`border-2 rounded-xl p-3 cursor-pointer hover:shadow-md transition select-none ${ESTADO_COLOR[mesa.estado]}`}
      onClick={() => onCambiar(mesa.id, nextEstado[mesa.estado])}
      title={`Cambiar a ${nextEstado[mesa.estado]}`}
    >
      <p className="font-bold text-lg leading-none">{mesa.numero}</p>
      <p className="text-xs mt-1 opacity-70">{mesa.capacidad} pers.</p>
      <p className="text-xs mt-2 font-medium capitalize">{mesa.estado}</p>
    </div>
  )
}
