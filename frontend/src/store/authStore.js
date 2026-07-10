// ==============================================================================
// File:      frontend/src/store/authStore.js
// Purpose:   Zustand store for authentication state. Manages user login,
//            registration, logout, profile refresh, and JWT token
//            persistence in localStorage.
// Callers:   App.jsx, AppHeader.jsx, Home.jsx, Login.jsx, Register.jsx,
//            CheckEmail.jsx, VerifyEmail.jsx, Profile.jsx, Terms.jsx,
//            Dashboard.jsx
// Callees:   zustand, api/auth.js
// Modified:  2026-06-01
// ==============================================================================
import { create } from 'zustand';
import { login as apiLogin, register as apiRegister, getProfile } from '../api/auth';

const useAuthStore = create((set, get) => ({
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  token: localStorage.getItem('token') || null,
  loading: false,
  error: null,

  login: async (username, password) => {
    set({ loading: true, error: null });
    try {
      const data = await apiLogin(username, password);
      localStorage.setItem('token', data.token);
      localStorage.setItem('user', JSON.stringify(data.user));
      set({ user: data.user, token: data.token, loading: false });
      return data;
    } catch (error) {
      set({ error: error.response?.data?.error || 'Login failed', loading: false });
      throw error;
    }
  },

  register: async (username, email, password) => {
    set({ loading: true, error: null });
    try {
      const data = await apiRegister(username, email, password);
      localStorage.setItem('token', data.token);
      localStorage.setItem('user', JSON.stringify(data.user));
      set({ user: data.user, token: data.token, loading: false });
      return data;
    } catch (error) {
      set({ error: error.response?.data?.error || 'Registration failed', loading: false });
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    set({ user: null, token: null });
  },

  refreshProfile: async () => {
    try {
      const data = await getProfile();
      localStorage.setItem('user', JSON.stringify(data.user));
      set({ user: data.user });
    } catch {
      // Token may be expired
      get().logout();
    }
  },

  isAuthenticated: () => !!get().token,
  clearError: () => set({ error: null }),
}));

export default useAuthStore;
