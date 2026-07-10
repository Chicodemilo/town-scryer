// ==============================================================================
// File:      frontend/src/pages/admin/AdminTables.jsx
// Purpose:   Admin "Tables" view. Lists every game_table with a per-table
//            scene_model dropdown so the admin can A/B which Claude model
//            handles scene extraction — without surfacing the choice to
//            DMs.
// Callers:   AdminLayout.jsx
// Callees:   React, api/client.js
// Modified:  2026-06-07
// ==============================================================================
import React, { useEffect, useState } from 'react';
import client from '../../api/client';

const MODELS = [
  { value: '', label: 'system default' },
  { value: 'claude-haiku-4-5-20251001', label: 'haiku 4.5' },
  { value: 'claude-sonnet-4-6', label: 'sonnet 4.6' },
  { value: 'claude-opus-4-7', label: 'opus 4.7' },
];

const IMAGE_MODELS = [
  { value: '', label: 'system default' },
  { value: 'fal-ai/recraft-v3', label: 'recraft v3 (stylized)' },
  { value: 'fal-ai/flux/dev', label: 'flux/dev (was default)' },
  { value: 'fal-ai/flux/schnell', label: 'flux/schnell (cheap)' },
  { value: 'fal-ai/flux-pro', label: 'flux pro' },
  { value: 'fal-ai/ideogram/v2', label: 'ideogram v2' },
  { value: 'fal-ai/stable-diffusion-v35-large', label: 'sd 3.5 large' },
];

function formatShortDate(iso) {
  if (!iso) return '--';
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function modelColor(model) {
  if (!model) return '#6b7280';
  if (model.includes('opus')) return '#a78bfa';
  if (model.includes('sonnet')) return '#60a5fa';
  if (model.includes('haiku')) return '#9ca3af';
  return '#d1d5db';
}

function AdminTables() {
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [savingId, setSavingId] = useState(null);

  const load = () => {
    setLoading(true);
    client.get('/api/admin/tables')
      .then((r) => {
        setTables(r.data.tables || []);
        setError(null);
      })
      .catch((e) => setError(e?.response?.data?.message || 'Failed to load tables'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleModelChange = async (id, value) => {
    setSavingId(id);
    try {
      await client.put(`/api/admin/tables/${id}/scene-model`, { scene_model: value });
      setTables((prev) => prev.map((t) => t.id === id ? { ...t, scene_model: value || null } : t));
    } catch (e) {
      setError(e?.response?.data?.message || 'Failed to save');
    } finally {
      setSavingId(null);
    }
  };

  const handleImageModelChange = async (id, value) => {
    setSavingId(id);
    try {
      await client.put(`/api/admin/tables/${id}/image-model`, { image_model: value });
      setTables((prev) => prev.map((t) => t.id === id ? { ...t, image_model: value || null } : t));
    } catch (e) {
      setError(e?.response?.data?.message || 'Failed to save');
    } finally {
      setSavingId(null);
    }
  };

  return (
    <div>
      <h2 style={t.h2}>tables</h2>
      <p style={t.muted}>
        Per-table Claude model for scene analysis. Changes take effect on the
        next session start (existing sessions stay locked to whatever they
        were started with). Blank = use system default ({'SCENE_MODEL_DEFAULT'} env var).
      </p>

      {loading && <p style={t.muted}>loading…</p>}
      {error && <p style={{ ...t.muted, color: '#ef4444' }}>{error}</p>}

      {!loading && !error && (
        <table style={t.table}>
          <thead>
            <tr>
              <th style={t.th}>id</th>
              <th style={t.th}>name</th>
              <th style={t.th}>owner</th>
              <th style={{ ...t.th, textAlign: 'right' }}>sessions</th>
              <th style={t.th}>created</th>
              <th style={t.th}>scene model</th>
              <th style={t.th}>image model</th>
            </tr>
          </thead>
          <tbody>
            {tables.map((tbl) => (
              <tr key={tbl.id} style={t.tr}>
                <td style={t.td}>{tbl.id}</td>
                <td style={t.td}>{tbl.name}</td>
                <td style={t.td}>{tbl.owner_username || '--'}</td>
                <td style={{ ...t.td, textAlign: 'right' }}>{tbl.session_count}</td>
                <td style={t.td}>{formatShortDate(tbl.created_at)}</td>
                <td style={t.td}>
                  <select
                    value={tbl.scene_model || ''}
                    onChange={(e) => handleModelChange(tbl.id, e.target.value)}
                    disabled={savingId === tbl.id}
                    style={{
                      ...t.select,
                      color: modelColor(tbl.scene_model),
                      borderColor: tbl.scene_model ? modelColor(tbl.scene_model) : '#1f1f1f',
                    }}
                  >
                    {MODELS.map((m) => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </td>
                <td style={t.td}>
                  <select
                    value={tbl.image_model || ''}
                    onChange={(e) => handleImageModelChange(tbl.id, e.target.value)}
                    disabled={savingId === tbl.id}
                    style={{
                      ...t.select,
                      color: tbl.image_model?.includes('recraft') ? '#4ade80'
                           : tbl.image_model?.includes('ideogram') ? '#fbbf24'
                           : tbl.image_model?.includes('flux') ? '#f87171'
                           : '#9ca3af',
                      borderColor: tbl.image_model ? '#3a3a3a' : '#1f1f1f',
                    }}
                  >
                    {IMAGE_MODELS.map((m) => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
            {tables.length === 0 && (
              <tr><td colSpan={7} style={{ ...t.td, color: '#6b7280', textAlign: 'center' }}>no tables yet</td></tr>
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
  table: { width: '100%', borderCollapse: 'collapse', fontSize: '12px' },
  th: { textAlign: 'left', padding: '8px 10px', borderBottom: '1px solid #1f1f1f', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 500 },
  tr: { borderBottom: '1px solid #1a1a1a' },
  td: { padding: '8px 10px', color: '#d1d5db' },
  select: {
    background: '#0a0a0a',
    border: '1px solid #1f1f1f',
    fontFamily: 'inherit',
    fontSize: '12px',
    padding: '4px 8px',
    cursor: 'pointer',
  },
};

export default AdminTables;
