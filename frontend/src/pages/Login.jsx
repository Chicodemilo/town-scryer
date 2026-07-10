// ==============================================================================
// File:      frontend/src/pages/Login.jsx
// Purpose:   Login page component. Presents a username/password form,
//            authenticates via the auth store, and redirects to home or
//            terms page on success.
// Callers:   App.jsx (route: /login)
// Callees:   React, react-router-dom, authStore.js, PasswordInput.jsx
// Modified:  2026-04-22
// ==============================================================================
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import PasswordInput from '../components/PasswordInput';

function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const { login, loading, error, clearError } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const data = await login(username, password);
      if (data.user && !data.user.terms_accepted) {
        navigate('/terms');
      } else {
        navigate('/dashboard');
      }
    } catch {
      // Error is set in store
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="auth-card__title">Log In</h1>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Username or Email</label>
            <input
              type="text"
              value={username}
              onChange={(e) => { setUsername(e.target.value); clearError(); }}
              required
              className="form-input"
              placeholder="Enter username or email"
            />
          </div>

          <div className="form-group form-group--last">
            <label className="form-label">Password</label>
            <PasswordInput
              value={password}
              onChange={(e) => { setPassword(e.target.value); clearError(); }}
              required
              className="form-input"
            />
          </div>

          {error && <div className="form-error">{error}</div>}

          <button type="submit" disabled={loading} className="btn-submit">
            {loading ? 'Signing In...' : 'Sign In'}
          </button>
        </form>

        <p className="auth-card__footer">
          Don't have an account? <a href="/register">Register</a>
        </p>
      </div>
    </div>
  );
}

export default Login;
