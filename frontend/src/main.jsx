// ==============================================================================
// File:      frontend/src/main.jsx
// Purpose:   Application entry point. Mounts the root React component into
//            the DOM, sets the document title from environment variables,
//            and wraps the app in React.StrictMode.
// Callers:   index.html (Vite entry)
// Callees:   React, ReactDOM, App.jsx
// Modified:  2026-04-22
// ==============================================================================
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from '../App.jsx'
import './main.css';
import './styles/common.css';
import './styles/layout.css';
import './styles/auth.css';
import './styles/profile.css';
import './styles/dashboard.css';
import './styles/landing.css';
import './styles/display.css';
import './styles/session.css';
import './styles/history.css';
import './styles/tables.css';
import './styles/characters.css';

const appName = import.meta.env.VITE_APP_NAME || 'My App';
document.title = appName;

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
