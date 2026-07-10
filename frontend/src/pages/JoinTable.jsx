// ==============================================================================
// File:      frontend/src/pages/JoinTable.jsx
// Purpose:   Join table page. Allows players to enter an invite code (or
//            auto-fill from URL query param) to join a DM's table.
// Callers:   App.jsx (route: /tables/join)
// Callees:   React, react-router-dom, api/tables.js, authStore.js, PageHeader.jsx
// Modified:  2026-06-01
// ==============================================================================
import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import { joinTable } from '../api/tables';
import PageHeader from '../components/PageHeader';
import PageContent from '../components/PageContent';

function JoinTable() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = useAuthStore((state) => state.token);

  const [code, setCode] = useState(searchParams.get('code') || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!token) {
      const returnUrl = `/tables/join${code ? `?code=${code}` : ''}`;
      navigate(`/login?redirect=${encodeURIComponent(returnUrl)}`, { replace: true });
    }
  }, [token, navigate, code]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = code.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(null);
    try {
      const data = await joinTable(trimmed);
      const tableId = data.table_id || data.table?.id || data.id;
      navigate(`/tables/${tableId}`);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to join table. Check your invite code.');
      setLoading(false);
    }
  };

  if (!token) return null;

  return (
    <div className="join-table-page">
      <PageHeader title="Join a Table" subtitle="Enter the invite code shared by your DM" />

      <PageContent>
      <div className="join-table-card">
        {error && <div className="form-error">{error}</div>}

        <form onSubmit={handleSubmit} className="join-table-form">
          <div className="form-group">
            <label className="form-label" htmlFor="invite-code">
              Invite Code
            </label>
            <input
              id="invite-code"
              className="form-input form-input--code"
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="XXXXXX"
              maxLength={20}
              autoFocus
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            className="btn btn--primary join-table-form__submit"
            disabled={loading || !code.trim()}
          >
            {loading ? 'Joining...' : 'Join Table'}
          </button>
        </form>
      </div>
      </PageContent>
    </div>
  );
}

export default JoinTable;
