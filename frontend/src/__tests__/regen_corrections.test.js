// ==============================================================================
// File:      frontend/src/__tests__/regen_corrections.test.js
// Purpose:   Vitest tests for regen and correction API functions — verifies
//            exports exist and are callable.
// Modified:  2026-06-01
// ==============================================================================
import { describe, it, expect } from 'vitest';
import {
  regenImage,
  getRegenInfo,
  addCorrection,
  getCorrections,
  deleteCorrection,
  clearCorrections,
} from '../api/session';

describe('Regen API functions', () => {
  it('exports regenImage as a function', () => {
    expect(typeof regenImage).toBe('function');
  });

  it('exports getRegenInfo as a function', () => {
    expect(typeof getRegenInfo).toBe('function');
  });
});

describe('Correction API functions', () => {
  it('exports addCorrection as a function', () => {
    expect(typeof addCorrection).toBe('function');
  });

  it('exports getCorrections as a function', () => {
    expect(typeof getCorrections).toBe('function');
  });

  it('exports deleteCorrection as a function', () => {
    expect(typeof deleteCorrection).toBe('function');
  });

  it('exports clearCorrections as a function', () => {
    expect(typeof clearCorrections).toBe('function');
  });
});
