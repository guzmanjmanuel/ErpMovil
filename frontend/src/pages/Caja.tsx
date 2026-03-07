import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'
import { api } from '../api/client'

// ── Tipos ──────────────────────────────────────────────────────────────────────

interface TurnoOut {
  id: number; usuario_id: number; estado: string; fondo_inicial: string
  total_efectivo?: string; total_ventas?: string; total_descuentos?: string
  diferencia_caja?: string; observaciones?: string
  abierto_en: string; cerrado_en?: string
}

interface DesglosePago {
  forma_pago_codigo: string; forma_pago_descripcion: string
  cantidad_transacciones: number; total: string
}

interface TurnoResumen {
  turno_id: number; estado: string; fondo_inicial: string
  abierto_en: string; cerrado_en?: string
  desglose_pagos: DesglosePago[]
  total_ventas_sistema: string; total_descuentos: string
  total_ingresos_manuales: string; total_egresos_manuales: string
  efectivo_esperado_caja: string
  efectivo_contado?: string; diferencia_caja?: string
  cantidad_pedidos: number
}

interface ResumenDia {
  fecha: string; cantidad_turnos: number
  desglose_pagos: DesglosePago[]
  ventas_total: string; descuentos_total: string; cantidad_pedidos: number
}

interface Movimiento {
  id: number; turno_id: number; tipo: string
  motivo: string; monto: string; created_at: string
}

type Tab = 'resumen' | 'movimientos' | 'historial' | 'corte'

// ── Helpers ────────────────────────────────────────────────────────────────────

const fmt = (v?: string | number) => `$${parseFloat(String(v ?? 0)).toFixed(2)}`
const fmtDate = (s: string) => new Date(s).toLocaleString('es-SV', { dateStyle: 'short', timeStyle: 'short' })
const fmtTime = (s: string) => new Date(s).toLocaleTimeString('es-SV', { hour: '2-digit', minute: '2-digit' })

const PAGO_ICON: Record<string, string> = {
  '01': '💵', '02': '💳', '03': '💳', '04': '🏦',
  '05': '🔄', '08': '📱', '09': '📱', '11': '₿',
  '12': '🪙', '13': '📋', '14': '🏧', '99': '🔖',
}

// ── Skeleton ───────────────────────────────────────────────────────────────────

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`bg-gray-200 animate-pulse rounded-lg ${className}`} />
}

function ResumenSkeleton() {
  return (
    <div className="space-y-6 max-w-4xl">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[1,2,3,4].map(i => <Skeleton key={i} className="h-24" />)}
      </div>
      <Skeleton className="h-48" />
      <Skeleton className="h-36" />
    </div>
  )
}

// ── Sub-componentes ────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, color = 'gray', loading }: {
  label: string; value: string; sub?: string
  color?: 'green'|'red'|'blue'|'gray'|'yellow'; loading?: boolean
}) {
  const colors = {
    green:  'bg-green-50 border-green-200 text-green-700',
    red:    'bg-red-50 border-red-200 text-red-700',
    blue:   'bg-blue-50 border-blue-200 text-blue-700',
    yellow: 'bg-yellow-50 border-yellow-200 text-yellow-700',
    gray:   'bg-gray-50 border-gray-200 text-gray-700',
  }
  return (
    <div className={`rounded-xl border p-4 ${colors[color]}`}>
      <p className="text-xs font-medium opacity-70 mb-1">{label}</p>
      {loading
        ? <div className="h-8 bg-current opacity-10 rounded animate-pulse" />
        : <p className="text-2xl font-bold">{value}</p>
      }
      {sub && !loading && <p className="text-xs opacity-60 mt-0.5">{sub}</p>}
    </div>
  )
}

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-gray-100 last:border-0">
      <span className="text-sm text-gray-500">{label}</span>
      <span className={`text-sm ${bold ? 'font-bold text-gray-900' : 'text-gray-700'}`}>{value}</span>
    </div>
  )
}

// ── Modal Cierre ───────────────────────────────────────────────────────────────

