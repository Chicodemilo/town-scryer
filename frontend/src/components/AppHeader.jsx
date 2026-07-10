// ==============================================================================
// File:      frontend/src/components/AppHeader.jsx
// Purpose:   Main application header shown on authenticated routes. Displays
//            app name, user avatar, and navigation bar.
// Callers:   App.jsx
// Callees:   React, react-router-dom, NavBar.jsx, authStore.js
// Modified:  2026-06-01
// ==============================================================================
import React from 'react';
import { Link } from 'react-router-dom';
import NavBar from './NavBar';
import useAuthStore from '../store/authStore';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5151';
const APP_NAME = import.meta.env.VITE_APP_NAME || 'My App';

function avatarUrl(user) {
  if (user?.avatar) return `${API_URL}/api/uploads/avatars/${user.avatar}_sm.jpg`;
  return null;
}

function AppHeader({ links = [] }) {
  const { user } = useAuthStore();

  const avatarSrc = avatarUrl(user);

  return (
    <header style={headerStyle}>
      <div style={headerInner}>
        {/* Top section */}
        <div style={topRow}>
          {/* Left: App name */}
          <Link to="/dashboard" style={appNameStyle}>
            {APP_NAME}
          </Link>

          {/* Right: User avatar */}
          <Link to="/profile" style={avatarLink}>
            {avatarSrc ? (
              <img src={avatarSrc} alt="" style={avatarImgStyle} />
            ) : (
              <span style={avatarPlaceholder}>
                {user?.username?.charAt(0).toUpperCase() || '?'}
              </span>
            )}
          </Link>
        </div>

        {/* Bottom section: NavBar */}
        <NavBar links={links} />
      </div>
    </header>
  );
}

const headerStyle = {
  width: '100%',
  backgroundColor: 'var(--bg-surface)',
  borderBottom: '1px solid var(--border-medium)',
  position: 'sticky',
  top: 0,
  zIndex: 100,
};

const headerInner = {
  maxWidth: '960px',
  minWidth: '320px',
  width: '92%',
  margin: '0 auto',
};

const topRow = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '10px 16px',
  borderBottom: '1px solid var(--border-light)',
};

const appNameStyle = {
  fontSize: '15px',
  fontWeight: '600',
  color: 'var(--text-muted)',
  textDecoration: 'none',
  whiteSpace: 'nowrap',
};

const avatarLink = {
  textDecoration: 'none',
  flexShrink: 0,
};

const avatarImgStyle = {
  width: '32px',
  height: '32px',
  borderRadius: '50%',
  objectFit: 'cover',
  display: 'block',
};

const avatarPlaceholder = {
  width: '32px',
  height: '32px',
  borderRadius: '50%',
  backgroundColor: 'var(--brand-primary)',
  color: 'var(--text-on-brand)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: '14px',
  fontWeight: '600',
};

export default AppHeader;
