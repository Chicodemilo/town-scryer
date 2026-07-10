// ==============================================================================
// File:      frontend/src/pages/admin/AdminLayout.jsx
// Purpose:   Admin panel layout shell. Renders a terminal-themed sidebar
//            with permission-filtered navigation, nested admin routes,
//            and login gate. Contains all admin sub-page routing.
// Callers:   App.jsx (route: /overview/*)
// Callees:   React, react-router-dom, adminStore.js, AdminLogin.jsx,
//            AdminDashboard.jsx, AdminUsers.jsx, AdminHealth.jsx,
//            AdminTerms.jsx
// Modified:  2026-06-01
// ==============================================================================
import React from 'react';
import { Routes, Route, NavLink, useNavigate } from 'react-router-dom';
import useAdminStore from '../../store/adminStore';
import AdminLogin from './AdminLogin';
import AdminDashboard from './AdminDashboard';
import AdminUsers from './AdminUsers';
import AdminHealth from './AdminHealth';
import AdminTerms from './AdminTerms';
import AdminSessions from './AdminSessions';
import AdminTables from './AdminTables';

const SECTIONS = [
  { path: '', label: 'dashboard', key: 'dashboard', element: <AdminDashboard />, index: true },
  { path: 'sessions', label: 'sessions', key: 'sessions', element: <AdminSessions /> },
  { path: 'tables', label: 'tables', key: 'tables', element: <AdminTables /> },
  { path: 'users', label: 'users', key: 'users', element: <AdminUsers /> },
  { path: 'health', label: 'health', key: 'health', element: <AdminHealth /> },
  { path: 'terms', label: 'terms', key: 'terms', element: <AdminTerms /> },
];

function hasSection(adminUser, key) {
  if (!adminUser) return false;
  const perms = adminUser.admin_permissions;
  if (!perms || Object.keys(perms).length === 0) return true;
  return !!perms[key];
}

function AdminLayout() {
  const { isAuthenticated, adminUser, logout, initialize } = useAdminStore();
  const navigate = useNavigate();

  React.useEffect(() => { initialize(); }, []);

  if (!isAuthenticated) {
    return <AdminLogin />;
  }

  const visibleSections = SECTIONS.filter(s => hasSection(adminUser, s.key));

  return (
    <div style={t.root}>
      <aside style={t.sidebar}>
        <div style={t.sidebarHeader}>
          <span style={t.prompt}>$</span> ADMIN : {import.meta.env.VITE_APP_NAME || 'Town Scryer'}
          <div style={t.userLine}>{adminUser?.username}</div>
        </div>
        <nav style={t.nav}>
          {visibleSections.map(s => (
            <NavLink key={s.key} to={s.index ? '/overview' : `/overview/${s.path}`} end={s.index} style={({ isActive }) => ({ ...t.navLink, color: isActive ? '#4ade80' : '#9ca3af', borderLeft: isActive ? '2px solid #4ade80' : '2px solid transparent' })}>
              <span style={t.prompt}>{'>'}</span> {s.label}
            </NavLink>
          ))}
        </nav>
        <button onClick={() => { logout(); navigate('/overview'); }} style={t.logoutBtn}>
          <span style={t.prompt}>$</span> logout
        </button>
      </aside>

      <main style={t.main}>
        <Routes>
          {visibleSections.map(s => (
            <Route key={s.key} path={s.path || undefined} index={s.index} element={s.element} />
          ))}
        </Routes>
      </main>
    </div>
  );
}

// Terminal theme tokens
const t = {
  root: { display: 'flex', minHeight: '100vh', fontFamily: "'SF Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace", backgroundColor: '#0a0a0a', color: '#d1d5db' },
  sidebar: { width: '220px', backgroundColor: '#111111', borderRight: '1px solid #1f1f1f', display: 'flex', flexDirection: 'column' },
  sidebarHeader: { padding: '20px 16px', borderBottom: '1px solid #1f1f1f', fontSize: '14px', color: '#4ade80' },
  userLine: { fontSize: '11px', color: '#6b7280', marginTop: '4px' },
  nav: { padding: '8px 0', flex: 1 },
  navLink: { display: 'block', padding: '8px 16px', textDecoration: 'none', fontSize: '13px', letterSpacing: '0.02em' },
  prompt: { color: '#4ade80', marginRight: '6px' },
  logoutBtn: { padding: '12px 16px', backgroundColor: 'transparent', color: '#ef4444', border: 'none', borderTop: '1px solid #1f1f1f', cursor: 'pointer', fontSize: '13px', fontFamily: 'inherit', textAlign: 'left', letterSpacing: '0.02em' },
  main: { flex: 1, padding: '24px 32px', overflow: 'auto' },
};

export default AdminLayout;
