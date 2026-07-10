// ==============================================================================
// File:      frontend/src/components/NavBar.jsx
// Purpose:   Horizontal navigation bar with configurable links and theme
//            toggle button (sun/moon icon).
// Callers:   AppHeader.jsx
// Callees:   React, react-router-dom, themeStore.js
// Modified:  2026-06-01
// ==============================================================================
import React from 'react';
import { NavLink } from 'react-router-dom';
import useThemeStore from '../store/themeStore';

function NavBar({ links = [] }) {
  const { theme, toggle } = useThemeStore();

  return (
    <nav style={navStyle}>
      <div style={linksContainer}>
        {links.map(({ label, to }) => (
          <NavLink
            key={to}
            to={to}
            style={({ isActive }) => ({
              ...linkStyle,
              color: isActive ? 'var(--brand-primary)' : 'var(--text-primary)',
              borderBottom: isActive ? '2px solid var(--brand-primary)' : '2px solid transparent',
              fontWeight: isActive ? '600' : '400',
            })}
          >
            {label}
          </NavLink>
        ))}
      </div>
      <div style={rightSection}>
        <button onClick={toggle} style={toggleBtn} aria-label="Toggle theme">
          {theme === 'light' ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="5" />
              <line x1="12" y1="1" x2="12" y2="3" />
              <line x1="12" y1="21" x2="12" y2="23" />
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
              <line x1="1" y1="12" x2="3" y2="12" />
              <line x1="21" y1="12" x2="23" y2="12" />
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
            </svg>
          )}
        </button>
      </div>
    </nav>
  );
}

const navStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '0 16px',
  borderTop: '1px solid var(--border-light)',
};

const linksContainer = {
  display: 'flex',
  alignItems: 'center',
  gap: '0',
};

const linkStyle = {
  textDecoration: 'none',
  fontSize: '14px',
  padding: '10px 12px',
  transition: 'color 0.15s',
  borderRight: '1px solid var(--border-medium)',
};

const rightSection = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
};

const toggleBtn = {
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  padding: '4px',
  color: 'var(--text-muted)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};

export default NavBar;
