/**
 * File: Modal.jsx
 * Purpose: Reusable modal dialog with overlay, Escape-to-close, and scroll lock.
 *          Accepts title, body content, confirm/cancel actions, and optional
 *          danger action (e.g., delete button on the left side).
 * Callers: FeedbackModal.jsx, PollModal.jsx
 * Callees: (none)
 * Modified: 2026-04-22
 */
import React, { useEffect } from 'react';

function Modal({ open, onClose, onConfirm, title, children, confirmText = 'Confirm', cancelText = 'Cancel', confirmDanger = false, confirmDisabled = false, dangerAction, dangerText, wide = false }) {
  useEffect(() => {
    if (!open) return;
    const handleKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKey);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className={`modal${wide ? ' modal--wide' : ''}`} onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="modal-title">
        {title && <h2 className="modal__title" id="modal-title">{title}</h2>}
        <div className="modal__body">{children}</div>
        <div className="modal__actions">
          {dangerAction && (
            <button onClick={dangerAction} className="btn btn--danger modal__btn">{dangerText || 'Delete'}</button>
          )}
          <button onClick={onClose} className="btn btn--secondary modal__btn">{cancelText}</button>
          {onConfirm && (
            <button
              onClick={onConfirm}
              disabled={confirmDisabled}
              className={`btn modal__btn ${confirmDanger ? 'btn--danger' : 'btn--primary'}`}
            >
              {confirmText}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default Modal;
