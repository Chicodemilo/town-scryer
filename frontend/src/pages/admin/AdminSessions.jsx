// ==============================================================================
// File:      frontend/src/pages/admin/AdminSessions.jsx
// Purpose:   Admin Sessions table. Shows every session sorted worst-first
//            by quality_score (high = bad). Quick triage view for finding
//            problem runs — DM corrections / regens / poor scene flow.
// Callers:   AdminLayout.jsx
// Callees:   React, api/client.js
// Modified:  2026-06-06
// ==============================================================================
import React, { useEffect, useState } from 'react';
import client from '../../api/client';

function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return '--';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function formatShortDate(iso) {
  if (!iso) return '--';
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function scoreColor(score) {
  if (score >= 40) return '#ef4444';   // red
  if (score >= 10) return '#f59e0b';   // amber
  if (score <= -30) return '#4ade80';  // bright green (clean run)
  if (score < 0)   return '#86efac';   // soft green
  return '#9ca3af';                    // neutral
}

function AdminSessions() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sort, setSort] = useState('quality');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    client.get(`/api/admin/sessions?sort=${sort}&limit=200`)
      .then((r) => {
        if (cancelled) return;
        setSessions(r.data.sessions || []);
        setError(null);
      })
      .catch((e) => {
        if (!cancelled) setError(e?.response?.data?.message || 'Failed to load sessions');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [sort]);

  return (
    <div>
      <h2 style={t.h2}>sessions</h2>
      <p style={t.muted}>
        Quality score: <b style={{color:'#ef4444'}}>high = bad</b>. +20 per DM correction, +10 per regen, -10 per scene naturally accepted, -15 per thumbs-up.
      </p>
      <p style={t.muted}>
        Audits column: <b style={{color:'#60a5fa'}}>N</b> = vision audits ran (triggered when quality_score &ge; 30). <b style={{color:'#a78bfa'}}>N/R</b> = N audits ran, R triggered a fal retry.
      </p>

      <div style={t.toolbar}>
        <button style={{ ...t.tab, ...(sort === 'quality' ? t.tabActive : null) }} onClick={() => setSort('quality')}>
          {'>'} worst first
        </button>
        <button style={{ ...t.tab, ...(sort === 'recent' ? t.tabActive : null) }} onClick={() => setSort('recent')}>
          {'>'} most recent
        </button>
      </div>

      {loading && <p style={t.muted}>loading…</p>}
      {error && <p style={{ ...t.muted, color: '#ef4444' }}>{error}</p>}

      {!loading && !error && (
        <table style={t.table}>
          <thead>
            <tr>
              <th style={t.th}>id</th>
              <th style={t.th}>user</th>
              <th style={t.th}>table</th>
              <th style={t.th}>status</th>
              <th style={{ ...t.th, textAlign: 'right' }}>score</th>
              <th style={t.th}>model</th>
              <th style={{ ...t.th, textAlign: 'right' }}>audits</th>
              <th style={{ ...t.th, textAlign: 'right' }}>images</th>
              <th style={{ ...t.th, textAlign: 'right' }}>regens</th>
              <th style={{ ...t.th, textAlign: 'right' }}>duration</th>
              <th style={{ ...t.th, textAlign: 'right' }}>cost</th>
              <th style={t.th}>started</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id} style={t.tr}>
                <td style={t.td}>{s.id}</td>
                <td style={t.td}>{s.username || '--'}</td>
                <td style={t.td}>{s.table_name || '--'}</td>
                <td style={{ ...t.td, color: s.status === 'ended' ? '#6b7280' : s.status === 'active' ? '#4ade80' : '#f59e0b' }}>
                  {s.status}
                </td>
                <td style={{ ...t.td, textAlign: 'right', color: scoreColor(s.quality_score), fontWeight: 600 }}>
                  {s.quality_score > 0 ? `+${s.quality_score}` : s.quality_score}
                </td>
                <td style={{
                  ...t.td,
                  color: s.scene_model?.includes('opus') ? '#a78bfa'
                       : s.scene_model?.includes('sonnet') ? '#60a5fa'
                       : s.scene_model?.includes('haiku') ? '#6b7280'
                       : '#444',
                }}>
                  {s.scene_model
                    ? s.scene_model.replace('claude-', '').replace('-20251001', '')
                    : '—'}
                </td>
                <td style={{ ...t.td, textAlign: 'right', color: s.audit_retry_count > 0 ? '#a78bfa' : (s.audit_count > 0 ? '#60a5fa' : '#6b7280') }}>
                  {s.audit_count > 0 ? `${s.audit_count}${s.audit_retry_count > 0 ? '/' + s.audit_retry_count : ''}` : '—'}
                </td>
                <td style={{ ...t.td, textAlign: 'right' }}>{s.image_count}</td>
                <td style={{ ...t.td, textAlign: 'right' }}>{s.regen_count}</td>
                <td style={{ ...t.td, textAlign: 'right' }}>{formatDuration(s.duration_s)}</td>
                <td style={{ ...t.td, textAlign: 'right' }}>${(s.estimated_cost_cents / 100).toFixed(2)}</td>
                <td style={t.td}>{formatShortDate(s.started_at)}</td>
              </tr>
            ))}
            {sessions.length === 0 && (
              <tr><td colSpan={12} style={{ ...t.td, color: '#6b7280', textAlign: 'center' }}>no sessions yet</td></tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}

const t = {
  h2: { fontSize: '20px', color: '#4ade80', margin: '0 0 8px', fontWeight: 500 },
  muted: { fontSize: '12px', color: '#9ca3af', margin: '0 0 16px' },
  toolbar: { display: 'flex', gap: '8px', marginBottom: '16px' },
  tab: { background: 'transparent', color: '#9ca3af', border: '1px solid #1f1f1f', padding: '6px 12px', fontFamily: 'inherit', fontSize: '12px', cursor: 'pointer' },
  tabActive: { color: '#4ade80', borderColor: '#4ade80' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: '12px' },
  th: { textAlign: 'left', padding: '8px 10px', borderBottom: '1px solid #1f1f1f', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 500 },
  tr: { borderBottom: '1px solid #1a1a1a' },
  td: { padding: '8px 10px', color: '#d1d5db' },
};

export default AdminSessions;
