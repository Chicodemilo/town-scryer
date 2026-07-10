// ==============================================================================
// File:      frontend/src/components/AudioCapture.jsx
// Purpose:   Audio capture using MediaRecorder. Records the room mic in 30s
//            chunks, POSTs each chunk as a webm/opus blob to the server
//            (where Whisper transcribes it before scene analysis). Replaces
//            the old browser SpeechRecognition path which can't handle
//            distant, noisy, multi-voice TTRPG-table audio.
// Callers:   Session.jsx
// Callees:   React, api/session.js
// Modified:  2026-06-05
// ==============================================================================
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { sendAudioChunk } from '../api/session';

const STATUS = {
  IDLE: 'idle',
  LISTENING: 'listening',
  SENDING: 'sending',
  ERROR: 'error',
};

const STATUS_COLORS = {
  [STATUS.IDLE]: '#888',
  [STATUS.LISTENING]: '#22c55e',
  [STATUS.SENDING]: '#eab308',
  [STATUS.ERROR]: '#ef4444',
};

// 15s chunks halve worst-case latency between the DM saying "you arrive at
// the village" and the screen reacting. Doubles the Claude analysis call
// frequency but each call is cheap; reactivity wins easily outweigh the
// extra spend. Bigger chunks (30s+) made scene changes feel sluggish.
const CHUNK_INTERVAL_MS = 15_000;
const MIME_CANDIDATES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/mp4',
];

function pickMimeType() {
  if (typeof MediaRecorder === 'undefined') return null;
  for (const t of MIME_CANDIDATES) {
    try {
      if (MediaRecorder.isTypeSupported(t)) return t;
    } catch (_) { /* ignore */ }
  }
  return null;
}

