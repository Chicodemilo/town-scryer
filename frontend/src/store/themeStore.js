// ==============================================================================
// File:      frontend/src/store/themeStore.js
// Purpose:   Zustand store for theme state. Manages light/dark mode toggle,
//            persists preference to localStorage, and respects the user's
//            OS-level prefers-color-scheme on first visit.
// Callers:   NavBar.jsx, Profile.jsx
// Callees:   zustand
// Modified:  2026-04-22
// ==============================================================================
import { create } from 'zustand';

function getInitialTheme() {
  const stored = localStorage.getItem('theme');
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
}

const initialTheme = getInitialTheme();
applyTheme(initialTheme);

const useThemeStore = create((set) => ({
  theme: initialTheme,
  toggle: () => set((state) => {
    const next = state.theme === 'light' ? 'dark' : 'light';
    applyTheme(next);
    return { theme: next };
  }),
}));

export default useThemeStore;
