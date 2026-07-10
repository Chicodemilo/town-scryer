// ==============================================================================
// File:      frontend/src/api/auth.js
// Purpose:   Authentication and user account API functions. Provides login,
//            register, email verification, profile retrieval, avatar upload,
//            terms acceptance, and invite completion endpoints.
// Callers:   authStore.js, CheckEmail.jsx, VerifyEmail.jsx, Terms.jsx,
//            Profile.jsx, Dashboard.jsx
// Callees:   api/client.js
// Modified:  2026-04-22
// ==============================================================================
import client from './client';

export const login = async (username, password) => {
  const { data } = await client.post('/api/auth/login', { username, password });
  return data;
};

export const register = async (username, email, password) => {
  const { data } = await client.post('/api/auth/register', { username, email, password });
  return data;
};

export const verifyToken = async () => {
  const { data } = await client.get('/api/auth/verify');
  return data;
};

export const getProfile = async () => {
  const { data } = await client.get('/api/auth/profile');
  return data;
};

export const verifyEmail = async (token) => {
  const { data } = await client.get(`/api/auth/verify-email?token=${token}`);
  return data;
};

export const resendVerification = async () => {
  const { data } = await client.post('/api/auth/resend-verification');
  return data;
};

export const setActiveGroup = async (groupId) => {
  const { data } = await client.put('/api/auth/active-group', { group_id: groupId });
  return data;
};

export const acceptTerms = async () => {
  const { data } = await client.put('/api/auth/accept-terms');
  return data;
};

export const getTerms = async () => {
  const { data } = await client.get('/api/auth/terms');
  return data;
};

export const changeEmail = async (email) => {
  const { data } = await client.put('/api/auth/change-email', { email });
  return data;
};

export const completeInvite = async (token, username, password) => {
  const { data } = await client.post('/api/auth/complete-invite', { token, username, password });
  return data;
};

export const uploadAvatar = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await client.post('/api/uploads/avatar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};
