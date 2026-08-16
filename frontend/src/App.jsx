import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import StockManagement from './pages/StockManagement'
import ExpiryTracking from './pages/ExpiryTracking'
import Predictions from './pages/Predictions'
import SalesHistory from './pages/SalesHistory'
import Medicines from './pages/Medicines'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="medicines" element={<Medicines />} />
          <Route path="stock" element={<StockManagement />} />
          <Route path="expiry" element={<ExpiryTracking />} />
          <Route path="predictions" element={<Predictions />} />
          <Route path="sales" element={<SalesHistory />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
