// ==============================================================================
// File:      frontend/src/__tests__/history.test.js
// Purpose:   Vitest tests for the history and preferences API modules.
//            Verifies that all exported functions exist and are callable.
// Modified:  2026-06-01
// ==============================================================================
import { describe, it, expect } from 'vitest';
import { getSessions, getSessionScenes } from '../api/history';
import { getPreferences, savePreferences } from '../api/preferences';

describe('History API functions', () => {
  it('exports getSessions as a function', () => {
    expect(typeof getSessions).toBe('function');
  });

  it('exports getSessionScenes as a function', () => {
    expect(typeof getSessionScenes).toBe('function');
  });
});

describe('Preferences API functions', () => {
  it('exports getPreferences as a function', () => {
    expect(typeof getPreferences).toBe('function');
  });

  it('exports savePreferences as a function', () => {
    expect(typeof savePreferences).toBe('function');
  });
});
