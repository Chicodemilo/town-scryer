// ==============================================================================
// File:      Dashboard.jsx
// Purpose:   User dashboard — simple bulleted index of the user's tables and
//            characters with links into each.
// Callers:   App.jsx (route: /dashboard)
// Callees:   React, react-router-dom, api/tables.js, api/characters.js,
//            authStore.js, PageHeader.jsx, PageContent.jsx, ContentCard.jsx
// Modified:  2026-06-05
// ==============================================================================
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import { getTables } from '../api/tables';
import { getMyCharacters } from '../api/characters';
import PageHeader from '../components/PageHeader';
import PageContent from '../components/PageContent';
import ContentCard from '../components/ContentCard';

function formatShortDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function Dashboard() {
  const { user } = useAuthStore();
  const [tables, setTables] = useState([]);
  const [characters, setCharacters] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [tablesData, charsData] = await Promise.all([
          getTables(),
          getMyCharacters(),
        ]);
        if (cancelled) return;
        setTables(tablesData.tables || []);
        setCharacters(charsData.characters || []);
      } catch (_) {
        // Non-critical: just render empty state
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <div>
      <PageHeader title="Dashboard" subtitle={`Welcome, ${user?.username}`} />
      <PageContent>
        <ContentCard style={cardStyle}>
          <h2 style={sectionHeader}>Your Tables</h2>
          {loading ? (
            <p style={mutedText}>Loading...</p>
          ) : tables.length === 0 ? (
            <p style={mutedText}>
              No tables yet. <Link to="/tables">Create one</Link> or{' '}
              <Link to="/tables/join">join with a code</Link>.
            </p>
          ) : (
            <ul style={listStyle}>
              {tables.map((t) => (
                <li key={t.id} style={itemStyle}>
                  <Link to={`/tables/${t.id}`} style={linkStyle}>{t.name}</Link>
                  <span style={metaStyle}>
                    {t.session_count || 0} campaign{t.session_count === 1 ? '' : 's'}
                    {t.created_at && ` • created ${formatShortDate(t.created_at)}`}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </ContentCard>

        <ContentCard style={{ ...cardStyle, marginTop: 16 }}>
          <h2 style={sectionHeader}>Your Characters</h2>
          {loading ? (
            <p style={mutedText}>Loading...</p>
          ) : characters.length === 0 ? (
            <p style={mutedText}>
              No characters yet. Pick a table and create or claim one.
            </p>
          ) : (
            <ul style={listStyle}>
              {characters.map((c) => (
                <li key={c.id} style={itemStyle}>
                  <Link to={`/tables/${c.table_id}`} style={linkStyle}>{c.name}</Link>
                  <span style={metaStyle}>
                    at {c.table_name || 'a table'}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </ContentCard>
      </PageContent>
    </div>
  );
}

const cardStyle = { padding: '20px 24px' };

const sectionHeader = {
  margin: '0 0 12px',
  fontSize: 16,
  color: 'var(--text-primary)',
};

const listStyle = {
  margin: 0,
  paddingLeft: 20,
  color: 'var(--text-primary)',
  lineHeight: 1.7,
};

const itemStyle = { marginBottom: 4 };

const linkStyle = {
  color: 'var(--brand-primary)',
  textDecoration: 'none',
  fontWeight: 500,
};

const metaStyle = {
  marginLeft: 8,
  fontSize: 12,
  color: 'var(--text-muted)',
};

const mutedText = {
  margin: 0,
  color: 'var(--text-muted)',
  fontSize: 14,
};

export default Dashboard;
