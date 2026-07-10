import { describe, it, expect } from 'vitest';
import {
  validateEmail,
  validatePassword,
  validateUsername,
  validateRequired,
  validateRegistration,
} from '../services/validation';

describe('validateEmail', () => {
  it('accepts valid emails', () => {
    expect(validateEmail('user@example.com')).toBe(true);
    expect(validateEmail('name+tag@domain.co')).toBe(true);
  });

  it('rejects invalid emails', () => {
    expect(validateEmail('')).toBe(false);
    expect(validateEmail('notanemail')).toBe(false);
    expect(validateEmail('missing@')).toBe(false);
  });
});

describe('validatePassword', () => {
  it('returns null for valid passwords', () => {
    expect(validatePassword('123456')).toBeNull();
    expect(validatePassword('strongpassword')).toBeNull();
  });

  it('returns error for short passwords', () => {
    expect(validatePassword('12345')).toBeTruthy();
    expect(validatePassword('')).toBeTruthy();
    expect(validatePassword(null)).toBeTruthy();
  });
});

describe('validateUsername', () => {
  it('returns null for valid usernames', () => {
    expect(validateUsername('user1')).toBeNull();
    expect(validateUsername('test_user')).toBeNull();
  });

  it('returns error for invalid usernames', () => {
    expect(validateUsername('a')).toBeTruthy();
    expect(validateUsername('bad user!')).toBeTruthy();
  });
});

describe('validateRequired', () => {
  it('returns null for non-empty values', () => {
    expect(validateRequired('value', 'Field')).toBeNull();
  });

  it('returns error for empty values', () => {
    expect(validateRequired('', 'Name')).toBeTruthy();
    expect(validateRequired('   ', 'Name')).toBeTruthy();
    expect(validateRequired(null, 'Name')).toBeTruthy();
  });
});

describe('validateRegistration', () => {
  it('returns null for valid registration', () => {
    expect(validateRegistration({
      username: 'validuser',
      email: 'test@example.com',
      password: 'password123',
    })).toBeNull();
  });

  it('returns errors for invalid registration', () => {
    const errors = validateRegistration({
      username: '',
      email: 'bad',
      password: '12',
    });
    expect(errors).toBeTruthy();
    expect(errors.username).toBeTruthy();
    expect(errors.email).toBeTruthy();
    expect(errors.password).toBeTruthy();
  });
});
