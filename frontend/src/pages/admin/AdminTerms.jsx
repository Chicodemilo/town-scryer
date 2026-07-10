// ==============================================================================
// File:      frontend/src/pages/admin/AdminTerms.jsx
// Purpose:   Admin terms and conditions editor. Provides a textarea to edit
//            the terms content, save updates with version tracking, and
//            reset all user acceptances to force re-acceptance.
// Callers:   AdminLayout.jsx
// Callees:   React, api/admin.js
// Modified:  2026-04-22
// ==============================================================================
import React, { useEffect, useState } from 'react';
import { getAdminTerms, updateAdminTerms, resetAllTerms } from '../../api/admin';

function AdminTerms() {
  const [terms, setTerms] = useState(null);
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => { loadTerms(); }, []);

  const loadTerms = async () => {
    try {
      const data = await getAdminTerms();
      setTerms(data.terms);
      setContent(data.terms.content);
    } catch {} finally { setLoading(false); }
  };

  const handleSave = async () => {
    setSaving(true); setMsg(null);
    try {
      const data = await updateAdminTerms(content);
      setTerms(data.terms);
      setMsg({ ok: true, text: 'terms updated' });
    } catch {
      setMsg({ ok: false, text: 'failed to update' });
    } finally { setSaving(false); }
  };

  const handleReset = async () => {
    if (!window.confirm('Reset all user acceptances?')) return;
    try {
      await resetAllTerms();
      setMsg({ ok: true, text: 'all users must re-accept' });
    } catch {
      setMsg({ ok: false, text: 'failed to reset' });
    }
  };

  if (loading) return <p style={t.muted}>loading...</p>;

  return (
    <div>
      <h1 style={t.h1}><span style={t.prompt}>$</span> terms</h1>

      <div style={{ color: '#4b5563', fontSize: '11px', marginBottom: '16px' }}>
        version: {terms?.version || 1} | updated: {terms?.updated_at ? new Date(terms.updated_at).toLocaleString() : 'never'}
      </div>

      <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={12}
        style={{ width: '100%', padding: '12px', backgroundColor: '#0a0a0a', border: '1px solid #2a2a2a', color: '#d1d5db', fontSize: '13px', fontFamily: 'inherit', resize: 'vertical', boxSizing: 'border-box', marginBottom: '12px' }} />

      <div style={{ display: 'flex', gap: '8px' }}>
        <button onClick={handleSave} disabled={saving} style={{ ...t.btn, color: '#4ade80' }}>
          {saving ? '> saving...' : '> save'}
        </button>
        <button onClick={handleReset} style={{ ...t.btn, color: '#f59e0b' }}>{'>'} reset_all</button>
      </div>

      {msg && <div style={{ marginTop: '8px', color: msg.ok ? '#4ade80' : '#ef4444', fontSize: '12px' }}>{msg.text}</div>}
    </div>
  );
}

const t = {
  h1: { fontSize: '18px', color: '#4ade80', fontWeight: 'normal', margin: '0 0 16px', fontFamily: 'inherit' },
  prompt: { color: '#4ade80' },
  muted: { color: '#6b7280', fontSize: '13px' },
  btn: { padding: '8px 16px', backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a', fontSize: '13px', fontFamily: 'inherit', cursor: 'pointer' },
};

export default AdminTerms;
