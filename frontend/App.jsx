// ==============================================================================
// File:      frontend/App.jsx
// Purpose:   Root application component. Defines all client-side routes and
//            wraps the app in React Router. Renders AppHeader on authenticated
//            routes with contextual nav links.
// Callers:   main.jsx
// Callees:   React, react-router-dom, authStore.js, useSessionTimeout.js,
//            ErrorBoundary.jsx, AppHeader.jsx, Login.jsx, Register.jsx,
//            Dashboard.jsx, VerifyEmail.jsx, CheckEmail.jsx, Profile.jsx,
//            Terms.jsx, Home.jsx, AdminLayout.jsx, Display.jsx
// Modified:  2026-06-01
// ==============================================================================
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import useAuthStore from './src/store/authStore';
import useSessionTimeout from './src/hooks/useSessionTimeout';
import ErrorBoundary from './src/components/ErrorBoundary';
import AppHeader from './src/components/AppHeader';
import { ModalProvider } from './src/components/ModalProvider';
import Login from './src/pages/Login';
import Register from './src/pages/Register';
import Dashboard from './src/pages/Dashboard';
import VerifyEmail from './src/pages/VerifyEmail';
import CheckEmail from './src/pages/CheckEmail';
import Profile from './src/pages/Profile';
import Terms from './src/pages/Terms';
import Home from './src/pages/Home';
import AdminLayout from './src/pages/admin/AdminLayout';
import Display from './src/pages/Display';
import Session from './src/pages/Session';
import History from './src/pages/History';
import Tables from './src/pages/Tables';
import TableDetail from './src/pages/TableDetail';
import JoinTable from './src/pages/JoinTable';
import Help from './src/pages/Help';

const PUBLIC_PATHS = ['/', '/login', '/register', '/verify-email', '/check-email', '/display'];

function AppShell() {
  const location = useLocation();
  const token = useAuthStore(state => state.token);
  const isAuthenticated = !!token;
  useSessionTimeout();
  const isPublic = PUBLIC_PATHS.includes(location.pathname);
  const isAdmin = location.pathname.startsWith('/overview');
  const showHeader = !isPublic && !isAdmin;
  const showContentWrapper = !isPublic && !isAdmin;

  const navLinks = [
    { label: 'Dashboard', to: '/dashboard' },
    { label: 'Session', to: '/session' },
    { label: 'History', to: '/history' },
    { label: 'Tables', to: '/tables' },
    { label: 'Help', to: '/help' },
  ];

  const publicRoutes = (
    <Routes>
      <Route path="/" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Home />} />
      <Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/check-email" element={<CheckEmail />} />
      <Route path="/display" element={<Display />} />
    </Routes>
  );

  const authenticatedRoutes = (
    <Routes>
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/session" element={<Session />} />
      <Route path="/history" element={<History />} />
      <Route path="/tables" element={<Tables />} />
      <Route path="/tables/join" element={<JoinTable />} />
      <Route path="/tables/:id" element={<TableDetail />} />
      <Route path="/profile" element={<Profile />} />
      <Route path="/help" element={<Help />} />
      <Route path="/terms" element={<Terms />} />
      <Route path="/overview/*" element={<AdminLayout />} />
    </Routes>
  );

  if (isPublic) {
    return (
      <div id="app-root" className="app-root app-root--public">
        {publicRoutes}
      </div>
    );
  }

  // Guard: kick to login if not authenticated
  if (!isAuthenticated && !isAdmin) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div id="app-root" className="app-root app-root--authenticated">
      {showHeader && <AppHeader links={navLinks} />}
      {showContentWrapper ? (
        <div className="content-container">
          {authenticatedRoutes}
        </div>
      ) : (
        authenticatedRoutes
      )}
    </div>
  );
}

function App() {
  return (
    <Router>
      <ErrorBoundary>
        <ModalProvider>
          <AppShell />
        </ModalProvider>
      </ErrorBoundary>
    </Router>
  );
}

export default App;
