// ==============================================================================
// File:      frontend/src/api/preferences.js
// Purpose:   Preferences API functions for Town Scryer. Provides endpoints for
//            fetching and saving user default preferences (game type, art style,
//            gore level) so they persist across sessions.
// Callers:   pages/Session.jsx
// Callees:   api/client.js
// Modified:  2026-06-01
// ==============================================================================
import client from './client';

export const getPreferences = async () => {
  const { data } = await client.get('/api/preferences');
  return data;
};

export const savePreferences = async (prefs) => {
  const { data } = await client.post('/api/preferences', prefs);
  return data;
};
