// ==============================================================================
// File:      frontend/src/store/adminStore.js
// Purpose:   Zustand store for admin panel state. Manages admin login,
//            logout, session initialization, and fetching dashboard stats,
//            users, and groups for the admin panel.
// Callers:   AdminLayout.jsx, AdminLogin.jsx, AdminDashboard.jsx,
//            AdminUsers.jsx, AdminGroups.jsx
// Callees:   zustand, api/admin.js
// Modified:  2026-04-22
// ==============================================================================
import { create } from 'zustand';
import { adminLogin, getStats, getUsers } from '../api/admin';

const useAdminStore = create((set, get) => ({
  isAuthenticated: !!localStorage.getItem('admin_token'),
  adminUser: JSON.parse(localStorage.getItem('admin_user') || 'null'),
  stats: null,
  users: [],
  loading: false,
  error: null,

  login: async (username, password) => {
    set({ loading: true, error: null });
    try {
      const data = await adminLogin(username, password);
      if (data.success) {
        localStorage.setItem('admin_token', data.token);
        localStorage.setItem('admin_user', JSON.stringify(data.user));
        set({ isAuthenticated: true, adminUser: data.user, loading: false });
      }
      return data;
    } catch (error) {
      set({ error: error.response?.data?.message || 'Login failed', loading: false });
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    set({ isAuthenticated: false, adminUser: null, stats: null });
  },

  fetchStats: async () => {
    set({ loading: true });
    try {
      const stats = await getStats();
      set({ stats, loading: false });
    } catch (error) {
      set({ error: 'Failed to load stats', loading: false });
    }
  },

  fetchUsers: async (params) => {
    set({ loading: true });
    try {
      const data = await getUsers(params);
      set({ users: data.users, loading: false });
      return data;
    } catch (error) {
      set({ error: 'Failed to load users', loading: false });
    }
  },

  initialize: () => {
    const token = localStorage.getItem('admin_token');
    const user = localStorage.getItem('admin_user');
    if (token && user) {
      set({ isAuthenticated: true, adminUser: JSON.parse(user) });
    }
  },

  clearError: () => set({ error: null }),
}));

export default useAdminStore;
