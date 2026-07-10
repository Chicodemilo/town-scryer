// ==============================================================================
// File:      frontend/src/api/session.js
// Purpose:   Session management API functions for Town Scryer. Provides
//            endpoints for starting, pausing, resuming, and ending DM
//            sessions, as well as sending audio transcript chunks and
//            retrieving scene data.
// Callers:   AudioCapture.jsx, Display.jsx, Dashboard.jsx
// Callees:   api/client.js
// Modified:  2026-06-01
// ==============================================================================
import client from './client';

export const startSession = async (options) => {
  const { data } = await client.post('/api/session/start', options);
  return data;
};

export const pauseSession = async (token) => {
  const { data } = await client.post('/api/session/pause', { session_token: token });
  return data;
};

export const resumeSession = async (token) => {
  const { data } = await client.post('/api/session/resume', { session_token: token });
  return data;
};

export const endSession = async (token) => {
  const { data } = await client.post('/api/session/end', { session_token: token });
  return data;
};

export const sendHeartbeat = async (token) => {
  const { data } = await client.post('/api/session/heartbeat', { session_token: token });
  return data;
};

export const sendChunk = async (token, transcript) => {
  const { data } = await client.post('/api/session/chunk', {
    session_token: token,
    transcript,
  });
  return data;
};

export const changeImage = async (token, guidance) => {
  const { data } = await client.post('/api/session/change-image', {
    session_token: token,
    guidance: guidance || '',
  });
  return data;
};

export const deleteScene = async (sceneId) => {
  const { data } = await client.delete(`/api/session/scenes/${sceneId}`);
  return data;
};

export const thumbsUpScene = async (sceneId) => {
  const { data } = await client.post(`/api/session/scenes/${sceneId}/thumbs-up`);
  return data;
};

export const sendAudioChunk = async (token, audioBlob) => {
  const formData = new FormData();
  formData.append('session_token', token);
  formData.append('audio', audioBlob, 'chunk.webm');
  const { data } = await client.post('/api/session/audio-chunk', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export const getCurrentSession = async () => {
  const { data } = await client.get('/api/session/current');
  return data;
};

export const getLatestScene = async () => {
  const { data } = await client.get('/api/session/latest-scene');
  return data;
};

export const regenImage = async (token, guidance) => {
  const { data } = await client.post('/api/session/regen', {
    session_token: token,
    ...(guidance ? { guidance } : {}),
  });
  return data;
};

export const getRegenInfo = async (token) => {
  const { data } = await client.get('/api/session/regen-info', {
    params: { session_token: token },
  });
  return data;
};

export const addCorrection = async (token, text) => {
  const { data } = await client.post('/api/session/correction', {
    session_token: token,
    text,
  });
  return data;
};

export const getCorrections = async (token) => {
  const { data } = await client.get('/api/session/corrections', {
    params: { session_token: token },
  });
  return data;
};

export const deleteCorrection = async (id) => {
  const { data } = await client.delete(`/api/session/correction/${id}`);
  return data;
};

export const clearCorrections = async (token) => {
  const { data } = await client.post('/api/session/corrections/clear', {
    session_token: token,
  });
  return data;
};
