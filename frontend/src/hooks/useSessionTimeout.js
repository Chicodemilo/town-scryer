/**
 * File: useSessionTimeout.js
 * Purpose: Idle session timeout hook. Logs the user out after a period of
 *          inactivity (mouse/key/scroll/touch).
 *
 *          Suppressed entirely on /session and /display — those routes
 *          ARE the active session. Display intentionally sits with no
 *          input for hours; Session can sit while the DM listens without
 *          clicking. Logging either out mid-campaign would suck.
 * Callers: AppShell (App.jsx)
 * Callees: authStore.js
 * Modified: 2026-06-06
 */
import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import useAuthStore from '../store/authStore';

const TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes
const CHECK_INTERVAL_MS = 60 * 1000; // check every minute
const ACTIVITY_EVENTS = ['mousedown', 'keypress', 'scroll', 'touchstart'];

const SESSION_PATHS = ['/session', '/display'];

export default function useSessionTimeout() {
  const token = useAuthStore(state => state.token);
  const logout = useAuthStore(state => state.logout);
  const location = useLocation();
  const lastActivity = useRef(Date.now());

  const onSessionPath = SESSION_PATHS.some(
    p => location.pathname === p || location.pathname.startsWith(p + '/')
  );

  useEffect(() => {
    if (!token) return;
    if (onSessionPath) return; // No idle-logout while running / displaying.

    const resetTimer = () => {
      lastActivity.current = Date.now();
    };

    const checkTimeout = () => {
      if (Date.now() - lastActivity.current > TIMEOUT_MS) {
        logout();
        window.location.href = '/login';
      }
    };

    const interval = setInterval(checkTimeout, CHECK_INTERVAL_MS);

    ACTIVITY_EVENTS.forEach(evt => {
      document.addEventListener(evt, resetTimer, true);
    });

    return () => {
      clearInterval(interval);
      ACTIVITY_EVENTS.forEach(evt => {
        document.removeEventListener(evt, resetTimer, true);
      });
    };
  }, [token, logout, onSessionPath]);
}
