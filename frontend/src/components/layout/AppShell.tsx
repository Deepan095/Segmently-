import type { ReactNode } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import {
  FolderKanban,
  LayoutDashboard,
  LogOut,
  Scissors,
  Settings,
  Shield,
} from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { cn } from '../../lib/utils';

interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
  { label: 'Projects', to: '/projects', icon: FolderKanban },
  { label: 'Clips', to: '/clips', icon: Scissors },
  { label: 'Settings', to: '/settings', icon: Settings },
];

const linkClasses = (isActive: boolean): string =>
  cn(
    'flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-colors',
    isActive ? 'bg-purple-100 text-purple-700' : 'text-gray-600 hover:bg-gray-100',
  );

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex min-h-screen bg-gray-50">
      <aside className="hidden w-64 flex-col border-r border-gray-200 bg-white/80 backdrop-blur-lg md:flex">
        <div className="px-6 py-5 text-xl font-bold text-purple-600">Segmently</div>
        <nav className="flex flex-1 flex-col gap-1 px-3 pb-4">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink key={item.to} to={item.to} className={({ isActive }) => linkClasses(isActive)}>
                <Icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            );
          })}
          {user?.is_admin && (
            <NavLink to="/admin" className={({ isActive }) => linkClasses(isActive)}>
              <Shield className="h-4 w-4" />
              Admin
            </NavLink>
          )}
        </nav>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-gray-200 bg-white/80 px-6 py-3 backdrop-blur-lg">
          <span className="text-sm text-gray-500">
            {user ? user.full_name ?? user.email : ''}
          </span>
          <button
            type="button"
            onClick={handleLogout}
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-100"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        </header>
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
