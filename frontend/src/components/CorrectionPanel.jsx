// ==============================================================================
// File:      frontend/src/components/CorrectionPanel.jsx
// Purpose:   Collapsible panel for DM scene corrections. Lets the DM add
//            short text corrections (e.g. "we're in a cave, not a forest")
//            that are sent to the backend and influence scene generation.
// Callers:   Session.jsx
// Callees:   api/session.js (addCorrection, getCorrections, deleteCorrection,
//            clearCorrections)
// Modified:  2026-06-01
// ==============================================================================
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  addCorrection,
  getCorrections,
  deleteCorrection,
  clearCorrections,
} from '../api/session';
import '../styles/corrections.css';

function CorrectionPanel({ sessionToken, isActive }) {
  const [corrections, setCorrections] = useState([]);
  const [text, setText] = useState('');
  const [expanded, setExpanded] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const inputRef = useRef(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  // Fetch existing corrections when the panel mounts with a token
  useEffect(() => {
    if (!sessionToken) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await getCorrections(sessionToken);
        if (cancelled || !mountedRef.current) return;
        setCorrections(data.corrections || data || []);
      } catch (_) {
        // Non-critical — panel starts empty
      }
    })();
    return () => { cancelled = true; };
  }, [sessionToken]);

  const handleAdd = useCallback(async () => {
    const trimmed = text.trim();
    if (!trimmed || !sessionToken || submitting) return;
    setSubmitting(true);
    try {
      const data = await addCorrection(sessionToken, trimmed);
      if (!mountedRef.current) return;
      // Backend may return the new correction or the full list
      if (data.corrections) {
        setCorrections(data.corrections);
      } else if (data.id) {
        setCorrections((prev) => [...prev, data]);
      } else {
        // Re-fetch to be safe
        const fresh = await getCorrections(sessionToken);
        if (mountedRef.current) setCorrections(fresh.corrections || fresh || []);
      }
      setText('');
      inputRef.current?.focus();
    } catch (_) {
      // Swallow — input stays so user can retry
    } finally {
      if (mountedRef.current) setSubmitting(false);
    }
  }, [text, sessionToken, submitting]);

  const handleDelete = useCallback(async (id) => {
    try {
      await deleteCorrection(id);
      if (mountedRef.current) {
        setCorrections((prev) => prev.filter((c) => c.id !== id));
      }
    } catch (_) {
      // Silent
    }
  }, []);

  const handleClearAll = useCallback(async () => {
    if (!sessionToken) return;
    try {
      await clearCorrections(sessionToken);
      if (mountedRef.current) setCorrections([]);
    } catch (_) {
      // Silent
    }
  }, [sessionToken]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleAdd();
      }
    },
    [handleAdd],
  );

  if (!isActive && corrections.length === 0) return null;

  const count = corrections.length;

  return (
    <div className="correction-panel">
      <button
        className="correction-panel__header"
        onClick={() => setExpanded((v) => !v)}
        type="button"
      >
        <span className="correction-panel__title">
          Scene Corrections
          {count > 0 && (
            <span className="correction-panel__badge">{count}</span>
          )}
        </span>
        <span className={`correction-panel__chevron${expanded ? ' correction-panel__chevron--open' : ''}`}>
          &#9660;
        </span>
      </button>

      {expanded && (
        <div className="correction-panel__body">
          {isActive && (
            <div className="correction-panel__input-row">
              <input
                ref={inputRef}
                className="correction-panel__input"
                type="text"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type a correction... (e.g. we're in a cave, not a forest)"
                disabled={submitting}
                maxLength={300}
              />
              <button
                className="correction-panel__add-btn"
                onClick={handleAdd}
                disabled={submitting || !text.trim()}
                type="button"
              >
                {submitting ? '...' : 'Add'}
              </button>
            </div>
          )}

          {count > 0 && (
            <div className="correction-panel__chips">
              {corrections.map((c) => (
                <span key={c.id} className="correction-chip">
                  <span className="correction-chip__text">{c.text}</span>
                  <button
                    className="correction-chip__remove"
                    onClick={() => handleDelete(c.id)}
                    type="button"
                    aria-label={`Remove correction: ${c.text}`}
                  >
                    &times;
                  </button>
                </span>
              ))}
            </div>
          )}

          {count >= 2 && (
            <button
              className="correction-panel__clear-link"
              onClick={handleClearAll}
              type="button"
            >
              Clear All
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default CorrectionPanel;