function AudioCapture({ sessionToken, isListening, onSceneUpdate, onError, onChunkResponse }) {
  const [status, setStatus] = useState(STATUS.IDLE);
  const [errorMessage, setErrorMessage] = useState(null);

  const streamRef = useRef(null);
  const recorderRef = useRef(null);
  const chunkTimerRef = useRef(null);
  const mimeTypeRef = useRef(null);
  const isListeningRef = useRef(isListening);
  const isMountedRef = useRef(true);
  const sessionTokenRef = useRef(sessionToken);
  const sendingRef = useRef(false);

  useEffect(() => { isListeningRef.current = isListening; }, [isListening]);
  useEffect(() => { sessionTokenRef.current = sessionToken; }, [sessionToken]);

  // ---- Upload a recorded chunk to the server ----
  const uploadChunk = useCallback(async (blob) => {
    const token = sessionTokenRef.current;
    if (!token || !blob || blob.size === 0) return;

    sendingRef.current = true;
    if (isMountedRef.current) setStatus(STATUS.SENDING);

    try {
      const response = await sendAudioChunk(token, blob);
      if (isMountedRef.current) {
        setStatus(isListeningRef.current ? STATUS.LISTENING : STATUS.IDLE);
        if (response?.scene_changed && onSceneUpdate) {
          onSceneUpdate(response.scene);
        }
        onChunkResponse?.(response);
      }
    } catch (err) {
      if (isMountedRef.current) {
        setStatus(STATUS.ERROR);
        setErrorMessage('Failed to send audio chunk');
        onError?.(err);
      }
    } finally {
      sendingRef.current = false;
    }
  }, [onSceneUpdate, onError, onChunkResponse]);

  // ---- Start a fresh MediaRecorder. Each ondataavailable produces an
  //      independently-decodable chunk we can ship to Whisper. ----
  const startRecorder = useCallback(() => {
    const stream = streamRef.current;
    if (!stream) return;

    const mimeType = mimeTypeRef.current;
    let recorder;
    try {
      recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
    } catch (err) {
      setStatus(STATUS.ERROR);
      setErrorMessage('Failed to start audio recorder.');
      onError?.(err);
      return;
    }

    const localChunks = [];

    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) localChunks.push(e.data);
    };

    recorder.onstop = () => {
      if (localChunks.length === 0) return;
      const blob = new Blob(localChunks, { type: mimeType || 'audio/webm' });
      uploadChunk(blob);
    };

    recorder.onerror = (e) => {
      if (!isMountedRef.current) return;
      setStatus(STATUS.ERROR);
      setErrorMessage('Audio recorder error.');
      onError?.(e?.error || new Error('MediaRecorder error'));
    };

    recorderRef.current = recorder;
    recorder.start();

    if (isMountedRef.current) {
      setStatus(STATUS.LISTENING);
      setErrorMessage(null);
    }
  }, [uploadChunk, onError]);

  // ---- Stop current recorder; its onstop will upload the chunk. ----
  const cycleRecorder = useCallback(() => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      try { recorder.stop(); } catch (_) { /* ignore */ }
    }
    if (isListeningRef.current && isMountedRef.current) {
      // Tiny delay so onstop/ondataavailable fire before the new recorder
      // grabs the same stream.
      setTimeout(() => {
        if (isListeningRef.current && isMountedRef.current) startRecorder();
      }, 50);
    }
  }, [startRecorder]);

  // ---- Acquire mic + kick off the first recorder. ----
  const startCapture = useCallback(async () => {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      setStatus(STATUS.ERROR);
      setErrorMessage('Microphone API not available in this browser.');
      return;
    }

    mimeTypeRef.current = pickMimeType();
    if (!mimeTypeRef.current) {
      setStatus(STATUS.ERROR);
      setErrorMessage('Browser does not support audio recording.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      if (!isMountedRef.current) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      streamRef.current = stream;
      startRecorder();
    } catch (err) {
      setStatus(STATUS.ERROR);
      setErrorMessage(
        err?.name === 'NotAllowedError'
          ? 'Microphone access was denied. Allow it in browser settings and reload.'
          : 'Failed to access microphone.'
      );
      onError?.(err);
    }
  }, [startRecorder, onError]);

  // ---- Tear down the recorder + mic. ----
  const stopCapture = useCallback(() => {
    clearInterval(chunkTimerRef.current);
    chunkTimerRef.current = null;

    const recorder = recorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      try { recorder.stop(); } catch (_) { /* ignore */ }
    }
    recorderRef.current = null;

    const stream = streamRef.current;
    if (stream) {
      stream.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    if (isMountedRef.current) setStatus(STATUS.IDLE);
  }, []);

  // ---- React to isListening prop changes ----
  useEffect(() => {
    if (isListening) {
      startCapture();
      chunkTimerRef.current = setInterval(cycleRecorder, CHUNK_INTERVAL_MS);
    } else {
      // Final flush: stop current recorder (its onstop uploads), then teardown.
      const recorder = recorderRef.current;
      if (recorder && recorder.state !== 'inactive') {
        try { recorder.stop(); } catch (_) { /* ignore */ }
      }
      stopCapture();
    }

    return () => {
      clearInterval(chunkTimerRef.current);
      chunkTimerRef.current = null;
    };
  }, [isListening, startCapture, stopCapture, cycleRecorder]);

  // ---- Cleanup on unmount ----
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      stopCapture();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- Render ----
  const dotColor = STATUS_COLORS[status];
  const isPulsing = status === STATUS.LISTENING;

  return (
    <div style={containerStyle}>
      <span
        style={{
          ...dotStyle,
          backgroundColor: dotColor,
          animation: isPulsing ? 'audio-capture-pulse 1.5s ease-in-out infinite' : 'none',
          boxShadow: isPulsing ? `0 0 8px ${dotColor}` : 'none',
        }}
      />
      <span style={labelStyle}>
        {status === STATUS.IDLE && 'Not listening'}
        {status === STATUS.LISTENING && 'Listening...'}
        {status === STATUS.SENDING && 'Sending...'}
        {status === STATUS.ERROR && (errorMessage || 'Error')}
      </span>

      <style>{`
        @keyframes audio-capture-pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(1.3); }
        }
      `}</style>
    </div>
  );
}

const containerStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  padding: '8px 12px',
  borderRadius: '8px',
  background: 'var(--surface, #1a1a2e)',
  fontSize: '13px',
};

const dotStyle = {
  width: '10px',
  height: '10px',
  borderRadius: '50%',
  flexShrink: 0,
};

const labelStyle = {
  color: 'var(--text-primary, #fff)',
};

export default AudioCapture;
