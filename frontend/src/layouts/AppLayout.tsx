import { Link, NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const links = [
  ['/', 'Dashboard'],
  ['/profile', 'Profile'],
  ['/users', 'Users'],
  ['/departments', 'Departments'],
  ['/upload', 'Ingestion'],
  ['/documents', 'Documents'],
  ['/rbac', 'RBAC'],
  ['/rag', 'RAG Test'],
  ['/audit', 'Audit Logs'],
  ['/system', 'System'],
] as const;

export function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="shell">
      <aside className="sidebar">
        <h2>RAG Admin</h2>
        <nav>
          {links.map(([to, label]) => (
            <NavLink key={to} to={to} className={({ isActive }) => (isActive ? 'active' : '')} end={to === '/'}>
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main>
        <header className="topbar">
          <div>
            <strong>{user?.username}</strong>
            <small>{user?.roles.join(', ') || 'No roles'}</small>
          </div>
          <div className="topbar-actions">
            <Link to="/profile">Profile</Link>
            <button onClick={() => logout()}>Logout</button>
          </div>
        </header>
        <div className="content">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
