// ==============================================================================
// File:      frontend/src/security/SecurityUtils.js
// Purpose:   Frontend security utility classes. Provides encrypted
//            localStorage wrapper (SecureStorage), security event monitor
//            (SecurityMonitor), CSP nonce helper, secure random generator,
//            and security headers checker.
// Callers:   security/index.js
// Callees:   (none — uses browser APIs: localStorage, crypto, fetch)
// Modified:  2026-04-22
// ==============================================================================
/**
 * Security Utilities - Frontend Security Helper Functions
 * 
 * Provides various security utilities for frontend applications including
 * secure storage, encryption helpers, and security monitoring.
 */

/**
 * Secure Local Storage Wrapper
 * Provides encrypted storage with automatic expiration
 */
export class SecureStorage {
    constructor(encryptionKey = null) {
        this.encryptionKey = encryptionKey || this.generateKey();
        this.prefix = 'secure_';
    }
    
    /**
     * Generate encryption key
     */
    generateKey() {
        return crypto.getRandomValues(new Uint8Array(32));
    }
    
    /**
     * Simple XOR encryption (for demo - use proper encryption in production)
     */
    encrypt(data, key) {
        const dataBytes = new TextEncoder().encode(JSON.stringify(data));
        const encrypted = new Uint8Array(dataBytes.length);
        
        for (let i = 0; i < dataBytes.length; i++) {
            encrypted[i] = dataBytes[i] ^ key[i % key.length];
        }
        
        return Array.from(encrypted).map(b => b.toString(16).padStart(2, '0')).join('');
    }
    
    /**
     * Simple XOR decryption
     */
    decrypt(encryptedHex, key) {
        try {
            const encrypted = new Uint8Array(
                encryptedHex.match(/.{2}/g).map(byte => parseInt(byte, 16))
            );
            
            const decrypted = new Uint8Array(encrypted.length);
            
            for (let i = 0; i < encrypted.length; i++) {
                decrypted[i] = encrypted[i] ^ key[i % key.length];
            }
            
            const decryptedString = new TextDecoder().decode(decrypted);
            return JSON.parse(decryptedString);
        } catch (error) {
            console.error('Decryption failed:', error);
            return null;
        }
    }
    
    /**
     * Store data securely with expiration
     */
    setItem(key, value, expirationMinutes = 60) {
        const item = {
            value,
            timestamp: Date.now(),
            expiration: Date.now() + (expirationMinutes * 60 * 1000)
        };
        
        const encrypted = this.encrypt(item, this.encryptionKey);
        localStorage.setItem(this.prefix + key, encrypted);
    }
    
    /**
     * Retrieve and decrypt data
     */
    getItem(key) {
        const encrypted = localStorage.getItem(this.prefix + key);
        if (!encrypted) return null;
        
        const decrypted = this.decrypt(encrypted, this.encryptionKey);
        if (!decrypted) return null;
        
        // Check expiration
        if (Date.now() > decrypted.expiration) {
            this.removeItem(key);
            return null;
        }
        
        return decrypted.value;
    }
    
    /**
     * Remove item
     */
    removeItem(key) {
        localStorage.removeItem(this.prefix + key);
    }
    
    /**
     * Clear all secure items
     */
    clear() {
        const keys = Object.keys(localStorage);
        keys.forEach(key => {
            if (key.startsWith(this.prefix)) {
                localStorage.removeItem(key);
            }
        });
    }
    
    /**
     * Clean expired items
     */
    cleanExpired() {
        const keys = Object.keys(localStorage);
        keys.forEach(key => {
            if (key.startsWith(this.prefix)) {
                const originalKey = key.substring(this.prefix.length);
                this.getItem(originalKey); // This will remove expired items
            }
        });
    }
}

/**
 * Security Event Monitor
 * Monitors for suspicious activities and security events
 */
export class SecurityMonitor {
    constructor() {
        this.events = [];
        this.maxEvents = 1000;
        this.suspiciousThreshold = 10;
        this.init();
    }
    
    init() {
        // Monitor for suspicious activities
        this.monitorConsoleAccess();
        this.monitorDevTools();
        this.monitorRapidClicks();
        this.monitorSuspiciousRequests();
    }
    
