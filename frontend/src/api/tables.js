// ==============================================================================
// File:      frontend/src/api/tables.js
// Purpose:   Tables API functions. Provides endpoints for creating, listing,
//            joining, and managing DM tables, as well as fetching table
//            characters.
// Callers:   Tables.jsx, TableDetail.jsx, Session.jsx
// Callees:   api/client.js
// Modified:  2026-06-01
// ==============================================================================
import client from './client';

export const createTable = async (name) => {
  const { data } = await client.post('/api/tables', { name });
  return data;
};

export const getTables = async () => {
  const { data } = await client.get('/api/tables');
  return data;
};

export const getTable = async (id) => {
  const { data } = await client.get(`/api/tables/${id}`);
  return data;
};

export const joinTable = async (code) => {
  const { data } = await client.post('/api/tables/join', { invite_code: code });
  return data;
};

export const regenerateCode = async (id) => {
  const { data } = await client.post(`/api/tables/${id}/regenerate-code`);
  return data;
};

export const updateTable = async (id, fields) => {
  const { data } = await client.put(`/api/tables/${id}`, fields);
  return data;
};

export const deleteTable = async (id) => {
  const { data } = await client.delete(`/api/tables/${id}`);
  return data;
};

export const getTableCharacters = async (tableId) => {
  const { data } = await client.get(`/api/tables/${tableId}/characters`);
  return data;
};
