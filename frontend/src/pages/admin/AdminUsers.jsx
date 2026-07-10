// ==============================================================================
// File:      frontend/src/pages/admin/AdminUsers.jsx
// Purpose:   Admin user management page. Lists all users with search,
//            provides admin/verified toggles, user deletion, email
//            invitations, and per-section permission editing for admins.
// Callers:   AdminLayout.jsx
// Callees:   React, adminStore.js, api/admin.js
// Modified:  2026-04-22
// ==============================================================================
import React, { useEffect, useState } from 'react';
import useAdminStore from '../../store/adminStore';
import { updateUser, deleteUser, inviteUser, getAdminUsers, updateUserPermissions } from '../../api/admin';

const ADMIN_SECTIONS = ['dashboard', 'users', 'groups', 'alerts', 'messages', 'health', 'terms'];

function AdminUsers() {
  const { users, fetchUsers, loading } = useAdminStore();
  const [search, setSearch] = useState('');
  const [tab, setTab] = useState('all');
  const [adminUsers, setAdminUsers] = useState([]);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteMsg, setInviteMsg] = useState(null);
  const [editingPerms, setEditingPerms] = useState(null);
  const [perms, setPerms] = useState({});

  useEffect(() => { fetchUsers({ search }); }, [search]);
  useEffect(() => { if (tab === 'admins') loadAdminUsers(); }, [tab]);

  const loadAdminUsers = async () => {
    try {
      const data = await getAdminUsers();
      setAdminUsers(data.users);
    } catch {}
  };

  const handleToggleAdmin = async (userId, currentStatus) => {
    await updateUser(userId, { is_admin: !currentStatus });
    fetchUsers({ search });
    if (tab === 'admins') loadAdminUsers();
  };

  const handleToggleVerified = async (userId, currentStatus) => {
    await updateUser(userId, { email_verified: !currentStatus });
    fetchUsers({ search });
  };

  const handleDelete = async (userId, username) => {
    if (window.confirm(`Delete user "${username}"?`)) {
      await deleteUser(userId);
      fetchUsers({ search });
      if (tab === 'admins') loadAdminUsers();
    }
  };

  const handleInvite = async (e) => {
    e.preventDefault();
    if (!inviteEmail) return;
    setInviteMsg(null);
    try {
      await inviteUser(inviteEmail);
      setInviteMsg({ ok: true, text: `invite sent to ${inviteEmail}` });
      setInviteEmail('');
      fetchUsers({ search });
    } catch (err) {
      setInviteMsg({ ok: false, text: err.response?.data?.error || 'failed to send invite' });
    }
  };

  const startEditPerms = (user) => {
    setEditingPerms(user.id);
    setPerms(user.admin_permissions || {});
  };

  const handlePermChange = (section) => setPerms(p => ({ ...p, [section]: !p[section] }));
  const setAllPerms = (value) => {
    const p = {};
    ADMIN_SECTIONS.forEach(s => { p[s] = value; });
    setPerms(p);
  };
  const savePerms = async (userId) => {
    await updateUserPermissions(userId, perms);
    setEditingPerms(null);
    loadAdminUsers();
  };

  const renderTable = (userList) => (
    <table style={t.table}>
      <thead>
        <tr>
          {['id', 'username', 'email', 'verified', 'admin', 'terms', 'actions'].map(h => (
            <th key={h} style={t.th}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {userList.map(user => (
          <React.Fragment key={user.id}>
            <tr style={t.tr}>
              <td style={t.td}>{user.id}</td>
              <td style={t.td}>{user.username}</td>
              <td style={t.td}>
                {user.email}
                {user.pending_email && <span style={{ color: '#f59e0b', fontSize: '11px' }}> (pending: {user.pending_email})</span>}
              </td>
              <td style={t.td}>
                <button onClick={() => handleToggleVerified(user.id, user.email_verified)} style={{ ...t.badge, color: user.email_verified ? '#4ade80' : '#f59e0b' }}>
                  [{user.email_verified ? 'yes' : 'no'}]
                </button>
              </td>
              <td style={t.td}>
                <button onClick={() => handleToggleAdmin(user.id, user.is_admin)} style={{ ...t.badge, color: user.is_admin ? '#4ade80' : '#6b7280' }}>
                  [{user.is_admin ? 'yes' : 'no'}]
                </button>
              </td>
              <td style={t.td}>
                <span style={{ color: user.terms_accepted ? '#4ade80' : '#6b7280' }}>
                  [{user.terms_accepted ? 'yes' : 'no'}]
                </span>
              </td>
              <td style={t.td}>
                {tab === 'admins' && user.is_admin && (
                  <button onClick={() => startEditPerms(user)} style={{ ...t.action, color: '#60a5fa' }}>[perms]</button>
                )}
                <button onClick={() => handleDelete(user.id, user.username)} style={{ ...t.action, color: '#ef4444' }}>[del]</button>
              </td>
            </tr>
            {editingPerms === user.id && (
              <tr>
                <td colSpan={7} style={{ ...t.td, backgroundColor: '#0a0a0a', padding: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                    <span style={{ color: '#9ca3af' }}>permissions for {user.username}:</span>
                    <button onClick={() => setAllPerms(true)} style={t.smallBtn}>[all on]</button>
                    <button onClick={() => setAllPerms(false)} style={t.smallBtn}>[all off]</button>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginBottom: '12px' }}>
                    {ADMIN_SECTIONS.map(section => (
                      <label key={section} style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer', color: '#9ca3af', fontSize: '13px' }}>
                        <input type="checkbox" checked={!!perms[section]} onChange={() => handlePermChange(section)} />
                        {section}
                      </label>
                    ))}
                  </div>
                  <button onClick={() => savePerms(user.id)} style={{ ...t.action, color: '#4ade80' }}>[save]</button>
                  <button onClick={() => setEditingPerms(null)} style={{ ...t.action, color: '#6b7280', marginLeft: '8px' }}>[cancel]</button>
                </td>
              </tr>
            )}
          </React.Fragment>
        ))}
      </tbody>
    </table>
  );

  return (
    <div>
      <h1 style={t.h1}><span style={t.prompt}>$</span> users</h1>

      {/* Invite */}
      <div style={t.section}>
        <div style={{ color: '#9ca3af', fontSize: '13px', marginBottom: '8px' }}>invite_user:</div>
        <form onSubmit={handleInvite} style={{ display: 'flex', gap: '8px' }}>
          <input type="email" placeholder="user@example.com" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} required style={t.input} />
          <button type="submit" style={t.submitBtn}>{'>'} send</button>
        </form>
        {inviteMsg && <div style={{ color: inviteMsg.ok ? '#4ade80' : '#ef4444', fontSize: '12px', marginTop: '6px' }}>{inviteMsg.text}</div>}
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '4px', marginBottom: '16px' }}>
        <button onClick={() => setTab('all')} style={{ ...t.tabBtn, color: tab === 'all' ? '#4ade80' : '#6b7280', borderBottom: tab === 'all' ? '1px solid #4ade80' : '1px solid transparent' }}>{'>'} all</button>
        <button onClick={() => setTab('admins')} style={{ ...t.tabBtn, color: tab === 'admins' ? '#4ade80' : '#6b7280', borderBottom: tab === 'admins' ? '1px solid #4ade80' : '1px solid transparent' }}>{'>'} admins</button>
      </div>

      {tab === 'all' && (
        <>
          <input type="text" placeholder="search..." value={search} onChange={(e) => setSearch(e.target.value)} style={{ ...t.input, marginBottom: '16px' }} />
          {loading && <p style={t.muted}>loading...</p>}
          {renderTable(users)}
        </>
      )}

      {tab === 'admins' && renderTable(adminUsers)}
    </div>
  );
}

