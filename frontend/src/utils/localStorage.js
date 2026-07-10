// ==============================================================================
// File:      frontend/src/utils/localStorage.js
// Purpose:   LocalStorage utility class with JSON serialization, admin
//            session helpers, and storage inspection methods. Provides a
//            safe wrapper around browser localStorage with error handling.
// Callers:   security/AuthGuard.jsx
// Callees:   (none — uses browser localStorage API directly)
// Modified:  2026-04-22
// ==============================================================================
/**
 * LocalStorage utility class for managing browser localStorage
 * Provides simple methods for saving, getting, and deleting data
 * Handles JSON serialization/deserialization automatically
 */
class LocalStorageUtil {
    /**
     * Save data to localStorage
     * @param {string} key - The key to store the data under
     * @param {any} value - The value to store (will be JSON stringified)
     * @returns {boolean} - True if successful, false if failed
     */
    static set(key, value) {
        try {
            const serializedValue = JSON.stringify(value);
            localStorage.setItem(key, serializedValue);
            return true;
        } catch (error) {
            console.error('Error saving to localStorage:', error);
            return false;
        }
    }

    /**
     * Get data from localStorage
     * @param {string} key - The key to retrieve data for
     * @param {any} defaultValue - Default value to return if key doesn't exist
     * @returns {any} - The parsed value or defaultValue
     */
    static get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            if (item === null) {
                return defaultValue;
            }
            return JSON.parse(item);
        } catch (error) {
            console.error('Error reading from localStorage:', error);
            return defaultValue;
        }
    }

    /**
     * Remove data from localStorage
     * @param {string} key - The key to remove
     * @returns {boolean} - True if successful, false if failed
     */
    static remove(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (error) {
            console.error('Error removing from localStorage:', error);
            return false;
        }
    }

    /**
     * Clear all localStorage data
     * @returns {boolean} - True if successful, false if failed
     */
    static clear() {
        try {
            localStorage.clear();
            return true;
        } catch (error) {
            console.error('Error clearing localStorage:', error);
            return false;
        }
    }

    /**
     * Check if a key exists in localStorage
     * @param {string} key - The key to check
     * @returns {boolean} - True if key exists, false otherwise
     */
    static exists(key) {
        return localStorage.getItem(key) !== null;
    }

    /**
     * Get all keys from localStorage
     * @returns {string[]} - Array of all keys
     */
    static getAllKeys() {
        try {
            return Object.keys(localStorage);
        } catch (error) {
            console.error('Error getting localStorage keys:', error);
            return [];
        }
    }

    /**
     * Get the size of localStorage in bytes (approximate)
     * @returns {number} - Approximate size in bytes
     */
    static getSize() {
        try {
            let total = 0;
            for (let key in localStorage) {
                if (localStorage.hasOwnProperty(key)) {
                    total += localStorage[key].length + key.length;
                }
            }
            return total;
        } catch (error) {
            console.error('Error calculating localStorage size:', error);
            return 0;
        }
    }
}

// Admin-specific localStorage keys (constants to avoid typos)
export const ADMIN_STORAGE_KEYS = {
    USER_ID: 'admin_user_id',
    USERNAME: 'admin_username', 
    EMAIL: 'admin_email',
    IS_ADMIN: 'admin_is_admin',
    LOGIN_TIME: 'admin_login_time'  // Renamed from AUTH_TOKEN to LOGIN_TIME
};

// Admin-specific helper functions
export const AdminStorage = {
    /**
     * Save admin login data to localStorage
     * @param {Object} adminData - Admin user data from login response
     */
    saveAdminLogin(adminData) {
        const loginTime = new Date().toISOString();
        
        LocalStorageUtil.set(ADMIN_STORAGE_KEYS.USER_ID, adminData.id);
        LocalStorageUtil.set(ADMIN_STORAGE_KEYS.USERNAME, adminData.username);
        LocalStorageUtil.set(ADMIN_STORAGE_KEYS.EMAIL, adminData.email);
        LocalStorageUtil.set(ADMIN_STORAGE_KEYS.IS_ADMIN, adminData.is_admin);
        LocalStorageUtil.set(ADMIN_STORAGE_KEYS.LOGIN_TIME, loginTime);
        
        console.log('Admin login data saved to localStorage');
    },

    /**
     * Get admin data from localStorage
     * @returns {Object|null} - Admin data object or null if not found
     */
    getAdminData() {
        const userId = LocalStorageUtil.get(ADMIN_STORAGE_KEYS.USER_ID);
        const username = LocalStorageUtil.get(ADMIN_STORAGE_KEYS.USERNAME);
        const email = LocalStorageUtil.get(ADMIN_STORAGE_KEYS.EMAIL);
        const isAdmin = LocalStorageUtil.get(ADMIN_STORAGE_KEYS.IS_ADMIN);
        const loginTime = LocalStorageUtil.get(ADMIN_STORAGE_KEYS.LOGIN_TIME);

        // Return null if essential data is missing
        if (!userId || !username || !email) {
            return null;
        }

        return {
            id: userId,
            username,
            email,
            is_admin: isAdmin,
            login_time: loginTime
        };
    },

    /**
     * Check if admin is currently logged in
     * @returns {boolean} - True if admin data exists and is valid
     */
    isAdminLoggedIn() {
        const adminData = this.getAdminData();
        return adminData !== null && adminData.is_admin === true;
    },

    /**
     * Clear all admin data from localStorage (logout)
     */
    clearAdminData() {
        LocalStorageUtil.remove(ADMIN_STORAGE_KEYS.USER_ID);
        LocalStorageUtil.remove(ADMIN_STORAGE_KEYS.USERNAME);
        LocalStorageUtil.remove(ADMIN_STORAGE_KEYS.EMAIL);
        LocalStorageUtil.remove(ADMIN_STORAGE_KEYS.IS_ADMIN);
        LocalStorageUtil.remove(ADMIN_STORAGE_KEYS.LOGIN_TIME);
        
        console.log('Admin data cleared from localStorage');
    },

    /**
     * Save auth token (using LOGIN_TIME key for session management)
     * @param {string} token - JWT or auth token
     */
    saveAuthToken(token) {
        LocalStorageUtil.set(ADMIN_STORAGE_KEYS.LOGIN_TIME, token);
    },

    /**
     * Get auth token (stored under LOGIN_TIME key)
     * @returns {string|null} - Auth token or null
     */
    getAuthToken() {
        return LocalStorageUtil.get(ADMIN_STORAGE_KEYS.LOGIN_TIME);
    }
};

export default LocalStorageUtil;
