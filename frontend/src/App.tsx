import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Layout    from './components/Layout'
import Login     from './pages/Login'
import Dashboard from './pages/Dashboard'
import Mesas     from './pages/Mesas'
import Pedidos   from './pages/Pedidos'
import Menu      from './pages/Menu'
import Caja      from './pages/Caja'
import KDS       from './pages/KDS'
import Usuarios  from './pages/Usuarios'
import Clientes         from './pages/Clientes'
import Negocios         from './pages/Negocios'
import Establecimientos from './pages/Establecimientos'
import Productos        from './pages/Productos'
import Inventario       from './pages/Inventario'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  return user ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            element={
              <RequireAuth>
                <Layout />
              </RequireAuth>
            }
          >
            <Route index         element={<Dashboard />} />
            <Route path="mesas"   element={<Mesas />}     />
            <Route path="pedidos" element={<Pedidos />}   />
            <Route path="menu"    element={<Menu />}      />
            <Route path="caja"    element={<Caja />}      />
            <Route path="kds"      element={<KDS />}      />
            <Route path="usuarios"  element={<Usuarios />}  />
            <Route path="clientes"          element={<Clientes />}          />
            <Route path="negocios"          element={<Negocios />}          />
            <Route path="establecimientos"  element={<Establecimientos />}  />
            <Route path="productos"         element={<Productos />}         />
            <Route path="inventario"        element={<Inventario />}        />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
