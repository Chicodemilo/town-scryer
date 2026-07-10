// ==============================================================================
// File:      frontend/src/pages/Terms.jsx
// Purpose:   Terms and conditions page. Fetches the current terms content,
//            displays it for review, and allows authenticated users to
//            accept the terms before continuing to use the app.
// Callers:   App.jsx (route: /terms)
// Callees:   React, react-router-dom, authStore.js, api/auth.js
// Modified:  2026-04-22
// ==============================================================================
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import { getTerms, acceptTerms } from '../api/auth';

function Terms() {
  const { user, refreshProfile } = useAuthStore();
  const navigate = useNavigate();
  const [terms, setTerms] = useState(null);
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);

  useEffect(() => {
    getTerms().then(data => {
      setTerms(data.terms);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const handleAccept = async () => {
    setAccepting(true);
    try {
      await acceptTerms();
      await refreshProfile();
      navigate('/');
    } catch {
      setAccepting(false);
    }
  };

  if (loading) return <div style={{ padding: '40px', textAlign: 'center' }}>Loading...</div>;

  return (
    <div style={{ padding: '20px', maxWidth: '700px', margin: '0 auto' }}>
      <h1 style={{ color: 'var(--text-primary)', marginBottom: '8px' }}>Terms & Conditions</h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: '24px', fontSize: '14px' }}>
        Please read and accept the terms below to continue using the app.
      </p>

      <div style={{ padding: '24px', backgroundColor: 'var(--bg-surface-alt)', borderRadius: '8px', border: '1px solid var(--border-primary)', maxHeight: '400px', overflowY: 'auto', marginBottom: '24px', whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>
        {terms?.content || 'No terms available.'}
      </div>

      {user && !user.terms_accepted && (
        <button onClick={handleAccept} disabled={accepting} style={{ width: '100%', padding: '14px', backgroundColor: 'var(--brand-success)', color: 'var(--text-on-brand)', border: 'none', borderRadius: '6px', fontSize: '16px', fontWeight: '500', cursor: accepting ? 'default' : 'pointer', opacity: accepting ? 0.6 : 1 }}>
          {accepting ? 'Accepting...' : 'I Accept the Terms & Conditions'}
        </button>
      )}

      {user?.terms_accepted && (
        <p style={{ textAlign: 'center', color: 'var(--brand-success)', fontWeight: '500' }}>
          You have already accepted the terms.{' '}
          <a href="/" style={{ color: 'var(--brand-primary)' }}>Go back</a>
        </p>
      )}

      {!user && (
        <p style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
          <a href="/login" style={{ color: 'var(--brand-primary)' }}>Log in</a> to accept the terms.
        </p>
      )}
    </div>
  );
}

export default Terms;
