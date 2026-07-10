// ==============================================================================
// File:      frontend/src/__tests__/tables.test.js
// Purpose:   Vitest tests verifying Tables and Characters API function exports
//            exist and are callable.
// Modified:  2026-06-01
// ==============================================================================
import { describe, it, expect } from 'vitest';
import {
  createTable,
  getTables,
  getTable,
  joinTable,
  regenerateCode,
  deleteTable,
  getTableCharacters,
} from '../api/tables';
import {
  createCharacter,
  updateCharacter,
  deleteCharacter,
  uploadPortrait,
} from '../api/characters';

describe('Tables API functions', () => {
  it('exports createTable as a function', () => {
    expect(typeof createTable).toBe('function');
  });

  it('exports getTables as a function', () => {
    expect(typeof getTables).toBe('function');
  });

  it('exports getTable as a function', () => {
    expect(typeof getTable).toBe('function');
  });

  it('exports joinTable as a function', () => {
    expect(typeof joinTable).toBe('function');
  });

  it('exports regenerateCode as a function', () => {
    expect(typeof regenerateCode).toBe('function');
  });

  it('exports deleteTable as a function', () => {
    expect(typeof deleteTable).toBe('function');
  });

  it('exports getTableCharacters as a function', () => {
    expect(typeof getTableCharacters).toBe('function');
  });
});

describe('Characters API functions', () => {
  it('exports createCharacter as a function', () => {
    expect(typeof createCharacter).toBe('function');
  });

  it('exports updateCharacter as a function', () => {
    expect(typeof updateCharacter).toBe('function');
  });

  it('exports deleteCharacter as a function', () => {
    expect(typeof deleteCharacter).toBe('function');
  });

  it('exports uploadPortrait as a function', () => {
    expect(typeof uploadPortrait).toBe('function');
  });
});
