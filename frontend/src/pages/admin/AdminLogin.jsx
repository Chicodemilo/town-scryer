// ==============================================================================
// File:      frontend/src/pages/admin/AdminLogin.jsx
// Purpose:   Admin login form component with terminal-themed styling.
//            Authenticates admin credentials via the admin store and
//            displays error feedback on failure.
// Callers:   AdminLayout.jsx
// Callees:   React, adminStore.js
// Modified:  2026-04-22
// ==============================================================================
import React, { useState } from 'react';
import useAdminStore from '../../store/adminStore';

function AdminLogin({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const { login, loading, error, clearError } = useAdminStore();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await login(username, password);
      if (onLogin) onLogin();
    } catch {}
  };

  return (
    <div style={t.wrapper}>
      <div style={t.box}>
        <div style={t.header}>
          <span style={t.prompt}>$</span> admin_login
        </div>

        <form onSubmit={handleSubmit}>
          <div style={t.field}>
            <label style={t.label}>username:</label>
            <input type="text" value={username} onChange={(e) => { setUsername(e.target.value); clearError(); }} required style={t.input} placeholder="admin" />
          </div>
          <div style={t.field}>
            <label style={t.label}>password:</label>
            <div style={t.pwRow}>
              <input type={showPw ? 'text' : 'password'} value={password} onChange={(e) => { setPassword(e.target.value); clearError(); }} required style={{ ...t.input, flex: 1 }} />
              <button type="button" onClick={() => setShowPw(!showPw)} style={t.eyeBtn}>{showPw ? 'hide' : 'show'}</button>
            </div>
          </div>

          {error && <div style={t.error}>[error] {error}</div>}

          <button type="submit" disabled={loading} style={t.submit}>
            {loading ? '> authenticating...' : '> authenticate'}
          </button>
        </form>

        <div style={t.hint}>
          dev: admin / change_me_admin_password
        </div>
      </div>
    </div>
  );
}

const t = {
  wrapper: { minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#0a0a0a', fontFamily: "'SF Mono', 'Fira Code', Consolas, monospace" },
  box: { width: '100%', maxWidth: '420px', padding: '32px', border: '1px solid #1f1f1f', backgroundColor: '#111111' },
  header: { fontSize: '16px', color: '#4ade80', marginBottom: '24px' },
  prompt: { color: '#4ade80', marginRight: '6px' },
  field: { marginBottom: '16px' },
  label: { display: 'block', marginBottom: '6px', color: '#9ca3af', fontSize: '13px' },
  input: { width: '100%', padding: '10px 12px', backgroundColor: '#0a0a0a', border: '1px solid #2a2a2a', color: '#d1d5db', fontSize: '14px', fontFamily: 'inherit', boxSizing: 'border-box', outline: 'none' },
  pwRow: { display: 'flex', gap: '8px', alignItems: 'stretch' },
  eyeBtn: { padding: '0 12px', backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a', color: '#9ca3af', fontSize: '12px', fontFamily: 'inherit', cursor: 'pointer' },
  error: { color: '#ef4444', padding: '8px 0', fontSize: '13px', marginBottom: '8px' },
  submit: { width: '100%', padding: '12px', backgroundColor: '#1a1a1a', color: '#4ade80', border: '1px solid #2a2a2a', fontSize: '14px', fontFamily: 'inherit', cursor: 'pointer', letterSpacing: '0.02em' },
  hint: { marginTop: '16px', fontSize: '11px', color: '#4b5563', textAlign: 'center' },
};

export default AdminLogin;
