// ==============================================================================
// File:      frontend/src/security/examples.jsx
// Purpose:   Comprehensive usage examples for the frontend security package.
//            Demonstrates login forms, registration, protected routes, admin
//            panels, input validation, secure storage, session timeouts, and
//            security monitoring in a sample React application.
// Callers:   (none — reference/demo file)
// Callees:   React, react-router-dom, security/index.js
// Modified:  2026-04-22
// ==============================================================================
/**
 * Frontend Security Usage Examples
 * 
 * This file contains comprehensive examples of how to use all the frontend
 * security components in your React application.
 */

import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';

// Import all security components
import {
    // Authentication
    AuthProvider, useAuth, ProtectedRoute, AdminRoute, useSessionTimeout,
    
    // Input Validation
    sanitizeInput, validateFormData, useInputValidation, isValidEmail,
    validatePassword, escapeHtml, clientRateLimiter,
    
    // Security Utils
    secureStorage, securityMonitor, SecureRandom, checkSecurityHeaders,
    
    // Configuration
    SECURITY_CONFIG, VALIDATION_SCHEMAS, SecurityHelpers
} from './index';

// =============================================================================
// AUTHENTICATION EXAMPLES
// =============================================================================

/**
 * Login Component with Security Features
 */
const LoginForm = () => {
    const { login, loading } = useAuth();
    const [formData, setFormData] = useState({ email: '', password: '' });
    const [errors, setErrors] = useState({});
    const [loginAttempts, setLoginAttempts] = useState(0);

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        // Rate limiting check
        const rateLimitKey = `login_${formData.email}`;
        if (!clientRateLimiter.isAllowed(rateLimitKey, 5, 300000)) { // 5 attempts per 5 minutes
            setErrors({ general: 'Too many login attempts. Please try again later.' });
            return;
        }
        
        // Validate form data
        const validation = validateFormData(formData, VALIDATION_SCHEMAS.LOGIN);
        
        if (!validation.isValid) {
            setErrors(validation.errors);
            return;
        }
        
        // Attempt login
        const result = await login(
            validation.sanitizedData.email,
            validation.sanitizedData.password
        );
        
        if (!result.success) {
            setLoginAttempts(prev => prev + 1);
            setErrors({ general: result.error });
            
            // Log security event
            securityMonitor.logEvent('LOGIN_FAILED', {
                email: formData.email,
                attempt: loginAttempts + 1
            });
        }
    };

    const handleInputChange = (field, value) => {
        // Sanitize input
        const sanitized = sanitizeInput(value, {
            maxLength: field === 'email' ? 254 : 128,
            trimWhitespace: true
        });
        
        setFormData(prev => ({ ...prev, [field]: sanitized }));
        
        // Clear field-specific errors
        if (errors[field]) {
            setErrors(prev => ({ ...prev, [field]: null }));
        }
    };

    return (
        <form onSubmit={handleSubmit} className="login-form">
            <h2>Secure Login</h2>
            
            {errors.general && (
                <div className="error-message">{errors.general}</div>
            )}
            
            <div className="form-group">
                <label htmlFor="email">Email:</label>
                <input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => handleInputChange('email', e.target.value)}
                    required
                />
                {errors.email && (
                    <div className="field-error">{errors.email.join(', ')}</div>
                )}
            </div>
            
            <div className="form-group">
                <label htmlFor="password">Password:</label>
                <input
                    id="password"
                    type="password"
                    value={formData.password}
                    onChange={(e) => handleInputChange('password', e.target.value)}
                    required
                />
                {errors.password && (
                    <div className="field-error">{errors.password.join(', ')}</div>
                )}
            </div>
            
            <button type="submit" disabled={loading}>
                {loading ? 'Logging in...' : 'Login'}
            </button>
            
            <div className="security-info">
                <small>
                    Login attempts: {loginAttempts}/5
                    <br />
                    Connection: {SecurityHelpers.isSecureContext() ? 'Secure (HTTPS)' : 'Insecure (HTTP)'}
                </small>
            </div>
        </form>
    );
};

