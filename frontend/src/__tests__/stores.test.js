import { describe, it, expect, beforeEach } from 'vitest';
import { act } from '@testing-library/react';

// Test Zustand stores in isolation (no API calls)
describe('authStore', () => {
  let useAuthStore;

  beforeEach(async () => {
    const mod = await import('../store/authStore');
    useAuthStore = mod.default;
    act(() => {
      useAuthStore.setState({
        user: null,
        token: null,
        loading: false,
        error: null,
      });
    });
  });

  it('starts with no user', () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.token).toBeNull();
  });

  it('clearError clears the error', () => {
    act(() => {
      useAuthStore.setState({ error: 'Some error' });
    });
    expect(useAuthStore.getState().error).toBe('Some error');

    act(() => {
      useAuthStore.getState().clearError();
    });
    expect(useAuthStore.getState().error).toBeNull();
  });
});
