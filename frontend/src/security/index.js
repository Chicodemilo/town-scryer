// ==============================================================================
// File:      frontend/src/security/index.js
// Purpose:   Barrel export for the frontend security package. Re-exports
//            authentication guards, input sanitizers, security utilities,
//            configuration constants, validation schemas, and helpers.
// Callers:   security/examples.jsx
// Callees:   security/AuthGuard.jsx, security/InputSanitizer.js,
//            security/SecurityUtils.js
// Modified:  2026-04-22
// ==============================================================================
/**
 * Security Package for Frontend
 * 
 * This package provides comprehensive frontend security utilities including:
 * - Authentication guards and route protection
 * - Input validation and sanitization
 * - Security monitoring and utilities
 * - Secure storage and encryption helpers
 * 
 * Usage:
 *   import { useAuth, ProtectedRoute, AdminRoute } from './security';
 *   import { sanitizeInput, validateFormData } from './security';
 *   import { secureStorage, securityMonitor } from './security';
 */

// Authentication and Authorization
export {
    useAuthGuard,
    ProtectedRoute,
    AdminRoute,
    AuthProvider,
    useAuth,
    withAuth,
    useSessionTimeout
} from './AuthGuard.jsx';

// Input Validation and Sanitization
export {
    escapeHtml,
    unescapeHtml,
    sanitizeHtml,
    isValidEmail,
    isValidUrl,
    validatePassword,
    sanitizeInput,
    validateFormData,
    ClientRateLimiter,
    clientRateLimiter,
    useInputValidation,
    generateSecureToken,
    generateCSPNonce
} from './InputSanitizer';

// Security Utilities and Monitoring
export {
    SecureStorage,
    SecurityMonitor,
    CSPHelper,
    SecureRandom,
    checkSecurityHeaders,
    secureStorage,
    securityMonitor,
    cspHelper
} from './SecurityUtils';

// Security Configuration
export const SECURITY_CONFIG = {
    // Session timeout in minutes
    SESSION_TIMEOUT: 30,
    
    // Rate limiting
    RATE_LIMIT: {
        MAX_REQUESTS_PER_MINUTE: 60,
        MAX_LOGIN_ATTEMPTS: 5,
        LOCKOUT_DURATION: 15 // minutes
    },
    
    // Password requirements
    PASSWORD_REQUIREMENTS: {
        MIN_LENGTH: 8,
        REQUIRE_UPPERCASE: true,
        REQUIRE_LOWERCASE: true,
        REQUIRE_NUMBERS: true,
        REQUIRE_SPECIAL_CHARS: true
    },
    
    // Input validation
    INPUT_LIMITS: {
        MAX_TEXT_LENGTH: 1000,
        MAX_EMAIL_LENGTH: 254,
        MAX_URL_LENGTH: 2048,
        MAX_FILENAME_LENGTH: 255
    },
    
    // Security monitoring
    MONITORING: {
        MAX_EVENTS: 1000,
        SUSPICIOUS_THRESHOLD: 10,
        CLEANUP_INTERVAL: 300000 // 5 minutes
    }
};

// Security validation schemas for common forms
export const VALIDATION_SCHEMAS = {
    LOGIN: {
        email: {
            required: true,
            type: 'email',
            maxLength: 254
        },
        password: {
            required: true,
            minLength: 1,
            maxLength: 128
        }
    },
    
    REGISTER: {
        username: {
            required: true,
            minLength: 3,
            maxLength: 50,
            pattern: /^[a-zA-Z0-9_-]+$/,
            patternMessage: 'Username can only contain letters, numbers, underscores, and hyphens'
        },
        email: {
            required: true,
            type: 'email',
            maxLength: 254
        },
        password: {
            required: true,
            type: 'password'
        },
        confirmPassword: {
            required: true,
            validate: (value, data) => {
                return value === data.password || 'Passwords do not match';
            }
        }
    },
    
    CONTACT: {
        name: {
            required: true,
            minLength: 2,
            maxLength: 100
        },
        email: {
            required: true,
            type: 'email',
            maxLength: 254
        },
        subject: {
            required: true,
            minLength: 5,
            maxLength: 200
        },
        message: {
            required: true,
            minLength: 10,
            maxLength: 2000,
            allowHtml: false
        }
    },
    
    PROFILE: {
        username: {
            required: true,
            minLength: 3,
            maxLength: 50,
            pattern: /^[a-zA-Z0-9_-]+$/,
            patternMessage: 'Username can only contain letters, numbers, underscores, and hyphens'
        },
        email: {
            required: true,
            type: 'email',
            maxLength: 254
        },
        bio: {
            required: false,
            maxLength: 500,
            allowHtml: false
        }
    }
};

// Security utility functions
export const SecurityHelpers = {
    /**
     * Check if current environment is secure (HTTPS)
     */
    isSecureContext: () => {
        return window.location.protocol === 'https:' || 
               window.location.hostname === 'localhost' ||
               window.location.hostname === '127.0.0.1';
    },
    
    /**
     * Generate secure headers for API requests
     */
    getSecureHeaders: (includeAuth = true) => {
        const headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        };
        
        if (includeAuth) {
            const token = localStorage.getItem('auth_token');
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
        }
        
        return headers;
    },
    
    /**
     * Sanitize URL for safe redirects
     */
    sanitizeRedirectUrl: (url) => {
        if (!url || typeof url !== 'string') return '/';
        
        // Only allow relative URLs
        if (url.startsWith('/') && !url.startsWith('//')) {
            return url;
        }
        
        return '/';
    },
    
    /**
     * Check if user agent appears to be a bot
     */
    isLikelyBot: () => {
        const userAgent = navigator.userAgent.toLowerCase();
        const botPatterns = [
            'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget'
        ];
        
        return botPatterns.some(pattern => userAgent.includes(pattern));
    },
    
    /**
     * Get client fingerprint for security tracking
     */
    getClientFingerprint: () => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        ctx.textBaseline = 'top';
        ctx.font = '14px Arial';
        ctx.fillText('Security fingerprint', 2, 2);
        
        return {
            userAgent: navigator.userAgent,
            language: navigator.language,
            platform: navigator.platform,
            screen: `${screen.width}x${screen.height}`,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            canvas: canvas.toDataURL(),
            timestamp: Date.now()
        };
    }
};

// Initialize security on module load
if (typeof window !== 'undefined') {
    // Set up global error handler for security events
    window.addEventListener('error', (event) => {
        if (window.securityMonitor) {
            window.securityMonitor.logEvent('JAVASCRIPT_ERROR', {
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno
            });
        }
    });
    
    // Set up unhandled promise rejection handler
    window.addEventListener('unhandledrejection', (event) => {
        if (window.securityMonitor) {
            window.securityMonitor.logEvent('UNHANDLED_PROMISE_REJECTION', {
                reason: event.reason?.toString() || 'Unknown'
            });
        }
    });
    
    // Expose security utilities globally for debugging (development only)
    if (process.env.NODE_ENV === 'development') {
        window.SecurityHelpers = SecurityHelpers;
        window.SECURITY_CONFIG = SECURITY_CONFIG;
    }
}
