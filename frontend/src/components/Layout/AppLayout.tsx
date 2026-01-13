import { Outlet, NavLink } from 'react-router-dom';
import { Workflow, FileText, Search, Settings, LogOut, User } from 'lucide-react';
import { cn } from '@/lib/cn';
import { useAuth } from '@/contexts/AuthContext';

const NAV_ITEMS = [
  { to: '/workflows', label: 'Workflows', icon: Workflow },
  { to: '/requests', label: 'Request Logs', icon: FileText },
  { to: '/discovery', label: 'Discovery', icon: Search },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export function AppLayout() {
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    if (confirm('Are you sure you want to log out?')) {
      await logout();
    }
  };

  return (
    <div className="h-screen flex">
      {/* Sidebar */}
      <aside className="w-56 bg-gray-900 text-white flex flex-col">
        {/* Logo */}
        <div className="p-4 border-b border-gray-700">
          <h1 className="text-lg font-bold">ScriptLink</h1>
          <p className="text-xs text-gray-400">Workflow Engine</p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-2">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800'
                )
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="p-4 border-t border-gray-700">
          <div className="flex items-center gap-2 mb-3">
            <User size={16} className="text-gray-400" />
            <span className="text-sm text-gray-300 truncate">{user?.username}</span>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            <LogOut size={16} />
            Log out
          </button>
          <div className="text-xs text-gray-500 mt-3">
            <p>v1.0.0</p>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 bg-gray-50 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
