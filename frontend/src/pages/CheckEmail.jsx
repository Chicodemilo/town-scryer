// ==============================================================================
// File:      frontend/src/pages/CheckEmail.jsx
// Purpose:   Post-registration email verification prompt. Instructs the
//            user to check their inbox and provides a button to resend
//            the verification email.
// Callers:   App.jsx (route: /check-email)
// Callees:   React, authStore.js, api/auth.js
// Modified:  2026-04-22
// ==============================================================================
import React, { useState } from 'react';
import useAuthStore from '../store/authStore';
import { resendVerification } from '../api/auth';

function CheckEmail() {
  const { token } = useAuthStore();
  const [resending, setResending] = useState(false);
  const [resent, setResent] = useState(false);

  const handleResend = async () => {
    setResending(true);
    try {
      await resendVerification();
      setResent(true);
    } catch {
      // ignore
    }
    setResending(false);
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-page-public)' }}>
      <div style={{ backgroundColor: 'var(--bg-surface)', padding: '40px', borderRadius: '12px', boxShadow: 'var(--shadow-card)', width: '100%', maxWidth: '400px', textAlign: 'center' }}>
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>&#9993;</div>
        <h1 style={{ color: 'var(--text-primary)' }}>Check Your Email</h1>
        <p style={{ color: 'var(--text-muted)', marginBottom: '24px' }}>
          We've sent a verification link to your email address. Click the link to verify your account.
        </p>

        {resent ? (
          <p style={{ color: 'var(--brand-success)', fontWeight: '500' }}>Verification email resent!</p>
        ) : (
          <button
            onClick={handleResend}
            disabled={resending || !token}
            style={{ padding: '12px 32px', backgroundColor: 'var(--brand-primary)', color: 'var(--text-on-brand)', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px' }}
          >
            {resending ? 'Sending...' : 'Resend Email'}
          </button>
        )}

        <p style={{ marginTop: '24px', color: 'var(--text-muted)', fontSize: '14px' }}>
          <a href="/login">Back to Login</a>
        </p>
      </div>
    </div>
  );
}

export default CheckEmail;
