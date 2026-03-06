import { createContext, useContext, useState, type ReactNode } from 'react'
import { api } from '../api/client'

export interface AuthUser {
  usuario_id: number
  nombre: string
  email: string
  rol: string
  tenant_id: number | null
  tipo_negocio: 'restaurante' | 'pos'
  establecimiento_id: number | null
  is_superadmin: boolean
  permisos: string[]
  access_token: string
}

interface AuthContextType {
  user: AuthUser | null
  login: (email: string, password: string, tenant_id?: number) => Promise<AuthUser>
  logout: () => void
  can: (permiso: string) => boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    const stored = localStorage.getItem('auth')
    return stored ? JSON.parse(stored) : null
  })

  async function login(email: string, password: string, tenant_id?: number): Promise<AuthUser> {
    const body: Record<string, unknown> = { email, password }
    if (tenant_id) body.tenant_id = tenant_id
    const data = await api.post<AuthUser>('/auth/login', body)
    // Solo persiste la sesión cuando ya tiene un tenant asignado
    if (data.tenant_id) {
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('auth', JSON.stringify(data))
      setUser(data)
    }
    return data
  }

  function logout() {
    localStorage.removeItem('token')
    localStorage.removeItem('auth')
    setUser(null)
  }

  function can(permiso: string): boolean {
    if (!user) return false
    if (user.is_superadmin || user.rol === 'admin' || user.rol === 'superadmin') return true
    return user.permisos.includes(permiso)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, can }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return ctx
}
