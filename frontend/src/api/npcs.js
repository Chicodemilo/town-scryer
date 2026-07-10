// ==============================================================================
// File:      frontend/src/api/npcs.js
// Purpose:   NPC API. CRUD for recurring non-player characters per table.
// Callers:   TableDetail.jsx
// Callees:   api/client.js
// Modified:  2026-06-05
// ==============================================================================
import client from './client';

export const getNpcs = async (tableId) => {
  const { data } = await client.get(`/api/tables/${tableId}/npcs`);
  return data;
};

export const createNpc = async (tableId, npc) => {
  const { data } = await client.post(`/api/tables/${tableId}/npcs`, npc);
  return data;
};

export const updateNpc = async (tableId, npcId, npc) => {
  const { data } = await client.put(`/api/tables/${tableId}/npcs/${npcId}`, npc);
  return data;
};

export const deleteNpc = async (tableId, npcId) => {
  const { data } = await client.delete(`/api/tables/${tableId}/npcs/${npcId}`);
  return data;
};
