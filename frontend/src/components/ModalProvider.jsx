// ==============================================================================
// File:      frontend/src/components/ModalProvider.jsx
// Purpose:   Universal modal context. Mounts a single <Modal> at the app
//            root and exposes imperative helpers via hooks:
//              useConfirm()  -> (message, opts) => Promise<boolean>
//              useAlert()    -> (message, opts) => Promise<void>
//              useNotify()   -> (message, opts) => Promise<void>  (alias)
//            Wraps the existing <Modal> component so when we re-skin it
//            with D&D parchment/scroll styling later, every modal in the
//            app gets it for free.
// Callers:   App.jsx (provider), any page that needs a confirm/alert
// Callees:   React (Context), components/Modal.jsx
// Modified:  2026-06-07
// ==============================================================================
import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from 'react';
import Modal from './Modal';

const ModalCtx = createContext(null);

export function ModalProvider({ children }) {
  const [state, setState] = useState({ open: false });
  const resolverRef = useRef(null);

  const close = useCallback((result) => {
    setState((s) => ({ ...s, open: false }));
    // Settle the pending promise on close.
    const resolver = resolverRef.current;
    resolverRef.current = null;
    if (resolver) resolver(result);
  }, []);

  const confirm = useCallback((message, opts = {}) => {
    return new Promise((resolve) => {
      resolverRef.current = resolve;
      setState({
        open: true,
        kind: 'confirm',
        title: opts.title || 'Confirm',
        body: message,
        confirmText: opts.confirmText || 'Confirm',
        cancelText: opts.cancelText || 'Cancel',
        confirmDanger: !!opts.danger,
      });
    });
  }, []);

  const alert = useCallback((message, opts = {}) => {
    return new Promise((resolve) => {
      resolverRef.current = resolve;
      setState({
        open: true,
        kind: 'alert',
        title: opts.title || 'Notice',
        body: message,
        confirmText: opts.confirmText || 'OK',
      });
    });
  }, []);

  const value = useMemo(() => ({ confirm, alert, notify: alert }), [confirm, alert]);

  return (
    <ModalCtx.Provider value={value}>
      {children}
      <Modal
        open={!!state.open}
        title={state.title}
        cancelText={state.kind === 'alert' ? undefined : state.cancelText}
        confirmText={state.confirmText}
        confirmDanger={state.confirmDanger}
        onClose={() => close(state.kind === 'alert' ? undefined : false)}
        onConfirm={() => close(state.kind === 'alert' ? undefined : true)}
      >
        {state.body}
      </Modal>
    </ModalCtx.Provider>
  );
}

function useModalCtx() {
  const ctx = useContext(ModalCtx);
  if (!ctx) {
    throw new Error('useConfirm/useAlert must be used inside <ModalProvider>');
  }
  return ctx;
}

export function useConfirm() {
  return useModalCtx().confirm;
}

export function useAlert() {
  return useModalCtx().alert;
}

export function useNotify() {
  return useModalCtx().notify;
}

export default ModalProvider;
