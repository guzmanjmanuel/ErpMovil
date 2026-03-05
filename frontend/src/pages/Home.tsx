import { useGet } from '../hooks/useApi'

interface HelloResponse {
  message: string
}

export default function Home() {
  const root = useGet<HelloResponse>('/')
  const hello = useGet<HelloResponse>('/hello/mundo')

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
      <div className="max-w-2xl w-full space-y-6">
        <h1 className="text-3xl font-bold text-gray-800">ERP Movil</h1>

        <EndpointCard
          title="GET /"
          loading={root.loading}
          error={root.error}
          data={root.data}
          onRefetch={root.refetch}
        />

        <EndpointCard
          title="GET /hello/mundo"
          loading={hello.loading}
          error={hello.error}
          data={hello.data}
          onRefetch={hello.refetch}
        />
      </div>
    </div>
  )
}

function EndpointCard({
  title,
  loading,
  error,
  data,
  onRefetch,
}: {
  title: string
  loading: boolean
  error: string | null
  data: unknown
  onRefetch: () => void
}) {
  return (
    <div className="bg-white rounded-xl shadow p-6 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-mono font-semibold text-indigo-600">{title}</h2>
        <button
          onClick={onRefetch}
          className="text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-700 px-3 py-1 rounded-full transition"
        >
          Refrescar
        </button>
      </div>

      {loading && <p className="text-sm text-gray-400 animate-pulse">Cargando...</p>}
      {error && <p className="text-sm text-red-500">{error}</p>}
      {!loading && !error && data !== null && (
        <pre className="text-sm bg-gray-50 rounded-lg p-3 text-gray-700 overflow-auto">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  )
}
