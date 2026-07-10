// ==============================================================================
// File:      frontend/src/api/history.js
// Purpose:   Session history API functions. Provides paginated access to past
//            sessions and their associated scenes.
// Callers:   History.jsx
// Callees:   api/client.js
// Modified:  2026-06-01
// ==============================================================================
import client from './client';

export const getSessions = async (page = 1, perPage = 20) => {
  const { data } = await client.get('/api/sessions', {
    params: { page, per_page: perPage },
  });
  return data;
};

export const getSessionScenes = async (sessionId, page = 1, perPage = 50) => {
  const { data } = await client.get(`/api/sessions/${sessionId}/scenes`, {
    params: { page, per_page: perPage },
  });
  return data;
};

export const deleteSession = async (sessionId) => {
  const { data } = await client.delete(`/api/sessions/${sessionId}`);
  return data;
};
