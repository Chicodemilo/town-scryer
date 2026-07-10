// ==============================================================================
// File:      frontend/src/pages/Tables.jsx
// Purpose:   Tables listing page. Shows all tables the user owns or has joined,
//            with ability to create new tables or join via invite code.
// Callers:   App.jsx (route: /tables)
// Callees:   React, react-router-dom, api/tables.js, PageHeader.jsx, ContentCard.jsx
// Modified:  2026-06-01
// ==============================================================================
import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getTables, createTable, joinTable } from '../api/tables';
import PageHeader from '../components/PageHeader';
import PageContent from '../components/PageContent';
import ContentCard from '../components/ContentCard';

function Tables() {
  const navigate = useNavigate();
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Create form
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [creating, setCreating] = useState(false);

  // Join form
  const [showJoin, setShowJoin] = useState(false);
  const [joinCode, setJoinCode] = useState('');
  const [joining, setJoining] = useState(false);

  const fetchTables = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getTables();
      setTables(data.tables || data || []);
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to load tables.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTables();
  }, [fetchTables]);

  const handleCreate = useCallback(async (e) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await createTable(newName.trim());
      setNewName('');
      setShowCreate(false);
      await fetchTables();
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to create table.');
    } finally {
      setCreating(false);
    }
  }, [newName, fetchTables]);

  const handleJoin = useCallback(async (e) => {
    e.preventDefault();
    if (!joinCode.trim()) return;
    setJoining(true);
    setError(null);
    try {
      await joinTable(joinCode.trim());
      setJoinCode('');
      setShowJoin(false);
      await fetchTables();
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to join table.');
    } finally {
      setJoining(false);
    }
  }, [joinCode, fetchTables]);

  return (
    <div className="tables-page">
      <PageHeader
        title="Tables"
        action={
          <div className="tables-page__header-actions">
            <div style={actionGroup}>
              <button
                className="btn btn--primary"
                onClick={() => { setShowCreate(true); setShowJoin(false); }}
              >
                Create New Table
              </button>
              <span style={actionHint}>Start a campaign as DM</span>
            </div>
            <div style={actionGroup}>
              <button
                className="btn btn--blue"
                onClick={() => { setShowJoin(true); setShowCreate(false); }}
              >
                Join Table
              </button>
              <span style={actionHint}>Enter a code from your DM</span>
            </div>
          </div>
        }
      />

      <PageContent>
      {error && <div className="tables-error">{error}</div>}

      {/* Create form */}
      {showCreate && (
        <ContentCard className="tables-inline-form">
          <form onSubmit={handleCreate} className="tables-inline-form__row">
            <input
              type="text"
              placeholder="Table name..."
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="tables-inline-form__input"
              autoFocus
              maxLength={100}
            />
            <button
              type="submit"
              className="btn btn--primary btn--small"
              disabled={creating || !newName.trim()}
            >
              {creating ? 'Creating...' : 'Create'}
            </button>
            <button
              type="button"
              className="btn btn--ghost btn--small"
              onClick={() => setShowCreate(false)}
            >
              Cancel
            </button>
          </form>
        </ContentCard>
      )}

      {/* Join form */}
      {showJoin && (
        <ContentCard className="tables-inline-form">
          <form onSubmit={handleJoin} className="tables-inline-form__row">
            <input
              type="text"
              placeholder="Invite code..."
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value)}
              className="tables-inline-form__input"
              autoFocus
            />
            <button
              type="submit"
              className="btn btn--blue btn--small"
              disabled={joining || !joinCode.trim()}
            >
              {joining ? 'Joining...' : 'Join'}
            </button>
            <button
              type="button"
              className="btn btn--ghost btn--small"
              onClick={() => setShowJoin(false)}
            >
              Cancel
            </button>
          </form>
        </ContentCard>
      )}

      {loading && <p className="tables-loading">Loading tables...</p>}

      {!loading && tables.length === 0 && !error && (
        <div className="empty-state">
          <div className="empty-state__icon">&#9876;</div>
          <h2 className="empty-state__title">No tables yet</h2>
          <p className="empty-state__text">
            Create a table to organize your campaigns, or join one with an invite code.
          </p>
        </div>
      )}

      {!loading && tables.length > 0 && (
        <div className="tables-grid">
          {tables.map((table) => (
            <ContentCard
              key={table.id}
              className="tables-card"
              onClick={() => navigate(`/tables/${table.id}`)}
            >
              <h3 className="tables-card__name">{table.name}</h3>
              <div className="tables-card__meta">
                <span className={`tables-card__role tables-card__role--${table.role?.toLowerCase() || 'player'}`}>
                  {table.role || 'Player'}
                </span>
                <span className="tables-card__members">
                  {table.member_count || table.members?.length || 0} member{(table.member_count || table.members?.length || 0) !== 1 ? 's' : ''}
                </span>
              </div>
            </ContentCard>
          ))}
        </div>
      )}
      </PageContent>
    </div>
  );
}

const actionGroup = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  gap: 4,
};

const actionHint = {
  fontSize: 11,
  color: 'var(--text-muted)',
};

export default Tables;
