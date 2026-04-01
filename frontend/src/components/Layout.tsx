import { NavLink, useNavigate } from 'react-router-dom'
import { ScanLine, History, CreditCard, LogOut, Zap } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import type { ReactNode } from 'react'

const nav = [
  { to: '/scan', label: 'Scan Resume', icon: ScanLine },
  { to: '/history', label: 'History', icon: History },
  { to: '/billing', label: 'Billing', icon: CreditCard },
]

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/')
  }

  return (
    <div className="flex min-h-screen bg-surface">
      {/* Sidebar */}
      <aside className="w-60 bg-white border-r border-slate-200 flex flex-col shrink-0">
        <div className="px-6 py-5 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Zap className="text-brand" size={20} strokeWidth={2.5} />
            <span className="font-bold text-slate-900 text-lg tracking-tight font-display">ResumeIQ</span>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-brand/10 text-brand'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`
              }
            >
              <Icon size={17} strokeWidth={1.75} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-4 py-4 border-t border-slate-100">
          {user && (
            <div className="mb-3">
              <p className="text-xs text-slate-500 truncate">{user.email}</p>
              <p className="text-xs text-brand font-medium capitalize mt-0.5">{user.plan} plan</p>
            </div>
          )}
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-700 transition-colors"
          >
            <LogOut size={15} />
            Log out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  )
}