/**
 * Registration Form with Password Validation
 */
const RegistrationForm = () => {
    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: '',
        confirmPassword: ''
    });
    const [errors, setErrors] = useState({});
    const [passwordStrength, setPasswordStrength] = useState(null);

    const handlePasswordChange = (password) => {
        setFormData(prev => ({ ...prev, password }));
        
        // Validate password strength
        const strength = validatePassword(password);
        setPasswordStrength(strength);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        // Validate entire form
        const validation = validateFormData(formData, VALIDATION_SCHEMAS.REGISTER);
        
        if (!validation.isValid) {
            setErrors(validation.errors);
            return;
        }
        
        // Additional password confirmation check
        if (formData.password !== formData.confirmPassword) {
            setErrors({ confirmPassword: ['Passwords do not match'] });
            return;
        }
        
        // Here you would call your registration API
        console.log('Registration data:', validation.sanitizedData);
    };

    return (
        <form onSubmit={handleSubmit} className="registration-form">
            <h2>Secure Registration</h2>
            
            <div className="form-group">
                <label htmlFor="username">Username:</label>
                <input
                    id="username"
                    type="text"
                    value={formData.username}
                    onChange={(e) => setFormData(prev => ({ 
                        ...prev, 
                        username: sanitizeInput(e.target.value, { maxLength: 50 })
                    }))}
                    required
                />
                {errors.username && (
                    <div className="field-error">{errors.username.join(', ')}</div>
                )}
            </div>
            
            <div className="form-group">
                <label htmlFor="email">Email:</label>
                <input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData(prev => ({ 
                        ...prev, 
                        email: sanitizeInput(e.target.value, { maxLength: 254 })
                    }))}
                    required
                />
                {errors.email && (
                    <div className="field-error">{errors.email.join(', ')}</div>
                )}
            </div>
            
            <div className="form-group">
                <label htmlFor="password">Password:</label>
                <input
                    id="password"
                    type="password"
                    value={formData.password}
                    onChange={(e) => handlePasswordChange(e.target.value)}
                    required
                />
                {passwordStrength && (
                    <div className={`password-strength strength-${passwordStrength.score}`}>
                        Strength: {passwordStrength.score}/5
                        {passwordStrength.feedback.length > 0 && (
                            <ul>
                                {passwordStrength.feedback.map((feedback, index) => (
                                    <li key={index}>{feedback}</li>
                                ))}
                            </ul>
                        )}
                    </div>
                )}
                {errors.password && (
                    <div className="field-error">{errors.password.join(', ')}</div>
                )}
            </div>
            
            <div className="form-group">
                <label htmlFor="confirmPassword">Confirm Password:</label>
                <input
                    id="confirmPassword"
                    type="password"
                    value={formData.confirmPassword}
                    onChange={(e) => setFormData(prev => ({ 
                        ...prev, 
                        confirmPassword: e.target.value
                    }))}
                    required
                />
                {errors.confirmPassword && (
                    <div className="field-error">{errors.confirmPassword.join(', ')}</div>
                )}
            </div>
            
            <button type="submit">Register</button>
        </form>
    );
};

/**
 * Protected Dashboard Component
 */
const Dashboard = () => {
    const { user, logout } = useAuth();
    const [securityReport, setSecurityReport] = useState(null);

    useEffect(() => {
        // Get security report
        const report = securityMonitor.getSecurityReport();
        setSecurityReport(report);
        
        // Check security headers
        checkSecurityHeaders().then(headers => {
            console.log('Security Headers Report:', headers);
        });
    }, []);

    return (
        <div className="dashboard">
            <h2>Secure Dashboard</h2>
            
            <div className="user-info">
                <h3>User Information</h3>
                <p>Email: {escapeHtml(user?.email || 'N/A')}</p>
                <p>Username: {escapeHtml(user?.username || 'N/A')}</p>
                <p>Admin: {user?.is_admin ? 'Yes' : 'No'}</p>
            </div>
            
            {securityReport && (
                <div className="security-report">
                    <h3>Security Report (Last 24 Hours)</h3>
                    <p>Total Events: {securityReport.totalEvents}</p>
                    <p>Suspicious Events: {securityReport.suspiciousEvents.length}</p>
                    
                    <h4>Event Types:</h4>
                    <ul>
                        {Object.entries(securityReport.eventTypes).map(([type, count]) => (
                            <li key={type}>{type}: {count}</li>
                        ))}
                    </ul>
                </div>
            )}
            
            <button onClick={logout}>Secure Logout</button>
        </div>
    );
};

