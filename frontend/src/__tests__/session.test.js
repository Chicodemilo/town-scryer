// ==============================================================================
// File:      frontend/src/__tests__/session.test.js
// Purpose:   Quick vitest tests for session API functions — verifies exports
//            exist and are callable.
// Modified:  2026-06-01
// ==============================================================================
import { describe, it, expect } from 'vitest';
import {
  startSession,
  pauseSession,
  resumeSession,
  endSession,
  sendHeartbeat,
  sendChunk,
  getCurrentSession,
  getLatestScene,
} from '../api/session';

describe('Session API functions', () => {
  it('exports startSession as a function', () => {
    expect(typeof startSession).toBe('function');
  });

  it('exports pauseSession as a function', () => {
    expect(typeof pauseSession).toBe('function');
  });

  it('exports resumeSession as a function', () => {
    expect(typeof resumeSession).toBe('function');
  });

  it('exports endSession as a function', () => {
    expect(typeof endSession).toBe('function');
  });

  it('exports sendHeartbeat as a function', () => {
    expect(typeof sendHeartbeat).toBe('function');
  });

  it('exports sendChunk as a function', () => {
    expect(typeof sendChunk).toBe('function');
  });

  it('exports getCurrentSession as a function', () => {
    expect(typeof getCurrentSession).toBe('function');
  });

  it('exports getLatestScene as a function', () => {
    expect(typeof getLatestScene).toBe('function');
  });
});
