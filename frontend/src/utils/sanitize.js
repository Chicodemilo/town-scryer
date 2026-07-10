/**
 * File: sanitize.js
 * Purpose: Lightweight input sanitization for API submission. Strips HTML tags,
 *          trims whitespace, and enforces length limits without HTML-encoding
 *          (React handles display escaping). Use on all user text before API calls.
 * Callers: All pages/components with form submissions
 * Callees: (none — pure functions)
 * Modified: 2026-04-06
 */

/**
 * Strip all HTML tags from a string.
 * Also removes javascript: and data: protocol URLs embedded in text.
 */
export function stripTags(str) {
  if (typeof str !== 'string') return str;
  let cleaned = str;
  // Remove script/style blocks entirely (content + tags)
  cleaned = cleaned.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
  cleaned = cleaned.replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '');
  // Remove all remaining HTML tags
  cleaned = cleaned.replace(/<[^>]*>/g, '');
  // Remove dangerous protocol prefixes
  cleaned = cleaned.replace(/javascript:/gi, '');
  cleaned = cleaned.replace(/data:(?!image\/)/gi, '');
  return cleaned;
}

/**
 * Clean user input for API submission.
 * Trims whitespace, strips HTML tags, enforces max length.
 * Does NOT HTML-encode — React handles that at render time.
 *
 * @param {string} value - Raw user input
 * @param {number} [maxLength=1000] - Maximum character length
 * @returns {string} Sanitized value safe for API submission
 */
export function clean(value, maxLength = 1000) {
  if (typeof value !== 'string') return value;
  let result = value.trim();
  result = stripTags(result);
  if (result.length > maxLength) {
    result = result.substring(0, maxLength);
  }
  return result;
}
