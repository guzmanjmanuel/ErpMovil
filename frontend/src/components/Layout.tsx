import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const NAV_RESTAURANTE = [
  { to: '/',        label: 'Dashboard',  perm: 'dashboard.ver', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
  { to: '/mesas',   label: 'Mesas',      perm: 'mesas.ver',     icon: 'M4 6h16M4 10h16M4 14h16M4 18h16' },
  { to: '/pedidos', label: 'Pedidos',    perm: 'pedidos.ver',   icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2' },
  { to: '/menu',    label: 'Menú',       perm: 'menu.ver',      icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253' },
  { to: '/kds',     label: 'Cocina',     perm: 'kds.ver',       icon: 'M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z' },
  { to: '/caja',    label: 'Caja',       perm: 'caja.ver',      icon: 'M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z' },
  { to: '/facturacion', label: 'Facturación', perm: 'facturacion.ver', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
  { to: '/clientes', label: 'Clientes',  perm: 'clientes.ver',  icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z' },
  { to: '/usuarios', label: 'Usuarios',  perm: 'usuarios.ver',  icon: 'M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0z' },
  { to: '/establecimientos', label: 'Sucursales', perm: 'usuarios.ver', icon: 'M8 14v3m4-3v3m4-3v3M3 21h18M3 10h18M3 7l9-4 9 4M4 10h16v11H4V10z' },
  { to: '/negocios', label: 'Negocios',  perm: 'usuarios.ver',  icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-2 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4' },
  { to: '/productos', label: 'Productos', perm: 'usuarios.ver', icon: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10' },
]

const NAV_POS = [
  { to: '/',        label: 'Dashboard',  perm: 'dashboard.ver', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
  { to: '/pedidos', label: 'Ventas',     perm: 'pedidos.ver',   icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2' },
  { to: '/menu',    label: 'Productos',  perm: 'menu.ver',      icon: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10' },
  { to: '/caja',    label: 'Caja',       perm: 'caja.ver',      icon: 'M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z' },
  { to: '/facturacion', label: 'Facturación', perm: 'facturacion.ver', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
  { to: '/clientes', label: 'Clientes',  perm: 'clientes.ver',  icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z' },
  { to: '/usuarios', label: 'Usuarios',  perm: 'usuarios.ver',  icon: 'M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0z' },
  { to: '/establecimientos', label: 'Sucursales', perm: 'usuarios.ver', icon: 'M8 14v3m4-3v3m4-3v3M3 21h18M3 10h18M3 7l9-4 9 4M4 10h16v11H4V10z' },
  { to: '/negocios', label: 'Negocios',  perm: 'usuarios.ver',  icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-2 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4' },
  { to: '/productos', label: 'Productos', perm: 'usuarios.ver', icon: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10' },
]

const TIPO_LABEL: Record<string, string> = { restaurante: '🍽 Restaurante', pos: '🏪 Punto de Venta' }
const TIPO_COLOR: Record<string, string> = { restaurante: 'bg-orange-600', pos: 'bg-indigo-600' }
const ROL_COLOR: Record<string, string> = {
  admin: 'bg-red-500', supervisor: 'bg-purple-500', cajero: 'bg-blue-500',
  mesero: 'bg-green-500', cocinero: 'bg-orange-500', vendedor: 'bg-teal-500', consulta: 'bg-gray-500',
}

export default function Layout() {
  const { user, logout, can } = useAuth()
  const navigate = useNavigate()
  const nav = user?.tipo_negocio === 'pos' ? NAV_POS : NAV_RESTAURANTE
  const sidebarColor = TIPO_COLOR[user?.tipo_negocio ?? 'restaurante']

  function handleLogout() { logout(); navigate('/login') }

  return (
    <div className="flex h-screen bg-gray-100">
      <aside className={`w-56 ${sidebarColor} flex flex-col`}>
        {/* Header */}
        <div className="px-4 py-4 border-b border-white/20">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-white font-bold text-base">ErpMovil</span>
            <span className="text-xs bg-white/20 text-white px-1.5 py-0.5 rounded-full">
              {user?.tipo_negocio === 'pos' ? 'POS' : 'REST'}
            </span>
          </div>
          <p className="text-white/70 text-xs truncate">{user?.nombre}</p>
          <span className={`inline-block mt-1 text-xs px-2 py-0.5 rounded-full text-white font-medium ${user?.is_superadmin ? 'bg-purple-500' : (ROL_COLOR[user?.rol ?? ''] ?? 'bg-white/20')}`}>
            {user?.is_superadmin ? 'Superadmin' : user?.rol}
          </span>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
          {nav.filter(item => can(item.perm)).map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${
                  isActive ? 'bg-white/20 text-white font-medium' : 'text-white/70 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={item.icon} />
              </svg>
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-2 py-3 border-t border-white/20">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-white/70 hover:bg-white/10 hover:text-white transition"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Cerrar sesión
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
