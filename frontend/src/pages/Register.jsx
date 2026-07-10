// ==============================================================================
// File:      frontend/src/pages/Register.jsx
// Purpose:   Registration page component. Presents a signup form with
//            client-side validation, creates the account via the auth
//            store, and redirects to the check-email page on success.
// Callers:   App.jsx (route: /register)
// Callees:   React, react-router-dom, authStore.js, PasswordInput.jsx,
//            services/validation.js
// Modified:  2026-04-22
// ==============================================================================
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import { validateRegistration } from '../services/validation';
import PasswordInput from '../components/PasswordInput';

function Register() {
  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [errors, setErrors] = useState({});
  const { register, loading, error, clearError } = useAuthStore();
  const navigate = useNavigate();

  const handleChange = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
    clearError();
    setErrors({});
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const validationErrors = validateRegistration(form);
    if (validationErrors) {
      setErrors(validationErrors);
      return;
    }
    try {
      await register(form.username, form.email, form.password);
      navigate('/check-email');
    } catch {
      // Error is set in store
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="auth-card__title">Create Account</h1>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Username</label>
            <input type="text" value={form.username} onChange={(e) => handleChange('username', e.target.value)} required className="form-input" />
            {errors.username && <p className="form-field-error">{errors.username}</p>}
          </div>

          <div className="form-group">
            <label className="form-label">Email</label>
            <input type="email" value={form.email} onChange={(e) => handleChange('email', e.target.value)} required className="form-input" />
            {errors.email && <p className="form-field-error">{errors.email}</p>}
          </div>

          <div className="form-group form-group--last">
            <label className="form-label">Password</label>
            <PasswordInput value={form.password} onChange={(e) => handleChange('password', e.target.value)} required className="form-input" />
            {errors.password && <p className="form-field-error">{errors.password}</p>}
          </div>

          {error && <div className="form-error">{error}</div>}

          <button type="submit" disabled={loading} className="btn-submit btn-submit--success">
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>

        <p className="auth-card__footer">
          Already have an account? <a href="/login">Log In</a>
        </p>
      </div>
    </div>
  );
}

export default Register;
