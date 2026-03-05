import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'

export function useGet<T>(path: string) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.get<T>(path)
      setData(result)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [path])

  useEffect(() => { fetch() }, [fetch])

  return { data, loading, error, refetch: fetch }
}
