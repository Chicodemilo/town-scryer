// ==============================================================================
// File:      frontend/src/pages/Profile.jsx
// Purpose:   User profile page. Shows user info, avatar with upload
//            capability, email change form, theme toggle, and logout button.
// Callers:   App.jsx (route: /profile)
// Callees:   React, react-router-dom, authStore.js, themeStore.js,
//            api/auth.js, PageHeader.jsx, ContentCard.jsx
// Modified:  2026-06-01
// ==============================================================================
import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import { changeEmail, uploadAvatar } from '../api/auth';
import useThemeStore from '../store/themeStore';
import PageHeader from '../components/PageHeader';
import PageContent from '../components/PageContent';
import ContentCard from '../components/ContentCard';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5151';

function avatarUrl(user, size = 'md') {
  if (user?.avatar) return `${API_URL}/api/uploads/avatars/${user.avatar}_${size}.jpg`;
  return null;
}

function Profile() {
  const { user, logout, refreshProfile } = useAuthStore();
  const { theme, toggle } = useThemeStore();
  const navigate = useNavigate();
  const fileRef = useRef(null);
  const [newEmail, setNewEmail] = useState('');
  const [emailMsg, setEmailMsg] = useState(null);
  const [emailErr, setEmailErr] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);

  if (!user) {
    navigate('/login');
    return null;
  }

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleChangeEmail = async (e) => {
    e.preventDefault();
    if (!newEmail || newEmail === user.email) return;
    setSubmitting(true);
    setEmailMsg(null);
    setEmailErr(null);
    try {
      await changeEmail(newEmail);
      setEmailMsg('Verification email sent to your new address. Your email will update once verified.');
      setNewEmail('');
      await refreshProfile();
    } catch (err) {
      setEmailErr(err.response?.data?.error || 'Failed to change email');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAvatarChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadAvatar(file);
      await refreshProfile();
    } catch {
      // handled silently
    } finally {
      setUploading(false);
    }
  };

  const src = avatarUrl(user);

  return (
    <div>
      <PageHeader title="Profile" />

      <PageContent>
        <ContentCard>
          <div className="profile-header-compact">
            <div className="profile-avatar" onClick={() => fileRef.current?.click()}>
              {src ? (
                <img src={src} alt="avatar" className="profile-avatar__img" />
              ) : (
                user.username.charAt(0).toUpperCase()
              )}
              <div className="profile-avatar__overlay">{uploading ? '...' : 'Edit'}</div>
              <input ref={fileRef} type="file" accept="image/jpeg,image/png" onChange={handleAvatarChange} style={{ display: 'none' }} />
            </div>
            <div>
              <span className="profile-header-compact__name">{user.username}</span>
              <p className="profile-header-compact__detail">{user.email}</p>
            </div>
          </div>

          <div style={{ display: 'grid', gap: '12px', marginTop: '16px' }}>
            <div className="pref-row">
              <span className="pref-row__label">Email Verified</span>
              <span style={{ color: user.email_verified ? 'var(--brand-success)' : 'var(--brand-warning)', fontWeight: '500' }}>
                {user.email_verified ? 'Yes' : 'No'}
              </span>
            </div>
            {user.pending_email && (
              <div className="pref-row">
                <span className="pref-row__label">Pending Email Change</span>
                <span style={{ color: 'var(--brand-warning)', fontWeight: '500' }}>{user.pending_email}</span>
              </div>
            )}
            <div className="pref-row">
              <span className="pref-row__label">Member Since</span>
              <span>{user.created_at ? new Date(user.created_at).toLocaleDateString() : '--'}</span>
            </div>
          </div>
        </ContentCard>

        <ContentCard>
          <div className="pref-row">
            <div>
              <div style={{ fontWeight: '500' }}>Dark Mode</div>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginTop: '2px' }}>
                {theme === 'dark' ? 'On' : 'Off'}
              </div>
            </div>
            <button
              onClick={toggle}
              className={`toggle toggle--compact ${theme === 'dark' ? 'toggle--on' : 'toggle--off'}`}
              aria-label="Toggle dark mode"
            >
              <span className={`toggle__thumb ${theme === 'dark' ? 'toggle__thumb--on' : 'toggle__thumb--off'}`} />
            </button>
          </div>
        </ContentCard>

        <ContentCard>
          <h3 style={{ margin: '0 0 12px' }}>Change Email</h3>
          <form onSubmit={handleChangeEmail} style={{ display: 'flex', gap: '8px' }}>
            <input
              type="email"
              placeholder="New email address"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              className="email-change__input email-change__input--full"
              style={{ flex: 1 }}
            />
            <button type="submit" disabled={submitting || !newEmail} className="btn btn--primary">
              {submitting ? 'Sending...' : 'Update'}
            </button>
          </form>
          {emailMsg && <p className="email-change__status email-change__status--success">{emailMsg}</p>}
          {emailErr && <p className="email-change__status email-change__status--error">{emailErr}</p>}
        </ContentCard>

        <button onClick={handleLogout} className="btn-logout">
          Log Out
        </button>
      </PageContent>
    </div>
  );
}

export default Profile;
