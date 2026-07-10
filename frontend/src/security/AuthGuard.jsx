// ==============================================================================
// File:      frontend/src/security/AuthGuard.jsx
// Purpose:   Frontend authentication and authorization guard. Provides
//            route protection components (ProtectedRoute, AdminRoute),
//            an auth context provider, session timeout handling, and
//            hooks for checking auth state and permissions.
// Callers:   security/index.js
// Callees:   React, react-router-dom, utils/localStorage.js
//            (NOTE: db/adminConnector, db/mainConnector are imported but
//            the db/ directory does not exist — dead imports)
// Modified:  2026-04-22
// ==============================================================================
/**
 * AuthGuard - Frontend Authentication and Authorization Guard
 * 
 * Provides route protection, session management, and authentication state
 * for React components and routes.
 */

import React, { useEffect, useState, createContext, useContext } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import LocalStorageUtil from '../utils/localStorage';
import adminConnector from '../db/adminConnector';
import mainConnector from '../db/mainConnector';

/**
 * Authentication Guard Hook
 * Manages authentication state and provides auth utilities
 */
export const useAuthGuard = () => {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isAdmin, setIsAdmin] = useState(false);
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();
    const location = useLocation();

    /**
     * Check if user is authenticated
     */
    const checkAuth = async () => {
        try {
            setLoading(true);
            
            // Check for stored admin session
            const adminToken = LocalStorageUtil.get('admin_token');
            if (adminToken) {
                const result = await adminConnector.verifySession();
                if (result.success) {
                    setIsAuthenticated(true);
                    setIsAdmin(true);
                    setUser(result.data);
                    return;
                }
            }
            
            // Check for stored user session
            const userToken = LocalStorageUtil.get('user_token');
            if (userToken) {
                const result = await mainConnector.verifyUserSession();
                if (result.success) {
                    setIsAuthenticated(true);
                    setIsAdmin(false);
                    setUser(result.data);
                    return;
                }
            }
            
            // No valid session found
            setIsAuthenticated(false);
            setIsAdmin(false);
            setUser(null);
            
        } catch (error) {
            console.error('Auth check failed:', error);
            setIsAuthenticated(false);
            setIsAdmin(false);
            setUser(null);
        } finally {
            setLoading(false);
        }
    };

    /**
     * Login user
     */
    const login = async (email, password, isAdminLogin = false) => {
        try {
            let result;
            
            if (isAdminLogin) {
                result = await adminConnector.login(email, password);
            } else {
                result = await mainConnector.loginUser(email, password);
            }
            
            if (result.success) {
                setIsAuthenticated(true);
                setIsAdmin(isAdminLogin);
                setUser(result.data);
                return { success: true, user: result.data };
            } else {
                return { success: false, error: result.error };
            }
        } catch (error) {
            return { success: false, error: error.message };
        }
    };

    /**
     * Logout user
     */
    const logout = async () => {
        try {
            if (isAdmin) {
                await adminConnector.logout();
            } else {
                await mainConnector.logoutUser();
            }
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            setIsAuthenticated(false);
            setIsAdmin(false);
            setUser(null);
            navigate('/');
        }
    };

    /**
     * Check if user has specific permission
     */
    const hasPermission = (permission) => {
        if (!isAuthenticated || !user) return false;
        
        // Admin users have all permissions
        if (isAdmin) return true;
        
        // Check user permissions
        const userPermissions = user.permissions || [];
        return userPermissions.includes(permission);
    };

    /**
     * Require authentication for current route
     */
    const requireAuth = (redirectTo = '/login') => {
        if (!loading && !isAuthenticated) {
            navigate(redirectTo, { 
                state: { from: location.pathname },
                replace: true 
            });
        }
    };

    /**
     * Require admin privileges for current route
     */
    const requireAdmin = (redirectTo = '/') => {
        if (!loading && (!isAuthenticated || !isAdmin)) {
            navigate(redirectTo, { 
                state: { from: location.pathname },
                replace: true 
            });
        }
    };

    // Check auth on mount and token changes
    useEffect(() => {
        checkAuth();
    }, []);

    return {
        isAuthenticated,
        isAdmin,
        user,
        loading,
        login,
        logout,
        hasPermission,
        requireAuth,
        requireAdmin,
        checkAuth
    };
};

