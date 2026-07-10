// ==============================================================================
// File:      frontend/src/pages/admin/AdminDashboard.jsx
// Purpose:   Admin dashboard overview page. Displays stat cards for users,
//            groups, items, alerts, messages, and recent signups.
// Callers:   AdminLayout.jsx
// Callees:   React, adminStore.js
// Modified:  2026-04-22
// ==============================================================================
import React, { useEffect } from 'react';
import useAdminStore from '../../store/adminStore';

function AdminDashboard() {
  const { stats, fetchStats, loading } = useAdminStore();

  useEffect(() => { fetchStats(); }, []);

  return (
    <div>
      <h1 style={t.h1}><span style={t.prompt}>$</span> dashboard</h1>

      {loading && <p style={t.muted}>loading stats...</p>}

      {stats && (
        <div style={t.grid}>
          <StatCard label="users" value={stats.users} />
          <StatCard label="groups" value={stats.groups} />
          <StatCard label="items" value={stats.items} />
          <StatCard label="alerts" value={stats.alerts || 0} />
          <StatCard label="messages" value={stats.messages || 0} />
          <StatCard label="signups_7d" value={stats.recent_signups} />
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <div style={t.card}>
      <div style={t.cardValue}>{value}</div>
      <div style={t.cardLabel}>{label}</div>
    </div>
  );
}

const t = {
  h1: { fontSize: '18px', color: '#4ade80', fontWeight: 'normal', margin: '0 0 24px', fontFamily: 'inherit' },
  prompt: { color: '#4ade80' },
  muted: { color: '#6b7280', fontSize: '13px' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px' },
  card: { padding: '20px', backgroundColor: '#111111', border: '1px solid #1f1f1f', textAlign: 'center' },
  cardValue: { fontSize: '28px', color: '#4ade80', fontWeight: 'bold', marginBottom: '4px' },
  cardLabel: { fontSize: '12px', color: '#6b7280', letterSpacing: '0.05em' },
};

export default AdminDashboard;