const t = {
  h1: { fontSize: '18px', color: '#4ade80', fontWeight: 'normal', margin: '0 0 20px', fontFamily: 'inherit' },
  prompt: { color: '#4ade80' },
  muted: { color: '#6b7280', fontSize: '13px' },
  section: { padding: '16px', backgroundColor: '#111111', border: '1px solid #1f1f1f', marginBottom: '20px' },
  input: { flex: 1, padding: '8px 12px', backgroundColor: '#0a0a0a', border: '1px solid #2a2a2a', color: '#d1d5db', fontSize: '13px', fontFamily: 'inherit', boxSizing: 'border-box' },
  submitBtn: { padding: '8px 16px', backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a', color: '#4ade80', fontSize: '13px', fontFamily: 'inherit', cursor: 'pointer' },
  tabBtn: { padding: '6px 12px', backgroundColor: 'transparent', border: 'none', fontSize: '13px', fontFamily: 'inherit', cursor: 'pointer' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { padding: '8px', color: '#6b7280', fontSize: '11px', textAlign: 'left', borderBottom: '1px solid #1f1f1f', letterSpacing: '0.05em' },
  tr: { borderBottom: '1px solid #1a1a1a' },
  td: { padding: '8px', fontSize: '13px', color: '#d1d5db' },
  badge: { background: 'none', border: 'none', cursor: 'pointer', fontSize: '12px', fontFamily: 'inherit', padding: 0 },
  action: { background: 'none', border: 'none', cursor: 'pointer', fontSize: '12px', fontFamily: 'inherit', padding: 0 },
  smallBtn: { background: 'none', border: 'none', cursor: 'pointer', fontSize: '11px', fontFamily: 'inherit', color: '#9ca3af', padding: 0 },
};

export default AdminUsers;
