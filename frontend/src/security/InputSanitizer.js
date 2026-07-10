// ==============================================================================
// File:      frontend/src/security/InputSanitizer.js
// Purpose:   Frontend input validation and sanitization library. Provides
//            HTML escaping, XSS protection, email/URL/password validation,
//            form data sanitization, client-side rate limiting, a React
//            validation hook, and secure token generation.
// Callers:   security/index.js
// Callees:   React (useState, useCallback)
// Modified:  2026-04-22
// ==============================================================================
/**
 * Input Sanitizer - Frontend Input Validation and Sanitization
 * 
 * Provides comprehensive input validation, sanitization, and XSS protection
 * for user inputs in React components.
 */

/**
 * HTML Entity Encoder/Decoder
 */
const htmlEntities = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#x27;',
    '/': '&#x2F;'
};

/**
 * Escape HTML characters to prevent XSS
 */
export const escapeHtml = (text) => {
    if (typeof text !== 'string') {
        return text;
    }
    
    return text.replace(/[&<>"'/]/g, (char) => htmlEntities[char]);
};

/**
 * Unescape HTML entities
 */
export const unescapeHtml = (text) => {
    if (typeof text !== 'string') {
        return text;
    }
    
    const reverseEntities = Object.fromEntries(
        Object.entries(htmlEntities).map(([key, value]) => [value, key])
    );
    
    return text.replace(/&amp;|&lt;|&gt;|&quot;|&#x27;|&#x2F;/g, (entity) => reverseEntities[entity]);
};

/**
 * Remove potentially dangerous HTML tags and attributes
 */
export const sanitizeHtml = (html) => {
    if (typeof html !== 'string') {
        return html;
    }
    
    // Allowed tags and attributes
    const allowedTags = ['p', 'br', 'strong', 'em', 'u', 'i', 'b', 'span', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'];
    const allowedAttributes = ['class', 'id'];
    
    // Remove script tags and their content
    html = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
    
    // Remove dangerous event handlers
    html = html.replace(/\s*on\w+\s*=\s*["'][^"']*["']/gi, '');
    
    // Remove javascript: URLs
    html = html.replace(/javascript:/gi, '');
    
    // Remove data: URLs (except images)
    html = html.replace(/data:(?!image\/)/gi, '');
    
    // Basic tag filtering (this is a simple implementation)
    // For production, consider using a library like DOMPurify
    const tagRegex = /<(\/?)([\w-]+)([^>]*)>/gi;
    html = html.replace(tagRegex, (match, closing, tagName, attributes) => {
        const lowerTagName = tagName.toLowerCase();
        
        if (!allowedTags.includes(lowerTagName)) {
            return '';
        }
        
        // Filter attributes
        const filteredAttributes = attributes.replace(/(\w+)\s*=\s*["']([^"']*)["']/g, (attrMatch, attrName, attrValue) => {
            if (allowedAttributes.includes(attrName.toLowerCase())) {
                return `${attrName}="${escapeHtml(attrValue)}"`;
            }
            return '';
        });
        
        return `<${closing}${tagName}${filteredAttributes}>`;
    });
    
    return html;
};

/**
 * Validate email format
 */
export const isValidEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
};

/**
 * Validate URL format
 */
export const isValidUrl = (url) => {
    try {
        const urlObj = new URL(url);
        return ['http:', 'https:'].includes(urlObj.protocol);
    } catch {
        return false;
    }
};

/**
 * Validate password strength
 */
export const validatePassword = (password) => {
    const result = {
        isValid: false,
        score: 0,
        feedback: []
    };
    
    if (!password || typeof password !== 'string') {
        result.feedback.push('Password is required');
        return result;
    }
    
    // Length check
    if (password.length < 8) {
        result.feedback.push('Password must be at least 8 characters long');
    } else {
        result.score += 1;
    }
    
    // Uppercase check
    if (!/[A-Z]/.test(password)) {
        result.feedback.push('Password must contain at least one uppercase letter');
    } else {
        result.score += 1;
    }
    
    // Lowercase check
    if (!/[a-z]/.test(password)) {
        result.feedback.push('Password must contain at least one lowercase letter');
    } else {
        result.score += 1;
    }
    
    // Number check
    if (!/\d/.test(password)) {
        result.feedback.push('Password must contain at least one number');
    } else {
        result.score += 1;
    }
    
    // Special character check
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
        result.feedback.push('Password must contain at least one special character');
    } else {
        result.score += 1;
    }
    
    // Common password check
    const commonPasswords = ['password', '123456', 'password123', 'admin', 'qwerty'];
    if (commonPasswords.includes(password.toLowerCase())) {
        result.feedback.push('Password is too common');
        result.score = Math.max(0, result.score - 2);
    }
    
    result.isValid = result.score >= 4 && result.feedback.length === 0;
    
    return result;
};

/**
 * Sanitize user input for safe storage and display
 */
export const sanitizeInput = (input, options = {}) => {
    const {
        maxLength = 1000,
        allowHtml = false,
        trimWhitespace = true,
        removeLineBreaks = false
    } = options;
    
    if (typeof input !== 'string') {
        return input;
    }
    
    let sanitized = input;
    
    // Trim whitespace
    if (trimWhitespace) {
        sanitized = sanitized.trim();
    }
    
    // Remove line breaks if requested
    if (removeLineBreaks) {
        sanitized = sanitized.replace(/[\r\n]/g, ' ');
    }
    
    // Limit length
    if (sanitized.length > maxLength) {
        sanitized = sanitized.substring(0, maxLength);
    }
    
    // Handle HTML
    if (allowHtml) {
        sanitized = sanitizeHtml(sanitized);
    } else {
        sanitized = escapeHtml(sanitized);
    }
    
    return sanitized;
};

/**
 * Validate and sanitize form data
 */
export const validateFormData = (data, schema) => {
    const result = {
        isValid: true,
        sanitizedData: {},
        errors: {}
    };
    
    for (const [field, rules] of Object.entries(schema)) {
        const value = data[field];
        let sanitizedValue = value;
        const fieldErrors = [];
        
        // Required check
        if (rules.required && (!value || (typeof value === 'string' && value.trim() === ''))) {
            fieldErrors.push(`${field} is required`);
        }
        
        if (value && typeof value === 'string') {
            // Length validation
            if (rules.minLength && value.length < rules.minLength) {
                fieldErrors.push(`${field} must be at least ${rules.minLength} characters`);
            }
            
            if (rules.maxLength && value.length > rules.maxLength) {
                fieldErrors.push(`${field} must be no more than ${rules.maxLength} characters`);
            }
            
            // Type-specific validation
            if (rules.type === 'email' && !isValidEmail(value)) {
                fieldErrors.push(`${field} must be a valid email address`);
            }
            
            if (rules.type === 'url' && !isValidUrl(value)) {
                fieldErrors.push(`${field} must be a valid URL`);
            }
            
            if (rules.type === 'password') {
                const passwordValidation = validatePassword(value);
                if (!passwordValidation.isValid) {
                    fieldErrors.push(...passwordValidation.feedback);
                }
            }
            
            // Pattern validation
            if (rules.pattern && !rules.pattern.test(value)) {
                fieldErrors.push(rules.patternMessage || `${field} format is invalid`);
            }
            
            // Custom validation
            if (rules.validate && typeof rules.validate === 'function') {
                const customResult = rules.validate(value);
                if (customResult !== true) {
                    fieldErrors.push(customResult || `${field} is invalid`);
                }
            }
            
            // Sanitize the value
            sanitizedValue = sanitizeInput(value, {
                maxLength: rules.maxLength || 1000,
                allowHtml: rules.allowHtml || false,
                trimWhitespace: rules.trimWhitespace !== false,
                removeLineBreaks: rules.removeLineBreaks || false
            });
        }
        
        result.sanitizedData[field] = sanitizedValue;
        
        if (fieldErrors.length > 0) {
            result.errors[field] = fieldErrors;
            result.isValid = false;
        }
    }
    
    return result;
};

/**
 * Rate limiting for client-side actions
 */
export class ClientRateLimiter {
    constructor() {
        this.requests = new Map();
    }
    
    isAllowed(key, maxRequests = 10, windowMs = 60000) {
        const now = Date.now();
        const windowStart = now - windowMs;
        
        if (!this.requests.has(key)) {
            this.requests.set(key, []);
        }
        
        const requests = this.requests.get(key);
        
        // Remove old requests
        const validRequests = requests.filter(timestamp => timestamp > windowStart);
        
        if (validRequests.length >= maxRequests) {
            return false;
        }
        
        // Add current request
        validRequests.push(now);
        this.requests.set(key, validRequests);
        
        return true;
    }
    
    cleanup(maxAge = 3600000) { // 1 hour
        const cutoff = Date.now() - maxAge;
        
        for (const [key, requests] of this.requests.entries()) {
            const validRequests = requests.filter(timestamp => timestamp > cutoff);
            
            if (validRequests.length === 0) {
                this.requests.delete(key);
            } else {
                this.requests.set(key, validRequests);
            }
        }
    }
}

/**
 * Global rate limiter instance
 */
export const clientRateLimiter = new ClientRateLimiter();

/**
 * React hook for input validation
 */
import { useState, useCallback } from 'react';

export const useInputValidation = (initialValue = '', validationRules = {}) => {
    const [value, setValue] = useState(initialValue);
    const [errors, setErrors] = useState([]);
    const [isValid, setIsValid] = useState(true);
    
    const validate = useCallback((inputValue) => {
        const validation = validateFormData(
            { input: inputValue },
            { input: validationRules }
        );
        
        setErrors(validation.errors.input || []);
        setIsValid(validation.isValid);
        
        return validation.isValid;
    }, [validationRules]);
    
    const handleChange = useCallback((newValue) => {
        const sanitized = sanitizeInput(newValue, validationRules);
        setValue(sanitized);
        validate(sanitized);
    }, [validate, validationRules]);
    
    const reset = useCallback(() => {
        setValue(initialValue);
        setErrors([]);
        setIsValid(true);
    }, [initialValue]);
    
    return {
        value,
        errors,
        isValid,
        handleChange,
        validate: () => validate(value),
        reset
    };
};

/**
 * Secure random string generator
 */
export const generateSecureToken = (length = 32) => {
    const array = new Uint8Array(length);
    crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
};

/**
 * Content Security Policy nonce generator
 */
export const generateCSPNonce = () => {
    return generateSecureToken(16);
};