    /**
     * Log security event
     */
    logEvent(type, details = {}) {
        const event = {
            type,
            details,
            timestamp: Date.now(),
            userAgent: navigator.userAgent,
            url: window.location.href
        };
        
        this.events.push(event);
        
        // Keep only recent events
        if (this.events.length > this.maxEvents) {
            this.events = this.events.slice(-this.maxEvents);
        }
        
        // Check for suspicious patterns
        this.checkSuspiciousActivity(type);
        
        console.warn('Security Event:', event);
    }
    
    /**
     * Check for suspicious activity patterns
     */
    checkSuspiciousActivity(eventType) {
        const recentEvents = this.events.filter(
            event => Date.now() - event.timestamp < 60000 // Last minute
        );
        
        const typeCount = recentEvents.filter(event => event.type === eventType).length;
        
        if (typeCount > this.suspiciousThreshold) {
            this.logEvent('SUSPICIOUS_ACTIVITY', {
                eventType,
                count: typeCount,
                timeWindow: '1 minute'
            });
            
            // Could trigger additional security measures here
            this.handleSuspiciousActivity(eventType, typeCount);
        }
    }
    
    /**
     * Handle suspicious activity
     */
    handleSuspiciousActivity(eventType, count) {
        // Log to server
        if (window.errorHandler) {
            window.errorHandler.logError({
                category: 'security',
                message: `Suspicious activity detected: ${eventType} (${count} times)`,
                severity: 'high'
            }, 'security_monitor');
        }
        
        // Could implement additional measures:
        // - Rate limiting
        // - Account lockout
        // - CAPTCHA challenges
        // - Admin notifications
    }
    
    /**
     * Monitor console access
     */
    monitorConsoleAccess() {
        const originalLog = console.log;
        const originalWarn = console.warn;
        const originalError = console.error;
        
        console.log = (...args) => {
            this.logEvent('CONSOLE_ACCESS', { method: 'log', args: args.length });
            return originalLog.apply(console, args);
        };
        
        console.warn = (...args) => {
            this.logEvent('CONSOLE_ACCESS', { method: 'warn', args: args.length });
            return originalWarn.apply(console, args);
        };
        
        console.error = (...args) => {
            this.logEvent('CONSOLE_ACCESS', { method: 'error', args: args.length });
            return originalError.apply(console, args);
        };
    }
    
    /**
     * Monitor for developer tools
     */
    monitorDevTools() {
        let devtools = { open: false };
        
        setInterval(() => {
            if (window.outerHeight - window.innerHeight > 200 || 
                window.outerWidth - window.innerWidth > 200) {
                if (!devtools.open) {
                    devtools.open = true;
                    this.logEvent('DEVTOOLS_OPENED');
                }
            } else {
                if (devtools.open) {
                    devtools.open = false;
                    this.logEvent('DEVTOOLS_CLOSED');
                }
            }
        }, 1000);
    }
    
    /**
     * Monitor rapid clicking
     */
    monitorRapidClicks() {
        let clickCount = 0;
        let clickTimer = null;
        
        document.addEventListener('click', () => {
            clickCount++;
            
            if (clickTimer) {
                clearTimeout(clickTimer);
            }
            
            clickTimer = setTimeout(() => {
                if (clickCount > 20) { // More than 20 clicks in 5 seconds
                    this.logEvent('RAPID_CLICKING', { count: clickCount });
                }
                clickCount = 0;
            }, 5000);
        });
    }
    
    /**
     * Monitor suspicious requests
     */
    monitorSuspiciousRequests() {
        const originalFetch = window.fetch;
        
        window.fetch = async (...args) => {
            const [url, options] = args;
            
            // Check for suspicious patterns
            if (typeof url === 'string') {
                if (url.includes('admin') && !window.location.pathname.includes('admin')) {
                    this.logEvent('SUSPICIOUS_REQUEST', { url, type: 'admin_access' });
                }
                
                if (url.includes('..') || url.includes('%2e%2e')) {
                    this.logEvent('SUSPICIOUS_REQUEST', { url, type: 'path_traversal' });
                }
            }
            
            return originalFetch.apply(window, args);
        };
    }
    
