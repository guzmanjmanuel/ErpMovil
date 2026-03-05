import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

interface Turno {
  id: number; estado: string; fondo_inicial: string
  total_efectivo?: string; total_tarjeta?: string; total_qr?: string
  total_ventas?: string; observaciones?: string
  abierto_en: string; cerrado_en?: string
}

interface Movimiento { id: number; tipo: string; concepto: string; monto: string; created_at: string }

export default function Caja() {
  const { user } = useAuth()
  const tid = user!.tenant_id
  const [turno,    setTurno]    = useState<Turno | null>(null)
  const [movs,     setMovs]     = useState<Movimiento[]>([])
  const [loading,  setLoading]  = useState(true)
  const [fondo,    setFondo]    = useState('0')
  const [tipo,     setTipo]     = useState<'ingreso'|'egreso'>('ingreso')
  const [concepto, setConcepto] = useState('')
  const [monto,    setMonto]    = useState('')
  const [saving,   setSaving]   = useState(false)

  async function cargar() {
    const t = await api.get<Turno | null>(`/tenants/${tid}/caja/turno-actual`)
    setTurno(t)
    if (t) {
      const m = await api.get<Movimiento[]>(`/tenants/${tid}/caja/turnos/${t.id}/movimientos`)
      setMovs(m)
    }
    setLoading(false)
  }

  useEffect(() => { cargar() }, [])

  async function abrirTurno() {
    setSaving(true)
    await api.post(`/tenants/${tid}/caja/abrir-turno`, { fondo_inicial: parseFloat(fondo) })
    await cargar()
    setSaving(false)
  }

  async function cerrarTurno() {
    if (!turno || !confirm('¿Cerrar el turno de caja?')) return
    setSaving(true)
    await api.post(`/tenants/${tid}/caja/cerrar-turno/${turno.id}`, {})
    setTurno(null)
    setMovs([])
    setSaving(false)
  }

  async function registrarMovimiento() {
    if (!turno || !concepto || !monto) return
    setSaving(true)
    await api.post(`/tenants/${tid}/caja/turnos/${turno.id}/movimientos`, {
      tipo, concepto, monto: parseFloat(monto),
    })
    setConcepto('')
    setMonto('')
    await cargar()
    setSaving(false)
  }

  if (loading) return <div className="p-6 text-gray-400 text-sm">Cargando...</div>

  return (
    <div className="p-6">
      <h2 className="text-xl font-bold text-gray-800 mb-6">Caja</h2>

      {!turno ? (
        <div className="bg-white rounded-xl shadow p-8 max-w-sm">
          <h3 className="font-semibold text-gray-700 mb-4">Abrir turno de caja</h3>
          <div className="mb-4">
            <label className="block text-sm text-gray-600 mb-1">Fondo inicial ($)</label>
            <input
              type="number"
              value={fondo}
              onChange={e => setFondo(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <button
            onClick={abrirTurno}
            disabled={saving}
            className="w-full bg-green-600 hover:bg-green-700 text-white py-2 rounded-lg text-sm font-medium"
          >
            Abrir turno
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Info turno */}
          <div className="bg-white rounded-xl shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-700">Turno #{turno.id}</h3>
              <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Abierto</span>
            </div>
            <div className="space-y-2 text-sm">
              <Row label="Fondo inicial" value={`$${parseFloat(turno.fondo_inicial).toFixed(2)}`} />
              <Row label="Abierto en" value={new Date(turno.abierto_en).toLocaleString()} />
              {turno.total_ventas && <Row label="Total ventas" value={`$${parseFloat(turno.total_ventas).toFixed(2)}`} />}
            </div>
            <button
              onClick={cerrarTurno}
              disabled={saving}
              className="mt-6 w-full bg-red-50 hover:bg-red-100 text-red-600 py-2 rounded-lg text-sm font-medium"
            >
              Cerrar turno
            </button>
          </div>

          {/* Movimientos */}
          <div className="bg-white rounded-xl shadow p-6 flex flex-col">
            <h3 className="font-semibold text-gray-700 mb-4">Movimientos</h3>

            {/* Form */}
            <div className="grid grid-cols-2 gap-2 mb-3">
              <select
                value={tipo}
                onChange={e => setTipo(e.target.value as 'ingreso'|'egreso')}
                className="border border-gray-300 rounded-lg px-2 py-1.5 text-sm"
              >
                <option value="ingreso">Ingreso</option>
                <option value="egreso">Egreso</option>
              </select>
              <input
                type="number"
                placeholder="Monto"
                value={monto}
                onChange={e => setMonto(e.target.value)}
                className="border border-gray-300 rounded-lg px-2 py-1.5 text-sm"
              />
            </div>
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                placeholder="Concepto"
                value={concepto}
                onChange={e => setConcepto(e.target.value)}
                className="flex-1 border border-gray-300 rounded-lg px-2 py-1.5 text-sm"
              />
              <button
                onClick={registrarMovimiento}
                disabled={saving}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1.5 rounded-lg text-sm"
              >
                +
              </button>
            </div>

            {/* Lista */}
            <div className="flex-1 overflow-auto space-y-2">
              {movs.length === 0 && <p className="text-xs text-gray-400 text-center py-4">Sin movimientos</p>}
              {movs.map(m => (
                <div key={m.id} className="flex items-center justify-between text-sm">
                  <div>
                    <p className="text-gray-700">{m.concepto}</p>
                    <p className="text-xs text-gray-400">{new Date(m.created_at).toLocaleTimeString()}</p>
                  </div>
                  <span className={`font-medium ${m.tipo === 'ingreso' ? 'text-green-600' : 'text-red-600'}`}>
                    {m.tipo === 'ingreso' ? '+' : '-'}${parseFloat(m.monto).toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-800 font-medium">{value}</span>
    </div>
  )
}
