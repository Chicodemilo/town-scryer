// ==============================================================================
// File:      frontend/src/pages/admin/AdminHealth.jsx
// Purpose:   Admin health monitoring page. Displays API and database status,
//            resource counts, auto-refreshing every 30 seconds, and test
//            suite results with pass/fail counts and failed test names.
// Callers:   AdminLayout.jsx
// Callees:   React, api/admin.js
// Modified:  2026-04-22
// ==============================================================================
import React, { useEffect, useState } from 'react';
import { getAdminHealth, getAdminTestResults } from '../../api/admin';

function AdminHealth() {
  const [health, setHealth] = useState(null);
  const [testResults, setTestResults] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [h, t] = await Promise.all([getAdminHealth(), getAdminTestResults()]);
      setHealth(h);
      setTestResults(t.results);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { fetchData(); const i = setInterval(fetchData, 30000); return () => clearInterval(i); }, []);

  if (loading && !health) return <p style={t.muted}>loading...</p>;

  return (
    <div>
      <h1 style={t.h1}><span style={t.prompt}>$</span> health</h1>

      {health && (
        <>
          <div style={t.grid}>
            <StatusCard label="api" value={health.api_status} ok={health.api_status === 'running'} />
            <StatusCard label="database" value={health.database} ok={health.database === 'connected'} />
            <StatCard label="users" value={health.users} />
            <StatCard label="groups" value={health.groups} />
            <StatCard label="items" value={health.items} />
            <StatCard label="alerts" value={health.alerts} />
            <StatCard label="messages" value={health.messages} />
          </div>
          <div style={{ color: '#4b5563', fontSize: '11px', marginTop: '8px', marginBottom: '24px' }}>
            last_check: {new Date(health.timestamp).toLocaleString()} (auto 30s)
          </div>
        </>
      )}

      <h2 style={t.h2}>test_results</h2>
      {!testResults ? (
        <div style={t.section}>
          <span style={t.muted}>no results. run scripts/run_tests.sh</span>
        </div>
      ) : (
        <>
          <div style={{ display: 'flex', gap: '16px', marginBottom: '8px' }}>
            <span style={{ color: '#4ade80', fontSize: '13px' }}>passed: {testResults.passed}</span>
            <span style={{ color: testResults.failed > 0 ? '#ef4444' : '#4ade80', fontSize: '13px' }}>failed: {testResults.failed}</span>
          </div>
          <div style={{ color: '#4b5563', fontSize: '11px', marginBottom: '12px' }}>
            last_run: {testResults.timestamp || 'unknown'}
          </div>
          {testResults.failed_tests && testResults.failed_tests.length > 0 && (
            <div style={t.section}>
              <div style={{ color: '#ef4444', fontSize: '12px', marginBottom: '4px' }}>failed_tests:</div>
              {testResults.failed_tests.map((ft, i) => (
                <div key={i} style={{ color: '#ef4444', fontSize: '12px', paddingLeft: '12px' }}>- {ft}</div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function StatusCard({ label, value, ok }) {
  return (
    <div style={t.card}>
      <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: ok ? '#4ade80' : '#ef4444', marginRight: '8px' }} />
      <span style={{ color: ok ? '#4ade80' : '#ef4444' }}>{value}</span>
      <div style={t.cardLabel}>{label}</div>
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <div style={t.card}>
      <span style={{ color: '#d1d5db', fontSize: '20px' }}>{value}</span>
      <div style={t.cardLabel}>{label}</div>
    </div>
  );
}

const t = {
  h1: { fontSize: '18px', color: '#4ade80', fontWeight: 'normal', margin: '0 0 20px', fontFamily: 'inherit' },
  h2: { fontSize: '14px', color: '#9ca3af', fontWeight: 'normal', margin: '0 0 12px' },
  prompt: { color: '#4ade80' },
  muted: { color: '#6b7280', fontSize: '13px' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' },
  card: { padding: '16px', backgroundColor: '#111111', border: '1px solid #1f1f1f', textAlign: 'center' },
  cardLabel: { fontSize: '11px', color: '#6b7280', marginTop: '4px', letterSpacing: '0.05em' },
  section: { padding: '12px', backgroundColor: '#111111', border: '1px solid #1f1f1f' },
};

export default AdminHealth;