function ModalCierre({ resumen, onClose, onConfirm, saving }: {
  resumen: TurnoResumen; onClose: () => void
  onConfirm: (efectivo: string, obs: string) => void; saving: boolean
}) {
  const [efectivo, setEfectivo] = useState('')
  const [obs, setObs] = useState('')
  const esperado = parseFloat(resumen.efectivo_esperado_caja)
  const contado  = parseFloat(efectivo || '0')
  const diferencia = contado - esperado

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="p-6 border-b border-gray-100">
          <h3 className="text-lg font-bold text-gray-800">Cerrar turno #{resumen.turno_id}</h3>
          <p className="text-sm text-gray-500 mt-1">Ingresa el efectivo contado en caja</p>
        </div>
        <div className="p-6 space-y-4">
          <div className="bg-gray-50 rounded-xl p-4 space-y-2">
            <Row label="Fondo inicial"     value={fmt(resumen.fondo_inicial)} />
            <Row label="Ventas (sistema)"  value={fmt(resumen.total_ventas_sistema)} />
            <Row label="Ingresos manuales" value={fmt(resumen.total_ingresos_manuales)} />
            <Row label="Egresos manuales"  value={`-${fmt(resumen.total_egresos_manuales)}`} />
            <Row label="Efectivo esperado" value={fmt(resumen.efectivo_esperado_caja)} bold />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Efectivo contado ($)</label>
            <input
              type="number" min="0" step="0.01" value={efectivo}
              onChange={e => setEfectivo(e.target.value)} placeholder="0.00" autoFocus
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-lg font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          {efectivo !== '' && (
            <div className={`rounded-xl p-4 flex justify-between items-center ${
              diferencia >= 0 ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
            }`}>
              <span className="text-sm font-medium">{diferencia >= 0 ? '✓ Sobrante' : '⚠ Faltante'}</span>
              <span className={`text-xl font-bold ${diferencia >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                {diferencia >= 0 ? '+' : ''}{fmt(diferencia)}
              </span>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Observaciones (opcional)</label>
            <textarea value={obs} onChange={e => setObs(e.target.value)} rows={2} placeholder="Notas del cierre..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none" />
          </div>
        </div>
        <div className="p-6 pt-0 flex gap-3">
          <button onClick={onClose} className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg text-sm font-medium hover:bg-gray-50">Cancelar</button>
          <button onClick={() => onConfirm(efectivo || '0', obs)} disabled={saving}
            className="flex-1 bg-red-600 hover:bg-red-700 text-white py-2 rounded-lg text-sm font-medium disabled:opacity-50">
            {saving ? 'Cerrando...' : 'Confirmar cierre'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Página principal ───────────────────────────────────────────────────────────

export default function Caja() {
  const { user } = useAuth()
  const tid = user!.tenant_id!

  // Turno carga primero — desbloquea el render inmediatamente
  const [turno,          setTurno]          = useState<TurnoOut | null | undefined>(undefined)
  const [resumen,        setResumen]        = useState<TurnoResumen | null>(null)
  const [resumenLoading, setResumenLoading] = useState(false)
  const [resumenError,   setResumenError]   = useState<string | null>(null)
  const [movs,           setMovs]           = useState<Movimiento[]>([])
  const [movsLoading,    setMovsLoading]    = useState(false)
  const [historial,      setHistorial]      = useState<TurnoOut[]>([])
  const [corteZ,         setCorteZ]         = useState<ResumenDia | null>(null)
  const [tab,            setTab]            = useState<Tab>('resumen')
  const [saving,         setSaving]         = useState(false)
  const [showCierre,     setShowCierre]     = useState(false)
  const [fondo,          setFondo]          = useState('0')
  const [movTipo,        setMovTipo]        = useState<'ingreso'|'egreso'>('ingreso')
  const [movConcepto,    setMovConcepto]    = useState('')
  const [movMonto,       setMovMonto]       = useState('')
  const [movError,       setMovError]       = useState<string | null>(null)

  // 1. Carga el turno primero (una sola query rápida)
  const cargarTurno = useCallback(async () => {
    const t = await api.get<TurnoOut | null>(`/tenants/${tid}/caja/turno-actual`)
    setTurno(t)
    return t
  }, [tid])

  // 2. Carga resumen y movimientos en paralelo (después de tener el turno)
  const cargarDetalle = useCallback(async (t: TurnoOut) => {
    setResumenLoading(true)
    setMovsLoading(true)
    setResumenError(null)
    try {
      const [r, m] = await Promise.all([
        api.get<TurnoResumen>(`/tenants/${tid}/caja/turno-actual/resumen`),
        api.get<Movimiento[]>(`/tenants/${tid}/caja/turnos/${t.id}/movimientos`),
      ])
      setResumen(r)
      setMovs(m)
    } catch (e: unknown) {
      setResumenError(e instanceof Error ? e.message : 'Error al cargar resumen')
    } finally {
      setResumenLoading(false)
      setMovsLoading(false)
    }
  }, [tid])

  const cargar = useCallback(async () => {
    const t = await cargarTurno()
    if (t) cargarDetalle(t)   // no await — se carga en background
  }, [cargarTurno, cargarDetalle])

  const cargarHistorial = useCallback(async () => {
    const [h, c] = await Promise.all([
      api.get<TurnoOut[]>(`/tenants/${tid}/caja/turnos?limit=20`),
      api.get<ResumenDia>(`/tenants/${tid}/caja/resumen-dia`),
    ])
    setHistorial(h)
    setCorteZ(c)
  }, [tid])

  useEffect(() => { cargar() }, [cargar])

  useEffect(() => {
    if (tab === 'historial' || tab === 'corte') cargarHistorial()
  }, [tab, cargarHistorial])

  // Refresco automático del resumen cada 30s
  useEffect(() => {
    if (!turno || tab !== 'resumen') return
    const id = setInterval(async () => {
      const r = await api.get<TurnoResumen>(`/tenants/${tid}/caja/turno-actual/resumen`)
      setResumen(r)
    }, 30_000)
    return () => clearInterval(id)
  }, [turno, tab, tid])

  async function abrirTurno() {
    setSaving(true)
    try {
      await api.post(`/tenants/${tid}/caja/abrir-turno`, { fondo_inicial: parseFloat(fondo || '0') })
      await cargar()
    } finally { setSaving(false) }
  }

  async function cerrarTurno(efectivo: string, obs: string) {
    if (!turno) return
    setSaving(true)
    try {
      await api.post(`/tenants/${tid}/caja/cerrar-turno/${turno.id}`, {
        efectivo_contado: parseFloat(efectivo),
        observaciones: obs || undefined,
      })
      setShowCierre(false)
      setTurno(null)
      setResumen(null)
      setMovs([])
      setTab('historial')
      cargarHistorial()
    } finally { setSaving(false) }
  }

  async function registrarMovimiento() {
    if (!turno || !movConcepto.trim() || !movMonto) return
    setSaving(true)
    setMovError(null)
    try {
      await api.post(`/tenants/${tid}/caja/turnos/${turno.id}/movimientos`, {
        tipo: movTipo, motivo: movConcepto, monto: parseFloat(movMonto),
      })
      setMovConcepto('')
      setMovMonto('')
      cargar()   // recarga en background sin bloquear
    } catch (e: unknown) {
      setMovError(e instanceof Error ? e.message : 'Error al registrar movimiento')
    } finally { setSaving(false) }
  }

  // ── turno === undefined → carga inicial (solo spinner pequeño en header) ──
  if (turno === undefined) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          <p className="text-xs text-gray-400">Verificando caja...</p>
        </div>
      </div>
    )
  }

  // ── Sin turno: pantalla de apertura ──────────────────────────────────────────
  if (turno === null) {
    return (
      <div className="min-h-full flex items-center justify-center bg-gray-50 p-6">
        <div className="w-full max-w-sm">
          <div className="bg-white rounded-2xl shadow-lg p-8 mb-4">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-indigo-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
                <svg className="w-8 h-8 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </div>
              <h2 className="text-xl font-bold text-gray-800">Caja cerrada</h2>
              <p className="text-sm text-gray-500 mt-1">Ingresa el fondo inicial para comenzar</p>
            </div>
            <div className="mb-5">
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Fondo inicial ($)</label>
              <input type="number" min="0" step="0.01" value={fondo}
                onChange={e => setFondo(e.target.value)} placeholder="0.00"
                className="w-full border border-gray-300 rounded-xl px-4 py-3 text-xl font-mono text-center focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
            <button onClick={abrirTurno} disabled={saving}
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-xl text-sm font-semibold disabled:opacity-50 transition">
              {saving ? 'Abriendo...' : 'Abrir turno de caja'}
            </button>
          </div>
          <button onClick={() => { cargarHistorial(); setTab('historial') }}
            className="w-full text-center text-sm text-indigo-600 hover:text-indigo-800 font-medium">
            Ver historial de turnos →
          </button>
        </div>
      </div>
    )
  }

  // ── Con turno: render inmediato, resumen en background ────────────────────────
  const TABS: { key: Tab; label: string }[] = [
    { key: 'resumen', label: 'Resumen' },
    { key: 'movimientos', label: 'Movimientos' },
    { key: 'historial', label: 'Historial' },
    { key: 'corte', label: 'Corte Z' },
  ]

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header — visible de inmediato con datos del turno */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-gray-800">Turno #{turno.id}</h2>
            <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">● Abierto</span>
          </div>
          <p className="text-xs text-gray-400">
            Fondo: {fmt(turno.fondo_inicial)} · Desde {fmtTime(turno.abierto_en)}
          </p>
        </div>
        <button onClick={() => setShowCierre(true)}
          className="flex items-center gap-2 bg-red-50 hover:bg-red-100 text-red-600 px-4 py-2 rounded-lg text-sm font-medium transition">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5.636 5.636a9 9 0 1012.728 0M12 3v9" />
          </svg>
          Cerrar turno
        </button>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200 px-6">
        <div className="flex">
          {TABS.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition ${
                tab === t.key ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6">

        {/* ── Resumen ── */}
        {tab === 'resumen' && (
          resumenError
            ? (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 max-w-lg">
                <p className="text-sm font-semibold text-red-700 mb-1">Error al cargar resumen</p>
                <p className="text-sm text-red-600">{resumenError}</p>
                <button onClick={() => turno && cargarDetalle(turno)}
                  className="mt-3 text-xs text-red-700 underline">Reintentar</button>
              </div>
            )
          : resumenLoading || !resumen
            ? <ResumenSkeleton />
            : (
              <div className="space-y-6 max-w-4xl">
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <StatCard label="Ventas del turno" value={fmt(resumen.total_ventas_sistema)}
                    sub={`${resumen.cantidad_pedidos} pedido(s)`} color="blue" />
                  <StatCard label="Efectivo en caja" value={fmt(resumen.efectivo_esperado_caja)}
                    sub={`Fondo ${fmt(resumen.fondo_inicial)}`} color="green" />
                  <StatCard label="Descuentos" value={fmt(resumen.total_descuentos)} color="yellow" />
                  <StatCard label="Balance movimientos"
                    value={fmt(parseFloat(resumen.total_ingresos_manuales) - parseFloat(resumen.total_egresos_manuales))}
                    sub={`+${fmt(resumen.total_ingresos_manuales)} / -${fmt(resumen.total_egresos_manuales)}`} color="gray" />
                </div>

                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                  <h3 className="font-semibold text-gray-700 mb-4">Ventas por forma de pago</h3>
                  {resumen.desglose_pagos.length === 0
                    ? <p className="text-sm text-gray-400 text-center py-4">Sin ventas en este turno</p>
                    : (
                      <div className="space-y-3">
                        {resumen.desglose_pagos.map(d => {
                          const pct = parseFloat(resumen.total_ventas_sistema) > 0
                            ? (parseFloat(d.total) / parseFloat(resumen.total_ventas_sistema)) * 100 : 0
                          return (
                            <div key={d.forma_pago_codigo}>
                              <div className="flex items-center justify-between mb-1">
                                <div className="flex items-center gap-2">
                                  <span className="text-lg">{PAGO_ICON[d.forma_pago_codigo] ?? '💰'}</span>
                                  <div>
                                    <p className="text-sm font-medium text-gray-800">{d.forma_pago_descripcion}</p>
                                    <p className="text-xs text-gray-400">Cód. {d.forma_pago_codigo} · {d.cantidad_transacciones} transacción(es)</p>
                                  </div>
                                </div>
                                <span className="text-sm font-bold text-gray-800">{fmt(d.total)}</span>
                              </div>
                              <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                <div className="h-full bg-indigo-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
                              </div>
                            </div>
                          )
                        })}
                        <div className="pt-3 border-t border-gray-100 flex justify-between">
                          <span className="text-sm font-semibold text-gray-700">Total</span>
                          <span className="text-base font-bold text-indigo-600">{fmt(resumen.total_ventas_sistema)}</span>
                        </div>
                      </div>
                    )
                  }
                </div>

                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                  <h3 className="font-semibold text-gray-700 mb-4">Composición del efectivo</h3>
                  <div className="space-y-1">
                    <Row label="Fondo inicial"       value={fmt(resumen.fondo_inicial)} />
                    <Row label="+ Ventas en efectivo"
                      value={fmt(resumen.desglose_pagos.find(d => d.forma_pago_codigo === '01')?.total ?? '0')} />
                    <Row label="+ Ingresos manuales" value={fmt(resumen.total_ingresos_manuales)} />
                    <Row label="− Egresos manuales"  value={`-${fmt(resumen.total_egresos_manuales)}`} />
                    <div className="pt-2 mt-2 border-t-2 border-gray-200">
                      <Row label="Efectivo esperado en caja" value={fmt(resumen.efectivo_esperado_caja)} bold />
                    </div>
                  </div>
                </div>
              </div>
            )
        )}

        {/* ── Movimientos ── */}
        {tab === 'movimientos' && (
          <div className="max-w-2xl space-y-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h3 className="font-semibold text-gray-700 mb-4">Registrar movimiento</h3>
              <div className="grid grid-cols-2 gap-3 mb-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Tipo</label>
                  <select value={movTipo} onChange={e => setMovTipo(e.target.value as 'ingreso'|'egreso')}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                    <option value="ingreso">↑ Ingreso</option>
                    <option value="egreso">↓ Egreso</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Monto ($)</label>
                  <input type="number" min="0" step="0.01" value={movMonto}
                    onChange={e => setMovMonto(e.target.value)} placeholder="0.00"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                </div>
              </div>
              <div className="flex gap-3">
                <input type="text" value={movConcepto} onChange={e => setMovConcepto(e.target.value)}
                  placeholder="Motivo del movimiento..." onKeyDown={e => e.key === 'Enter' && registrarMovimiento()}
                  className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                <button onClick={registrarMovimiento} disabled={saving || !movConcepto.trim() || !movMonto}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2 rounded-lg text-sm font-medium disabled:opacity-40">
                  {saving ? 'Guardando...' : 'Registrar'}
                </button>
              </div>
              {movError && (
                <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2 mt-1">
                  {movError}
                </p>
              )}
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100">
              <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center">
                <h3 className="font-semibold text-gray-700">Movimientos del turno</h3>
                <span className="text-xs text-gray-400">{movs.length} registros</span>
              </div>
              {movsLoading
                ? <div className="p-6 space-y-3">{[1,2,3].map(i => <Skeleton key={i} className="h-10" />)}</div>
                : movs.length === 0
                  ? <p className="text-sm text-gray-400 text-center py-8">Sin movimientos en este turno</p>
                  : (
                    <>
                      <div className="divide-y divide-gray-50">
                        {movs.map(m => (
                          <div key={m.id} className="px-6 py-3 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                                m.tipo === 'ingreso' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                              }`}>
                                {m.tipo === 'ingreso' ? '↑' : '↓'}
                              </div>
                              <div>
                                <p className="text-sm text-gray-800">{m.motivo}</p>
                                <p className="text-xs text-gray-400">{fmtTime(m.created_at)}</p>
                              </div>
                            </div>
                            <span className={`text-sm font-bold ${m.tipo === 'ingreso' ? 'text-green-600' : 'text-red-600'}`}>
                              {m.tipo === 'ingreso' ? '+' : '-'}{fmt(m.monto)}
                            </span>
                          </div>
                        ))}
                      </div>
                      <div className="px-6 py-4 border-t border-gray-100 bg-gray-50 rounded-b-xl grid grid-cols-2 gap-4">
                        <div className="text-center">
                          <p className="text-xs text-gray-500">Total ingresos</p>
                          <p className="text-base font-bold text-green-600">
                            +{fmt(movs.filter(m => m.tipo === 'ingreso').reduce((s, m) => s + parseFloat(m.monto), 0))}
                          </p>
                        </div>
                        <div className="text-center">
                          <p className="text-xs text-gray-500">Total egresos</p>
                          <p className="text-base font-bold text-red-600">
                            -{fmt(movs.filter(m => m.tipo === 'egreso').reduce((s, m) => s + parseFloat(m.monto), 0))}
                          </p>
                        </div>
                      </div>
                    </>
                  )
              }
            </div>
          </div>
        )}

        {/* ── Historial ── */}
        {tab === 'historial' && (
          <div className="max-w-3xl">
            <div className="bg-white rounded-xl shadow-sm border border-gray-100">
              <div className="px-6 py-4 border-b border-gray-100">
                <h3 className="font-semibold text-gray-700">Historial de turnos</h3>
                <p className="text-xs text-gray-400 mt-0.5">Últimos 20 turnos</p>
              </div>
              {historial.length === 0
                ? <div className="p-6 space-y-3">{[1,2,3].map(i => <Skeleton key={i} className="h-14" />)}</div>
                : (
                  <div className="divide-y divide-gray-50">
                    {historial.map(t => (
                      <div key={t.id} className="px-6 py-4 flex items-center justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-semibold text-gray-800">Turno #{t.id}</p>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              t.estado === 'abierto' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                            }`}>{t.estado}</span>
                          </div>
                          <p className="text-xs text-gray-400 mt-0.5">
                            {fmtDate(t.abierto_en)}{t.cerrado_en ? ` → ${fmtDate(t.cerrado_en)}` : ' · en curso'}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-bold text-gray-800">{t.total_ventas ? fmt(t.total_ventas) : '—'}</p>
                          {t.diferencia_caja != null && (
                            <p className={`text-xs font-medium ${parseFloat(t.diferencia_caja) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                              {parseFloat(t.diferencia_caja) >= 0 ? '+' : ''}{fmt(t.diferencia_caja)} dif.
                            </p>
                          )}
                          <p className="text-xs text-gray-400">Fondo: {fmt(t.fondo_inicial)}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )
              }
            </div>
          </div>
        )}

        {/* ── Corte Z ── */}
        {tab === 'corte' && (
          <div className="max-w-2xl">
            {!corteZ
              ? <div className="space-y-4"><Skeleton className="h-40" /><Skeleton className="h-56" /></div>
              : (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h3 className="font-bold text-gray-800 text-lg">Corte Z del día</h3>
                      <p className="text-sm text-gray-400">{new Date(corteZ.fecha + 'T12:00:00').toLocaleDateString('es-SV', { dateStyle: 'full' })}</p>
                    </div>
                    <button onClick={cargarHistorial} className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">Actualizar</button>
                  </div>
                  <div className="grid grid-cols-2 gap-4 mb-6">
                    <StatCard label="Ventas del día"    value={fmt(corteZ.ventas_total)}          color="blue" />
                    <StatCard label="Pedidos"           value={String(corteZ.cantidad_pedidos)}   color="green" />
                    <StatCard label="Descuentos"        value={fmt(corteZ.descuentos_total)}      color="yellow" />
                    <StatCard label="Turnos"            value={String(corteZ.cantidad_turnos)}    color="gray" />
                  </div>
                  <h4 className="text-sm font-semibold text-gray-600 mb-3">Desglose por forma de pago</h4>
                  {corteZ.desglose_pagos.length === 0
                    ? <p className="text-sm text-gray-400 text-center py-4">Sin ventas hoy</p>
                    : (
                      <div className="space-y-2">
                        {corteZ.desglose_pagos.map(d => (
                          <div key={d.forma_pago_codigo}
                            className="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-3">
                            <div className="flex items-center gap-2">
                              <span>{PAGO_ICON[d.forma_pago_codigo] ?? '💰'}</span>
                              <div>
                                <p className="text-sm font-medium text-gray-800">{d.forma_pago_descripcion}</p>
                                <p className="text-xs text-gray-400">{d.cantidad_transacciones} transacción(es)</p>
                              </div>
                            </div>
                            <span className="text-sm font-bold text-gray-800">{fmt(d.total)}</span>
                          </div>
                        ))}
                        <div className="flex justify-between items-center pt-3 border-t border-gray-200">
                          <span className="text-sm font-bold text-gray-700">TOTAL</span>
                          <span className="text-lg font-bold text-indigo-600">{fmt(corteZ.ventas_total)}</span>
                        </div>
                      </div>
                    )
                  }
                </div>
              )
            }
          </div>
        )}
      </div>

      {showCierre && resumen && (
        <ModalCierre resumen={resumen} saving={saving} onClose={() => setShowCierre(false)} onConfirm={cerrarTurno} />
      )}
    </div>
  )
}
