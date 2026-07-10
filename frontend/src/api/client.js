// ==============================================================================
// File:      frontend/src/api/client.js
// Purpose:   Axios HTTP client instance with JWT interceptor. Attaches
//            Bearer token from localStorage to all outgoing requests.
//            Handles 401 responses globally by clearing session and
//            redirecting to login.
// Callers:   api/auth.js, api/groups.js, api/items.js, api/alerts.js,
//            api/conversations.js, api/admin.js, api/activity.js,
//            api/polls.js, api/feedback.js, VerifyEmail.jsx,
//            GroupCreate.jsx
// Callees:   axios
// Modified:  2026-04-22
// ==============================================================================
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5151';

const client = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' }
});

// Attach JWT token to every request
client.interceptors.request.use((config) => {
  const isAdminRequest = config.url?.includes('/api/admin/');
  const token = isAdminRequest
    ? (localStorage.getItem('admin_token') || localStorage.getItem('token'))
    : localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses globally
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const isAdminRequest = error.config?.url?.includes('/api/admin/');
      if (isAdminRequest) {
        localStorage.removeItem('admin_token');
        localStorage.removeItem('admin_user');
      } else {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default client;
