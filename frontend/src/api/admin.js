// ==============================================================================
// File:      frontend/src/api/admin.js
// Purpose:   Admin panel API functions. Provides admin login, dashboard
//            stats, user/group management, health checks, test results,
//            terms editing, invite sending, and permission management.
// Callers:   adminStore.js, AdminUsers.jsx, AdminGroups.jsx,
//            AdminHealth.jsx, AdminTerms.jsx
// Callees:   api/client.js
// Modified:  2026-04-22
// ==============================================================================
import client from './client';

export const adminLogin = async (username, password) => {
  const { data } = await client.post('/api/admin/login', { username, password });
  return data;
};

export const getStats = async () => {
  const { data } = await client.get('/api/admin/stats');
  return data.stats;
};

export const getUsers = async ({ search = '', page = 1, perPage = 20 } = {}) => {
  const { data } = await client.get('/api/admin/users', {
    params: { search, page, per_page: perPage }
  });
  return data;
};

export const getUser = async (userId) => {
  const { data } = await client.get(`/api/admin/users/${userId}`);
  return data;
};

export const updateUser = async (userId, updates) => {
  const { data } = await client.put(`/api/admin/users/${userId}`, updates);
  return data;
};

export const deleteUser = async (userId) => {
  const { data } = await client.delete(`/api/admin/users/${userId}`);
  return data;
};

export const getAdminGroups = async ({ search = '', type = '', page = 1, perPage = 20 } = {}) => {
  const { data } = await client.get('/api/admin/groups', {
    params: { search, type, page, per_page: perPage }
  });
  return data;
};

export const getAdminGroup = async (groupId) => {
  const { data } = await client.get(`/api/admin/groups/${groupId}`);
  return data;
};

export const deleteAdminGroup = async (groupId) => {
  const { data } = await client.delete(`/api/admin/groups/${groupId}`);
  return data;
};

export const getAdminHealth = async () => {
  const { data } = await client.get('/api/admin/health');
  return data;
};

export const getAdminTestResults = async () => {
  const { data } = await client.get('/api/admin/test-results');
  return data;
};

// Terms & Conditions
export const getAdminTerms = async () => {
  const { data } = await client.get('/api/admin/terms');
  return data;
};

export const updateAdminTerms = async (content) => {
  const { data } = await client.put('/api/admin/terms', { content });
  return data;
};

export const resetAllTerms = async () => {
  const { data } = await client.post('/api/admin/terms/reset');
  return data;
};

// Invites
export const inviteUser = async (email) => {
  const { data } = await client.post('/api/admin/invite', { email });
  return data;
};

// Admin users
export const getAdminUsers = async () => {
  const { data } = await client.get('/api/admin/admin-users');
  return data;
};

// Permissions
export const updateUserPermissions = async (userId, permissions) => {
  const { data } = await client.put(`/api/admin/users/${userId}/permissions`, { permissions });
  return data;
};