/**
 * Admin Panel Component
 */
const AdminPanel = () => {
    const { user } = useAuth();
    const [users, setUsers] = useState([]);
    const [securityEvents, setSecurityEvents] = useState([]);

    useEffect(() => {
        // Load admin data
        loadUsers();
        loadSecurityEvents();
    }, []);

    const loadUsers = async () => {
        // Simulated API call with security headers
        try {
            const response = await fetch('/api/admin/users', {
                headers: SecurityHelpers.getSecureHeaders()
            });
            
            if (response.ok) {
                const data = await response.json();
                setUsers(data.users || []);
            }
        } catch (error) {
            console.error('Failed to load users:', error);
        }
    };

    const loadSecurityEvents = () => {
        const events = securityMonitor.events.slice(-10); // Last 10 events
        setSecurityEvents(events);
    };

    return (
        <div className="admin-panel">
            <h2>Admin Panel</h2>
            <p>Welcome, {escapeHtml(user?.username || 'Admin')}</p>
            
            <div className="admin-section">
                <h3>User Management</h3>
                <div className="users-list">
                    {users.map(user => (
                        <div key={user.id} className="user-item">
                            {escapeHtml(user.email)}
                        </div>
                    ))}
                </div>
            </div>
            
            <div className="admin-section">
                <h3>Recent Security Events</h3>
                <div className="security-events">
                    {securityEvents.map((event, index) => (
                        <div key={index} className="security-event">
                            <strong>{event.type}</strong>
                            <span>{new Date(event.timestamp).toLocaleString()}</span>
                            <pre>{JSON.stringify(event.details, null, 2)}</pre>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

// =============================================================================
// INPUT VALIDATION EXAMPLES
// =============================================================================

/**
 * Contact Form with Comprehensive Validation
 */
const ContactForm = () => {
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        subject: '',
        message: ''
    });
    const [errors, setErrors] = useState({});
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Use custom validation hook for email
    const emailValidation = useInputValidation('', {
        required: true,
        type: 'email',
        maxLength: 254
    });

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsSubmitting(true);
        
        // Rate limiting
        if (!clientRateLimiter.isAllowed('contact_form', 3, 600000)) { // 3 per 10 minutes
            setErrors({ general: 'Too many submissions. Please wait before trying again.' });
            setIsSubmitting(false);
            return;
        }
        
        // Validate form
        const validation = validateFormData(formData, VALIDATION_SCHEMAS.CONTACT);
        
        if (!validation.isValid) {
            setErrors(validation.errors);
            setIsSubmitting(false);
            return;
        }
        
        try {
            // Submit form (simulated)
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Log successful submission
            securityMonitor.logEvent('CONTACT_FORM_SUBMITTED', {
                name: validation.sanitizedData.name,
                email: validation.sanitizedData.email
            });
            
            alert('Message sent successfully!');
            
            // Reset form
            setFormData({ name: '', email: '', subject: '', message: '' });
            setErrors({});
            
        } catch (error) {
            setErrors({ general: 'Failed to send message. Please try again.' });
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleInputChange = (field, value) => {
        const sanitized = sanitizeInput(value, {
            maxLength: field === 'message' ? 2000 : 200,
            allowHtml: false,
            trimWhitespace: field !== 'message'
        });
        
        setFormData(prev => ({ ...prev, [field]: sanitized }));
        
        // Clear errors for this field
        if (errors[field]) {
            setErrors(prev => ({ ...prev, [field]: null }));
        }
    };

    return (
        <form onSubmit={handleSubmit} className="contact-form">
            <h2>Secure Contact Form</h2>
            
            {errors.general && (
                <div className="error-message">{errors.general}</div>
            )}
            
            <div className="form-group">
                <label htmlFor="name">Name:</label>
                <input
                    id="name"
                    type="text"
                    value={formData.name}
                    onChange={(e) => handleInputChange('name', e.target.value)}
                    required
                />
                {errors.name && (
                    <div className="field-error">{errors.name.join(', ')}</div>
                )}
            </div>
            
            <div className="form-group">
                <label htmlFor="email">Email:</label>
                <input
                    id="email"
                    type="email"
                    value={emailValidation.value}
                    onChange={(e) => {
                        emailValidation.handleChange(e.target.value);
                        setFormData(prev => ({ ...prev, email: e.target.value }));
                    }}
                    required
                />
                {!emailValidation.isValid && emailValidation.errors.length > 0 && (
                    <div className="field-error">{emailValidation.errors.join(', ')}</div>
                )}
            </div>
            
            <div className="form-group">
                <label htmlFor="subject">Subject:</label>
                <input
                    id="subject"
                    type="text"
                    value={formData.subject}
                    onChange={(e) => handleInputChange('subject', e.target.value)}
                    required
                />
                {errors.subject && (
                    <div className="field-error">{errors.subject.join(', ')}</div>
                )}
            </div>
            
            <div className="form-group">
                <label htmlFor="message">Message:</label>
                <textarea
                    id="message"
                    value={formData.message}
                    onChange={(e) => handleInputChange('message', e.target.value)}
                    rows={5}
                    required
                />
                <div className="character-count">
                    {formData.message.length}/2000 characters
                </div>
                {errors.message && (
                    <div className="field-error">{errors.message.join(', ')}</div>
                )}
            </div>
            
            <button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Sending...' : 'Send Message'}
            </button>
        </form>
    );
};

// =============================================================================
// SECURE STORAGE EXAMPLES
// =============================================================================

/**
 * Settings Component with Secure Storage
 */
const UserSettings = () => {
    const [settings, setSettings] = useState({
        theme: 'light',
        notifications: true,
        autoSave: false
    });
    const [storageInfo, setStorageInfo] = useState(null);

    useEffect(() => {
        // Load settings from secure storage
        loadSettings();
        
        // Show storage info
        updateStorageInfo();
    }, []);

    const loadSettings = () => {
        const savedSettings = secureStorage.getItem('user_settings');
        if (savedSettings) {
            setSettings(savedSettings);
        }
    };

    const saveSettings = (newSettings) => {
        setSettings(newSettings);
        
        // Save to secure storage with 7-day expiration
        secureStorage.setItem('user_settings', newSettings, 7 * 24 * 60); // 7 days in minutes
        
        updateStorageInfo();
        
        // Log settings change
        securityMonitor.logEvent('SETTINGS_CHANGED', {
            changes: Object.keys(newSettings).filter(key => newSettings[key] !== settings[key])
        });
    };

    const updateStorageInfo = () => {
        // Generate some storage statistics
        const keys = Object.keys(localStorage);
        const secureKeys = keys.filter(key => key.startsWith('secure_'));
        
        setStorageInfo({
            totalKeys: keys.length,
            secureKeys: secureKeys.length,
            storageUsed: JSON.stringify(localStorage).length
        });
    };

    const clearSecureStorage = () => {
        secureStorage.clear();
        updateStorageInfo();
        alert('Secure storage cleared!');
    };

    return (
        <div className="user-settings">
            <h2>User Settings</h2>
            
            <div className="settings-group">
                <h3>Preferences</h3>
                
                <label>
                    <input
                        type="radio"
                        name="theme"
                        value="light"
                        checked={settings.theme === 'light'}
                        onChange={() => saveSettings({ ...settings, theme: 'light' })}
                    />
                    Light Theme
                </label>
                
                <label>
                    <input
                        type="radio"
                        name="theme"
                        value="dark"
                        checked={settings.theme === 'dark'}
                        onChange={() => saveSettings({ ...settings, theme: 'dark' })}
                    />
                    Dark Theme
                </label>
                
                <label>
                    <input
                        type="checkbox"
                        checked={settings.notifications}
                        onChange={(e) => saveSettings({ ...settings, notifications: e.target.checked })}
                    />
                    Enable Notifications
                </label>
                
                <label>
                    <input
                        type="checkbox"
                        checked={settings.autoSave}
                        onChange={(e) => saveSettings({ ...settings, autoSave: e.target.checked })}
                    />
                    Auto-save Changes
                </label>
            </div>
            
            {storageInfo && (
                <div className="storage-info">
                    <h3>Storage Information</h3>
                    <p>Total Keys: {storageInfo.totalKeys}</p>
                    <p>Secure Keys: {storageInfo.secureKeys}</p>
                    <p>Storage Used: {(storageInfo.storageUsed / 1024).toFixed(2)} KB</p>
                    
                    <button onClick={clearSecureStorage} className="danger-button">
                        Clear Secure Storage
                    </button>
                </div>
            )}
        </div>
    );
};

// =============================================================================
// SECURITY MONITORING EXAMPLES
// =============================================================================

/**
 * Security Dashboard Component
 */
const SecurityDashboard = () => {
    const [securityReport, setSecurityReport] = useState(null);
    const [clientFingerprint, setClientFingerprint] = useState(null);
    const [randomTokens, setRandomTokens] = useState([]);

    useEffect(() => {
        loadSecurityData();
        generateRandomTokens();
    }, []);

    const loadSecurityData = async () => {
        // Get security report
        const report = securityMonitor.getSecurityReport();
        setSecurityReport(report);
        
        // Get client fingerprint
        const fingerprint = SecurityHelpers.getClientFingerprint();
        setClientFingerprint(fingerprint);
    };

    const generateRandomTokens = () => {
        const tokens = [
            SecureRandom.string(16),
            SecureRandom.string(32, 'ABCDEF0123456789'), // Hex only
            SecureRandom.uuid(),
            SecureRandom.number(1000, 9999).toString()
        ];
        setRandomTokens(tokens);
    };

    const triggerSecurityEvent = (eventType) => {
        securityMonitor.logEvent(eventType, {
            triggered_by: 'user',
            timestamp: Date.now()
        });
        
        // Refresh report
        setTimeout(() => {
            const report = securityMonitor.getSecurityReport();
            setSecurityReport(report);
        }, 100);
    };

    return (
        <div className="security-dashboard">
            <h2>Security Dashboard</h2>
            
            {securityReport && (
                <div className="security-report">
                    <h3>Security Report</h3>
                    <div className="report-stats">
                        <div className="stat">
                            <strong>Total Events:</strong> {securityReport.totalEvents}
                        </div>
                        <div className="stat">
                            <strong>Suspicious Events:</strong> {securityReport.suspiciousEvents.length}
                        </div>
                    </div>
                    
                    <h4>Event Types:</h4>
                    <ul>
                        {Object.entries(securityReport.eventTypes).map(([type, count]) => (
                            <li key={type}>
                                <strong>{type}:</strong> {count}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
            
            <div className="security-actions">
                <h3>Test Security Events</h3>
                <button onClick={() => triggerSecurityEvent('TEST_EVENT')}>
                    Trigger Test Event
                </button>
                <button onClick={() => triggerSecurityEvent('SUSPICIOUS_ACTIVITY')}>
                    Trigger Suspicious Activity
                </button>
                <button onClick={() => triggerSecurityEvent('LOGIN_ATTEMPT')}>
                    Trigger Login Attempt
                </button>
            </div>
            
            {clientFingerprint && (
                <div className="client-fingerprint">
                    <h3>Client Fingerprint</h3>
                    <pre>{JSON.stringify(clientFingerprint, null, 2)}</pre>
                </div>
            )}
            
            <div className="random-tokens">
                <h3>Secure Random Tokens</h3>
                <ul>
                    {randomTokens.map((token, index) => (
                        <li key={index}>
                            <code>{token}</code>
                        </li>
                    ))}
                </ul>
                <button onClick={generateRandomTokens}>
                    Generate New Tokens
                </button>
            </div>
        </div>
    );
};

// =============================================================================
// SESSION TIMEOUT EXAMPLE
// =============================================================================

/**
 * Component with Session Timeout
 */
const SessionTimeoutExample = () => {
    const { user, isAuthenticated } = useAuth();
    const { resetTimeout } = useSessionTimeout(5); // 5 minute timeout
    const [activityCount, setActivityCount] = useState(0);

    const handleUserActivity = () => {
        setActivityCount(prev => prev + 1);
        resetTimeout();
    };

    if (!isAuthenticated) {
        return <div>Please log in to see session timeout example.</div>;
    }

    return (
        <div className="session-timeout-example">
            <h2>Session Timeout Example</h2>
            <p>User: {user?.email}</p>
            <p>Activity Count: {activityCount}</p>
            <p>Session will timeout after 5 minutes of inactivity.</p>
            
            <button onClick={handleUserActivity}>
                Record Activity
            </button>
            
            <div className="activity-info">
                <small>
                    Click anywhere, type, or scroll to reset the session timeout.
                    The session will automatically logout after 5 minutes of inactivity.
                </small>
            </div>
        </div>
    );
};

// =============================================================================
// MAIN APPLICATION EXAMPLE
// =============================================================================

/**
 * Main Application with Security Integration
 */
const SecureApp = () => {
    return (
        <AuthProvider>
            <Router>
                <div className="app">
                    <nav className="navigation">
                        <AuthNavigation />
                    </nav>
                    
                    <main className="main-content">
                        <Routes>
                            {/* Public Routes */}
                            <Route path="/login" element={<LoginForm />} />
                            <Route path="/register" element={<RegistrationForm />} />
                            <Route path="/contact" element={<ContactForm />} />
                            
                            {/* Protected Routes */}
                            <Route path="/dashboard" element={
                                <ProtectedRoute>
                                    <Dashboard />
                                </ProtectedRoute>
                            } />
                            
                            <Route path="/settings" element={
                                <ProtectedRoute>
                                    <UserSettings />
                                </ProtectedRoute>
                            } />
                            
                            <Route path="/session-timeout" element={
                                <ProtectedRoute>
                                    <SessionTimeoutExample />
                                </ProtectedRoute>
                            } />
                            
                            {/* Admin Routes */}
                            <Route path="/admin" element={
                                <AdminRoute>
                                    <AdminPanel />
                                </AdminRoute>
                            } />
                            
                            <Route path="/security" element={
                                <AdminRoute>
                                    <SecurityDashboard />
                                </AdminRoute>
                            } />
                            
                            {/* Default Route */}
                            <Route path="/" element={<Navigate to="/dashboard" replace />} />
                        </Routes>
                    </main>
                </div>
            </Router>
        </AuthProvider>
    );
};

/**
 * Navigation Component with Auth State
 */
const AuthNavigation = () => {
    const { isAuthenticated, isAdmin, user, logout } = useAuth();

    return (
        <nav className="auth-navigation">
            {isAuthenticated ? (
                <>
                    <span>Welcome, {escapeHtml(user?.username || user?.email || 'User')}</span>
                    <a href="/dashboard">Dashboard</a>
                    <a href="/settings">Settings</a>
                    {isAdmin && (
                        <>
                            <a href="/admin">Admin</a>
                            <a href="/security">Security</a>
                        </>
                    )}
                    <button onClick={logout}>Logout</button>
                </>
            ) : (
                <>
                    <a href="/login">Login</a>
                    <a href="/register">Register</a>
                    <a href="/contact">Contact</a>
                </>
            )}
        </nav>
    );
};

export default SecureApp;
