import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import StockManagement from './pages/StockManagement'
import ExpiryTracking from './pages/ExpiryTracking'
import Predictions from './pages/Predictions'
import SalesHistory from './pages/SalesHistory'
import Medicines from './pages/Medicines'
import PackInventory from './pages/PackInventory'
import WriteOffs from './pages/WriteOffs'
import ReorderRecommendations from './pages/ReorderRecommendations'
import CDRegister from './pages/CDRegister'
import DutyRegister from './pages/DutyRegister'
import CDDestruction from './pages/CDDestruction'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard"       element={<Dashboard />} />
            <Route path="medicines"       element={<Medicines />} />
            <Route path="stock"           element={<StockManagement />} />
            <Route path="packs"           element={<PackInventory />} />
            <Route path="reorder"         element={<ReorderRecommendations />} />
            <Route path="writeoffs"       element={<WriteOffs />} />
            <Route path="expiry"          element={<ExpiryTracking />} />
            <Route path="predictions"     element={<Predictions />} />
            <Route path="sales"           element={<SalesHistory />} />
            <Route path="cd-register"     element={<CDRegister />} />
            <Route path="duty-register"   element={<DutyRegister />} />
            <Route path="cd-destruction"  element={<CDDestruction />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
