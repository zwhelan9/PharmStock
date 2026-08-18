import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ children, requiredRole }) {
  const { user } = useAuth()
  const location = useLocation()

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (requiredRole && user.role !== requiredRole) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-2xl mb-2">🔒</p>
          <p className="text-gray-600 font-medium">Access denied</p>
          <p className="text-sm text-gray-400">You need {requiredRole} access for this page.</p>
        </div>
      </div>
    )
  }

  return children
}
