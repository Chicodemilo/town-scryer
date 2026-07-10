// ==============================================================================
// File:      frontend/src/services/auth.js
// Purpose:   Token and session management utilities. Provides helpers for
//            getting, setting, and removing JWT tokens and user data from
//            localStorage, plus session-clearing logic.
// Callers:   (none currently — available as a shared utility)
// Callees:   (none — uses browser localStorage API directly)
// Modified:  2026-04-22
// ==============================================================================
// Token and session management for web frontend

export const getToken = () => localStorage.getItem('token');

export const setToken = (token) => localStorage.setItem('token', token);

export const removeToken = () => localStorage.removeItem('token');

export const isAuthenticated = () => !!getToken();

export const getStoredUser = () => {
  const user = localStorage.getItem('user');
  return user ? JSON.parse(user) : null;
};

export const setStoredUser = (user) => {
  localStorage.setItem('user', JSON.stringify(user));
};

export const clearSession = () => {
  removeToken();
  localStorage.removeItem('user');
};