/**
 * Protected Route Component
 * Wraps components that require authentication
 */
export const ProtectedRoute = ({ 
    children, 
    requireAdmin = false, 
    requiredPermission = null,
    fallback = null,
    redirectTo = '/login' 
}) => {
    const { isAuthenticated, isAdmin, loading, hasPermission } = useAuthGuard();
    const navigate = useNavigate();
    const location = useLocation();

    useEffect(() => {
        if (loading) return;

        // Check authentication
        if (!isAuthenticated) {
            navigate(redirectTo, { 
                state: { from: location.pathname },
                replace: true 
            });
            return;
        }

        // Check admin requirement
        if (requireAdmin && !isAdmin) {
            navigate('/', { 
                state: { from: location.pathname },
                replace: true 
            });
            return;
        }

        // Check permission requirement
        if (requiredPermission && !hasPermission(requiredPermission)) {
            navigate('/', { 
                state: { from: location.pathname },
                replace: true 
            });
            return;
        }
    }, [isAuthenticated, isAdmin, loading, requireAdmin, requiredPermission]);

    if (loading) {
        return fallback || <div className="loading">Loading...</div>;
    }

    if (!isAuthenticated) {
        return null; // Will redirect
    }

    if (requireAdmin && !isAdmin) {
        return null; // Will redirect
    }

    if (requiredPermission && !hasPermission(requiredPermission)) {
        return null; // Will redirect
    }

    return children;
};

/**
 * Admin Route Component
 * Shorthand for routes that require admin privileges
 */
export const AdminRoute = ({ children, ...props }) => {
    return (
        <ProtectedRoute requireAdmin={true} {...props}>
            {children}
        </ProtectedRoute>
    );
};

/**
 * Authentication Context Provider
 * Provides auth state to entire app
 */
const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const auth = useAuthGuard();
    
    return (
        <AuthContext.Provider value={auth}>
            {children}
        </AuthContext.Provider>
    );
};

/**
 * Hook to use auth context
 */
export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

/**
 * Higher-Order Component for authentication
 */
export const withAuth = (Component, options = {}) => {
    return function AuthenticatedComponent(props) {
        const auth = useAuth();
        
        if (options.requireAuth && !auth.isAuthenticated) {
            return <div>Please log in to access this content.</div>;
        }
        
        if (options.requireAdmin && !auth.isAdmin) {
            return <div>Admin access required.</div>;
        }
        
        return <Component {...props} auth={auth} />;
    };
};

/**
 * Session timeout handler
 */
export const useSessionTimeout = (timeoutMinutes = 30) => {
    const { logout, isAuthenticated } = useAuth();
    const [lastActivity, setLastActivity] = useState(Date.now());

    const resetTimeout = () => {
        setLastActivity(Date.now());
    };

    useEffect(() => {
        if (!isAuthenticated) return;

        const checkTimeout = () => {
            const now = Date.now();
            const timeSinceLastActivity = now - lastActivity;
            const timeoutMs = timeoutMinutes * 60 * 1000;

            if (timeSinceLastActivity > timeoutMs) {
                logout();
                alert('Your session has expired due to inactivity.');
            }
        };

        // Check every minute
        const interval = setInterval(checkTimeout, 60000);

        // Listen for user activity
        const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
        const resetTimeoutHandler = () => resetTimeout();

        events.forEach(event => {
            document.addEventListener(event, resetTimeoutHandler, true);
        });

        return () => {
            clearInterval(interval);
            events.forEach(event => {
                document.removeEventListener(event, resetTimeoutHandler, true);
            });
        };
    }, [isAuthenticated, lastActivity, timeoutMinutes, logout]);

    return { resetTimeout };
};
