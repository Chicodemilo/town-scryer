// ==============================================================================
// File:      frontend/src/services/validation.js
// Purpose:   Form validation rules shared between web and mobile. Provides
//            validators for email, password, username, and required fields,
//            plus a composite registration validator.
// Callers:   Register.jsx
// Callees:   (none — pure validation functions)
// Modified:  2026-04-22
// ==============================================================================
// Form validation rules — shared patterns between web and mobile

export const validateEmail = (email) => {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
};

export const validatePassword = (password) => {
  if (!password || password.length < 6) {
    return 'Password must be at least 6 characters';
  }
  return null;
};

export const validateUsername = (username) => {
  if (!username || username.length < 2) {
    return 'Username must be at least 2 characters';
  }
  if (!/^[a-zA-Z0-9_]+$/.test(username)) {
    return 'Username can only contain letters, numbers, and underscores';
  }
  return null;
};

export const validateRequired = (value, fieldName) => {
  if (!value || (typeof value === 'string' && !value.trim())) {
    return `${fieldName} is required`;
  }
  return null;
};

export const validateRegistration = ({ username, email, password }) => {
  const errors = {};
  const usernameErr = validateUsername(username);
  if (usernameErr) errors.username = usernameErr;
  if (!validateEmail(email)) errors.email = 'Please enter a valid email';
  const passwordErr = validatePassword(password);
  if (passwordErr) errors.password = passwordErr;
  return Object.keys(errors).length > 0 ? errors : null;
};
