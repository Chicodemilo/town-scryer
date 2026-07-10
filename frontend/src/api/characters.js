// ==============================================================================
// File:      frontend/src/api/characters.js
// Purpose:   Character management API functions for Town Scryer. Provides
//            endpoints for creating, updating, deleting characters and
//            uploading character portraits.
// Callers:   TableDetail.jsx, JoinTable.jsx
// Callees:   api/client.js
// Modified:  2026-06-01
// ==============================================================================
import client from './client';

export const getCharacters = async (tableId) => {
  const { data } = await client.get(`/api/tables/${tableId}/characters`);
  return data;
};

export const createCharacter = async (tableId, characterData) => {
  const { data } = await client.post(`/api/tables/${tableId}/characters`, characterData);
  return data;
};

export const updateCharacter = async (tableId, charId, characterData) => {
  const { data } = await client.put(`/api/tables/${tableId}/characters/${charId}`, characterData);
  return data;
};

export const deleteCharacter = async (tableId, charId) => {
  const { data } = await client.delete(`/api/tables/${tableId}/characters/${charId}`);
  return data;
};

export const uploadPortrait = async (tableId, charId, file) => {
  const formData = new FormData();
  formData.append('portrait', file);
  const { data } = await client.post(
    `/api/tables/${tableId}/characters/${charId}/portrait`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );
  return data;
};

export const claimCharacter = async (tableId, charId) => {
  const { data } = await client.post(`/api/tables/${tableId}/characters/${charId}/claim`);
  return data;
};

export const getMyCharacters = async () => {
  const { data } = await client.get('/api/tables/characters/mine');
  return data;
};

export const unclaimCharacter = async (tableId, charId) => {
  const { data } = await client.post(`/api/tables/${tableId}/characters/${charId}/unclaim`);
  return data;
};
