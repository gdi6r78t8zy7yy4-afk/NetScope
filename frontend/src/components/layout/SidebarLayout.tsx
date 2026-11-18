import { useState } from 'react'
import { NavLink } from 'react-router-dom'

// Use ChildrenType type alias for clarity
type ChildrenType = React.ReactNode

const menuItems = [
  { path: '/dashboard', label: 'Overview' },
  { path: '/discovery', label: 'Network Discovery' },
  { path: '/assets', label: 'Asset Inventory' },
  { path: '/scanning', label: 'Port Scanner' },
  { path: '/analysis', label: 'Host Analysis' },
  { path: '/vulnerabilities', label: 'Vulnerabilities' },
  { path: '/risk', label: 'Risk Analysis' },
  { path: '/topology', label: 'Network Topology' },
  { path: '/history', label: 'Scan History' },
  { path: '/settings', label: 'Settings' },
]

export function SidebarLayout({ children }: { children: ChildrenType }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100">
      {/* Sidebar */}
      <aside
        className={`bg-slate-900 border-r border-slate-800 flex-col transition-all duration-300 ${
          isSidebarOpen ? 'w-64' : 'w-16'
        }`}
      >
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <h1 className="text-xl font-bold text-emerald-400">NetScope</h1>
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="p-1 rounded hover:bg-slate-800"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d={isSidebarOpen ? 'M6 18L18 6M6 6l12 12' : 'M4 6h16M4 12h16M4 18h16'}
              />
            </svg>
          </button>
        </div>

        <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
          {menuItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className="flex items-center px-3 py-2 rounded-md text-slate-400 hover:text-emerald-400 hover:bg-slate-800 transition-colors"
            >
              <span className="flex-1 text-sm">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-slate-800">
          <div className="text-xs text-slate-500">
            v1.0.0
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  )
}

export default SidebarLayout
