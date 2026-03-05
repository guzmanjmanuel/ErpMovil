import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

interface Categoria { id: number; nombre: string; orden: number }
interface Item       { id: number; nombre: string; descripcion?: string; precio_override?: string; disponible: boolean; categoria_id?: number; imagen_url?: string }

export default function Menu() {
  const { user } = useAuth()
  const tid = user!.tenant_id
  const [categorias, setCategorias] = useState<Categoria[]>([])
  const [items,      setItems]      = useState<Item[]>([])
  const [catActiva,  setCatActiva]  = useState<number | null>(null)
  const [loading, setLoading]       = useState(true)

  async function cargar() {
    const [cats, its] = await Promise.all([
      api.get<Categoria[]>(`/tenants/${tid}/menu/categorias`),
      api.get<Item[]>(`/tenants/${tid}/menu/items`),
    ])
    setCategorias(cats)
    setItems(its)
    if (cats.length > 0 && !catActiva) setCatActiva(cats[0].id)
    setLoading(false)
  }

  useEffect(() => { cargar() }, [])

  async function toggleDisponible(item: Item) {
    await api.patch(`/tenants/${tid}/menu/items/${item.id}`, { disponible: !item.disponible })
    cargar()
  }

  const itemsFiltrados = catActiva ? items.filter(i => i.categoria_id === catActiva) : items

  return (
    <div className="p-6">
      <h2 className="text-xl font-bold text-gray-800 mb-6">Menú</h2>

      {loading ? (
        <p className="text-gray-400 text-sm">Cargando...</p>
      ) : (
        <div className="flex gap-6">
          {/* Categorías */}
          <aside className="w-44 flex-shrink-0">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Categorías</p>
            <div className="space-y-1">
              <button
                onClick={() => setCatActiva(null)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                  catActiva === null ? 'bg-indigo-600 text-white' : 'hover:bg-gray-100 text-gray-700'
                }`}
              >
                Todas
              </button>
              {categorias.map(c => (
                <button
                  key={c.id}
                  onClick={() => setCatActiva(c.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                    catActiva === c.id ? 'bg-indigo-600 text-white' : 'hover:bg-gray-100 text-gray-700'
                  }`}
                >
                  {c.nombre}
                </button>
              ))}
            </div>
          </aside>

          {/* Items */}
          <div className="flex-1">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {itemsFiltrados.map(item => (
                <div
                  key={item.id}
                  className={`bg-white rounded-xl shadow-sm border transition ${
                    item.disponible ? 'border-gray-100' : 'border-gray-200 opacity-60'
                  }`}
                >
                  {item.imagen_url && (
                    <img src={item.imagen_url} alt={item.nombre} className="w-full h-32 object-cover rounded-t-xl" />
                  )}
                  <div className="p-4">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-semibold text-gray-800 text-sm">{item.nombre}</p>
                        {item.descripcion && (
                          <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">{item.descripcion}</p>
                        )}
                        {item.precio_override && (
                          <p className="text-sm font-bold text-indigo-600 mt-2">${parseFloat(item.precio_override).toFixed(2)}</p>
                        )}
                      </div>
                      <button
                        onClick={() => toggleDisponible(item)}
                        className={`flex-shrink-0 w-10 h-6 rounded-full transition-colors relative ${
                          item.disponible ? 'bg-green-500' : 'bg-gray-300'
                        }`}
                        title={item.disponible ? 'Marcar no disponible' : 'Marcar disponible'}
                      >
                        <span className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform shadow-sm ${
                          item.disponible ? 'translate-x-5' : 'translate-x-1'
                        }`} />
                      </button>
                    </div>
                    <div className="mt-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        item.disponible ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'
                      }`}>
                        {item.disponible ? 'Disponible' : 'No disponible'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
              {itemsFiltrados.length === 0 && (
                <p className="col-span-3 text-center text-gray-400 text-sm py-12">Sin items en esta categoría.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
