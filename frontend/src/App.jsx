import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import ExpiryTracking from './pages/ExpiryTracking'
import SalesHistory from './pages/SalesHistory'
import Medicines from './pages/Medicines'
import WriteOffs from './pages/WriteOffs'
import DataImport from './pages/DataImport'
import Inventory from './pages/Inventory'
import ForecastingReorder from './pages/ForecastingReorder'
import ControlledDrugs from './pages/ControlledDrugs'

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
            <Route path="inventory"       element={<Inventory />} />
            <Route path="sales"           element={<SalesHistory />} />
            <Route path="forecasting"     element={<ForecastingReorder />} />
            <Route path="writeoffs"       element={<WriteOffs />} />
            <Route path="expiry"          element={<ExpiryTracking />} />
            <Route path="controlled-drugs" element={<ControlledDrugs />} />
            <Route path="data-import"     element={<DataImport />} />

            {/* Legacy route redirects (keep old links working) */}
            <Route path="stock"          element={<Navigate to="/inventory" replace />} />
            <Route path="packs"          element={<Navigate to="/inventory" replace />} />
            <Route path="predictions"    element={<Navigate to="/forecasting" replace />} />
            <Route path="reorder"        element={<Navigate to="/forecasting" replace />} />
            <Route path="cd-register"    element={<Navigate to="/controlled-drugs" replace />} />
            <Route path="duty-register"  element={<Navigate to="/controlled-drugs" replace />} />
            <Route path="cd-destruction" element={<Navigate to="/controlled-drugs" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
