import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import type { ReactNode } from 'react'

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { token, isLoading } = useAuth()
  if (isLoading) return <div className="min-h-screen flex items-center justify-center text-slate-500">Loading…</div>
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}