    /**
     * Get security report
     */
    getSecurityReport() {
        const now = Date.now();
        const last24Hours = this.events.filter(event => now - event.timestamp < 86400000);
        
        const eventTypes = {};
        last24Hours.forEach(event => {
            eventTypes[event.type] = (eventTypes[event.type] || 0) + 1;
        });
        
        return {
            totalEvents: last24Hours.length,
            eventTypes,
            suspiciousEvents: last24Hours.filter(event => 
                event.type === 'SUSPICIOUS_ACTIVITY' || 
                event.type.includes('SUSPICIOUS')
            ),
            timeRange: '24 hours'
        };
    }
}

/**
 * Content Security Policy Helper
 */
export class CSPHelper {
    constructor() {
        this.nonce = this.generateNonce();
    }
    
    generateNonce() {
        const array = new Uint8Array(16);
        crypto.getRandomValues(array);
        return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
    }
    
    /**
     * Create script element with CSP nonce
     */
    createSecureScript(src, content = null) {
        const script = document.createElement('script');
        script.nonce = this.nonce;
        
        if (src) {
            script.src = src;
        }
        
        if (content) {
            script.textContent = content;
        }
        
        return script;
    }
    
    /**
     * Create style element with CSP nonce
     */
    createSecureStyle(content) {
        const style = document.createElement('style');
        style.nonce = this.nonce;
        style.textContent = content;
        return style;
    }
    
    /**
     * Report CSP violation
     */
    reportViolation(violation) {
        console.error('CSP Violation:', violation);
        
        if (window.errorHandler) {
            window.errorHandler.logError({
                category: 'security',
                message: `CSP Violation: ${violation.violatedDirective}`,
                details: violation
            }, 'csp_monitor');
        }
    }
}

/**
 * Secure Random Generator
 */
export class SecureRandom {
    /**
     * Generate secure random string
     */
    static string(length = 32, charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789') {
        const array = new Uint8Array(length);
        crypto.getRandomValues(array);
        
        return Array.from(array, byte => charset[byte % charset.length]).join('');
    }
    
    /**
     * Generate secure random number
     */
    static number(min = 0, max = 1) {
        const array = new Uint32Array(1);
        crypto.getRandomValues(array);
        
        return min + (array[0] / (0xFFFFFFFF + 1)) * (max - min);
    }
    
    /**
     * Generate UUID v4
     */
    static uuid() {
        const array = new Uint8Array(16);
        crypto.getRandomValues(array);
        
        // Set version (4) and variant bits
        array[6] = (array[6] & 0x0f) | 0x40;
        array[8] = (array[8] & 0x3f) | 0x80;
        
        const hex = Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
        
        return [
            hex.slice(0, 8),
            hex.slice(8, 12),
            hex.slice(12, 16),
            hex.slice(16, 20),
            hex.slice(20, 32)
        ].join('-');
    }
}

/**
 * Security Headers Checker
 */
export const checkSecurityHeaders = async (url = window.location.origin) => {
    try {
        const response = await fetch(url, { method: 'HEAD' });
        const headers = response.headers;
        
        const securityHeaders = {
            'Content-Security-Policy': headers.get('Content-Security-Policy'),
            'X-Content-Type-Options': headers.get('X-Content-Type-Options'),
            'X-Frame-Options': headers.get('X-Frame-Options'),
            'X-XSS-Protection': headers.get('X-XSS-Protection'),
            'Strict-Transport-Security': headers.get('Strict-Transport-Security'),
            'Referrer-Policy': headers.get('Referrer-Policy')
        };
        
        const missing = Object.entries(securityHeaders)
            .filter(([key, value]) => !value)
            .map(([key]) => key);
        
        return {
            present: Object.fromEntries(
                Object.entries(securityHeaders).filter(([key, value]) => value)
            ),
            missing,
            score: ((Object.keys(securityHeaders).length - missing.length) / Object.keys(securityHeaders).length) * 100
        };
    } catch (error) {
        console.error('Failed to check security headers:', error);
        return null;
    }
};

// Global instances
export const secureStorage = new SecureStorage();
export const securityMonitor = new SecurityMonitor();
export const cspHelper = new CSPHelper();

// Initialize security monitoring
if (typeof window !== 'undefined') {
    // Clean expired secure storage items on page load
    secureStorage.cleanExpired();
    
    // Set up CSP violation reporting
    document.addEventListener('securitypolicyviolation', (event) => {
        cspHelper.reportViolation(event);
    });
    
    // Periodic cleanup
    setInterval(() => {
        secureStorage.cleanExpired();
    }, 300000); // Every 5 minutes
}
