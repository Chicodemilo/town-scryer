// ==============================================================================
// File:      frontend/src/pages/VerifyEmail.jsx
// Purpose:   Email verification handler. Reads the verification token from
//            the URL, calls the appropriate verify endpoint (new account or
//            email change), and displays success or error status.
// Callers:   App.jsx (route: /verify-email)
// Callees:   React, react-router-dom, api/auth.js, api/client.js
// Modified:  2026-04-22
// ==============================================================================
import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { verifyEmail } from '../api/auth';
import client from '../api/client';
import useAuthStore from '../store/authStore';

function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('verifying');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    const type = searchParams.get('type');
    if (!token) {
      setStatus('error');
      setMessage('No verification token provided.');
      return;
    }

    const verifyFn = type === 'email-change'
      ? () => client.get(`/api/auth/verify-new-email?token=${token}`).then(r => r.data)
      : () => verifyEmail(token);

    verifyFn()
      .then((data) => {
        setStatus('success');
        setMessage(type === 'email-change' ? 'Your email has been updated!' : 'Your email has been verified!');
        if (data?.token) {
          localStorage.setItem('token', data.token);
          localStorage.setItem('user', JSON.stringify(data.user));
          useAuthStore.setState({ token: data.token, user: data.user });
        }
      })
      .catch((err) => {
        setStatus('error');
        setMessage(err.response?.data?.error || 'Verification failed. The link may be invalid or expired.');
      });
  }, [searchParams]);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-page-public)' }}>
      <div style={{ backgroundColor: 'var(--bg-surface)', padding: '40px', borderRadius: '12px', boxShadow: 'var(--shadow-card)', width: '100%', maxWidth: '400px', textAlign: 'center' }}>
        {status === 'verifying' && (
          <>
            <h1 style={{ color: 'var(--text-primary)' }}>Verifying...</h1>
            <p style={{ color: 'var(--text-muted)' }}>Please wait while we verify your email.</p>
          </>
        )}
        {status === 'success' && (
          <>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>&#10003;</div>
            <h1 style={{ color: 'var(--brand-success)' }}>Email Verified!</h1>
            <p style={{ color: 'var(--text-muted)' }}>{message}</p>
            <a href="/login" style={{ display: 'inline-block', marginTop: '20px', padding: '12px 32px', backgroundColor: 'var(--brand-primary)', color: 'var(--text-on-brand)', textDecoration: 'none', borderRadius: '6px' }}>
              Log In
            </a>
          </>
        )}
        {status === 'error' && (
          <>
            <div style={{ fontSize: '48px', marginBottom: '16px', color: 'var(--brand-danger)' }}>&#10007;</div>
            <h1 style={{ color: 'var(--brand-danger)' }}>Verification Failed</h1>
            <p style={{ color: 'var(--text-muted)' }}>{message}</p>
            <a href="/login" style={{ display: 'inline-block', marginTop: '20px', padding: '12px 32px', backgroundColor: 'var(--brand-primary)', color: 'var(--text-on-brand)', textDecoration: 'none', borderRadius: '6px' }}>
              Go to Login
            </a>
          </>
        )}
      </div>
    </div>
  );
}

export default VerifyEmail;
