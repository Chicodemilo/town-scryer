// ==============================================================================
// File:      frontend/src/pages/Session.jsx
// Purpose:   DM-facing session control page. Allows starting a game session
//            with configurable game type, art style, and gore level. Shows
//            live session controls, audio capture, and a scene feed grid.
//            Handles rate-limit feedback: force-pause banners, cooldown
//            countdown, and image progress bar.
// Callers:   App.jsx (route: /session)
// Callees:   React, api/session.js, api/preferences.js, AudioCapture.jsx
// Modified:  2026-06-01
// ==============================================================================
import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  startSession,
  pauseSession,
  resumeSession,
  endSession,
  sendHeartbeat,
  getCurrentSession,
  regenImage,
  getRegenInfo,
  deleteScene,
  changeImage,
  thumbsUpScene,
} from '../api/session';
import AudioCapture from '../components/AudioCapture';
import CorrectionPanel from '../components/CorrectionPanel';
import PageHeader from '../components/PageHeader';
import PageContent from '../components/PageContent';
import { useConfirm } from '../components/ModalProvider';
import { getPreferences } from '../api/preferences';
import { getTables, updateTable } from '../api/tables';

const HEARTBEAT_INTERVAL_MS = 60_000;
const SESSION_IMAGE_LIMIT = 120;
const SESSION_MAX_DURATION_HR = 8;
const COOLDOWN_SECONDS = 30;

const GAME_TYPES = [
  { value: 'Fantasy D&D', label: 'Fantasy D&D' },
  { value: 'Sci-Fi', label: 'Sci-Fi' },
  { value: 'Horror', label: 'Horror' },
  { value: 'Western', label: 'Western' },
  { value: 'Modern', label: 'Modern' },
  { value: 'Post-Apocalyptic', label: 'Post-Apocalyptic' },
];

const ART_STYLES = [
  { value: 'Oil Painting', label: 'Oil Painting', subtitle: 'rich, textured' },
  { value: 'Watercolor', label: 'Watercolor', subtitle: 'soft, dreamy washes' },
  { value: 'Comic Book', label: 'Comic Book', subtitle: 'bold lines, vivid colors' },
  { value: 'Pencil Sketch', label: 'Pencil Sketch', subtitle: 'hand-drawn feel' },
  { value: 'Digital Art', label: 'Digital Art', subtitle: 'modern, polished' },
];

const RATINGS = [
  { value: 'G', label: 'G', subtitle: 'all ages, no scary stuff' },
  { value: 'PG', label: 'PG', subtitle: 'family friendly' },
  { value: 'PG-13', label: 'PG-13', subtitle: 'mild violence' },
  { value: 'R', label: 'R', subtitle: 'graphic combat, mature themes' },
];

const FORCE_PAUSE_MESSAGES = {
  session_image_limit:
    "You've hit 120 images this session. Resume anytime to keep listening without new images.",
  max_duration:
    '8-hour session limit reached. Start a new session to continue.',
  cost_limit:
    "Session paused \u2014 you've been playing a while! Resume anytime.",
};

function formatDuration(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const parts = [];
  if (h > 0) parts.push(String(h).padStart(2, '0'));
  parts.push(String(m).padStart(2, '0'));
  parts.push(String(s).padStart(2, '0'));
  return parts.join(':');
}

function formatTimestamp(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function Session() {
  const confirm = useConfirm();

  // ---- Setup state ----
  const [gameType, setGameType] = useState('Fantasy D&D');
  const [artStyle, setArtStyle] = useState('Oil Painting');
  const [rating, setRating] = useState('PG-13');
  const [showCaptions, setShowCaptions] = useState(true);
  const [showDaubUpdates, setShowDaubUpdates] = useState(true);

  // ---- Table state ----
  const [tables, setTables] = useState([]);
  const [selectedTableId, setSelectedTableId] = useState('');

  // ---- Session state ----
  const [sessionToken, setSessionToken] = useState(null);
  const [sessionStatus, setSessionStatus] = useState(null); // 'active' | 'paused'
  const [sessionStartedAt, setSessionStartedAt] = useState(null);
  const [scenes, setScenes] = useState([]);
  const [elapsed, setElapsed] = useState(0);
  // Wall clock — always ticks, used so the DM can glance at real-world time.
  const [wallClock, setWallClock] = useState(() => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showEndConfirm, setShowEndConfirm] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);

  // ---- Rate-limit state ----
  const [forcePauseReason, setForcePauseReason] = useState(null);
  const [qualityScore, setQualityScore] = useState(0);
  // "New location detected" ping — short chyron-style tag shown next
  // to Audio Capture for ~4s when Claude reports a location change.
  const [locationPing, setLocationPing] = useState(null);
  const [cooldownRemaining, setCooldownRemaining] = useState(0);

  // ---- Regen state ----
  const [regenInfo, setRegenInfo] = useState(null); // {regen_count, regen_limit, remaining}
  const [regenLoading, setRegenLoading] = useState(false);
  const [regenOpen, setRegenOpen] = useState(false);

  // Change-Image: DM "give me a fresh take" — 30s cooldown, optional text.
  const [changeImageGuidance, setChangeImageGuidance] = useState('');
  const [changeImageBusy, setChangeImageBusy] = useState(false);
  const [changeImageCooldown, setChangeImageCooldown] = useState(0);

  // Cooldown ticker — 1s tick while > 0.
  useEffect(() => {
    if (changeImageCooldown <= 0) return;
    const id = setInterval(
      () => setChangeImageCooldown((s) => (s > 1 ? s - 1 : 0)),
      1000,
    );
    return () => clearInterval(id);
  }, [changeImageCooldown]);

  const handleChangeImage = useCallback(async () => {
    if (!sessionToken || changeImageBusy || changeImageCooldown > 0) return;
    setChangeImageBusy(true);
    try {
      const res = await changeImage(sessionToken, changeImageGuidance.trim() || undefined);
      if (isMountedRef.current && res?.scene) {
        setScenes((prev) => [res.scene, ...prev]);
      }
      if (isMountedRef.current) {
        setChangeImageGuidance('');
        setChangeImageCooldown(30);
      }
    } catch (err) {
      if (isMountedRef.current) {
        // 429 cooldown error from server → align our local timer.
        const remaining = err?.response?.data?.cooldown_remaining_s;
        if (typeof remaining === 'number') {
          setChangeImageCooldown(remaining);
        } else {
          setError(err?.response?.data?.error || 'Change Image failed.');
        }
      }
    } finally {
      if (isMountedRef.current) setChangeImageBusy(false);
    }
  }, [sessionToken, changeImageBusy, changeImageCooldown, changeImageGuidance]);
  const [regenGuidance, setRegenGuidance] = useState('');
  const [regenError, setRegenError] = useState(null);

  const heartbeatRef = useRef(null);
  const timerRef = useRef(null);
  const cooldownRef = useRef(null);
  const lastImageTimeRef = useRef(null);
  const isMountedRef = useRef(true);

  const isActive = sessionStatus === 'active';
  const isPaused = sessionStatus === 'paused';
  const hasSession = isActive || isPaused;

  // Pause-aware duration: accumulate ms while paused, subtract from wall
  // time when computing elapsed. State (not refs) so React re-renders the
  // tick effect on edges; no "reset" branch that can fire during transient
  // re-renders and zero the timer.
  const pauseStartRef = useRef(null);
  const [pauseAccumMs, setPauseAccumMs] = useState(0);

  useEffect(() => {
    if (isPaused) {
      if (pauseStartRef.current == null) pauseStartRef.current = Date.now();
    } else if (isActive && pauseStartRef.current != null) {
      const delta = Date.now() - pauseStartRef.current;
      pauseStartRef.current = null;
      setPauseAccumMs((p) => p + delta);
    }
    // Intentionally no "else" reset — that branch could fire mid-render
    // and zero a live session. handleStart resets pauseAccumMs explicitly.
  }, [isActive, isPaused]);

  // ---- Cooldown ticker ----
  const startCooldownTimer = useCallback(() => {
    clearInterval(cooldownRef.current);
    cooldownRef.current = setInterval(() => {
      if (!lastImageTimeRef.current) {
        setCooldownRemaining(0);
        clearInterval(cooldownRef.current);
        return;
      }
      const diff =
        COOLDOWN_SECONDS -
        Math.floor((Date.now() - lastImageTimeRef.current) / 1000);
      if (diff <= 0) {
        setCooldownRemaining(0);
        clearInterval(cooldownRef.current);
      } else {
        setCooldownRemaining(diff);
      }
    }, 1000);
  }, []);

  // ---- Check for existing session on mount ----
  useEffect(() => {
    isMountedRef.current = true;
    let cancelled = false;

    (async () => {
      let hasActiveSession = false;
      let activeToken = null;
      try {
        const data = await getCurrentSession();
        if (cancelled || !isMountedRef.current) return;

        if (data && data.session_token) {
          hasActiveSession = true;
          activeToken = data.session_token;
          setSessionToken(data.session_token);
          setSessionStatus(data.status || 'active');
          setSessionStartedAt(data.started_at || Date.now());
          if (data.scenes) setScenes(data.scenes);
          if (data.game_type) setGameType(data.game_type);
          if (data.art_style) setArtStyle(data.art_style);
          if (data.rating) setRating(data.rating);
          // Restore the linked-table id so the live captions toggle (and
          // any other per-table updateTable call) has a target after a
          // page refresh mid-session.
          if (data.table_id) setSelectedTableId(String(data.table_id));
        }
      } catch (_) {
        // No active session — that is fine
      }

      // When no active session, populate dropdowns from saved preferences
      if (!hasActiveSession && !cancelled && isMountedRef.current) {
        try {
          const prefs = await getPreferences();
          if (cancelled || !isMountedRef.current) return;
          if (prefs.game_type) setGameType(prefs.game_type);
          if (prefs.art_style) setArtStyle(prefs.art_style);
          if (prefs.rating) setRating(prefs.rating);
        } catch (_) {
          // Defaults are fine if preferences fetch fails
        }
      }

      // Fetch tables the user owns (for the optional table selector)
      if (!cancelled && isMountedRef.current) {
        try {
          const tablesData = await getTables();
          if (cancelled || !isMountedRef.current) return;
          const allTables = tablesData.tables || tablesData || [];
          // Only show tables where user is DM/owner
          const dmTables = allTables.filter(
            (t) => t.role === 'DM' || t.role === 'owner' || t.is_owner
          );
          setTables(dmTables);
        } catch (_) {
          // Tables fetch failure is non-critical
        }
      }

      // Fetch regen info if we have an active session
      if (hasActiveSession && activeToken && !cancelled && isMountedRef.current) {
        try {
          const info = await getRegenInfo(activeToken);
          if (!cancelled && isMountedRef.current) setRegenInfo(info);
        } catch (_) {
          // Non-critical
        }
      }

      if (!cancelled) setInitialLoading(false);
    })();

    return () => {
      cancelled = true;
      isMountedRef.current = false;
    };
  }, []);

  // ---- Per-table memory: when a table is selected, prefill its saved
  // settings. The page can still override before clicking Start. ----
  useEffect(() => {
    if (hasSession) return;
    if (!selectedTableId) return;
    const t = tables.find((x) => String(x.id) === String(selectedTableId));
    if (!t) return;
    if (t.game_type) setGameType(t.game_type);
    if (t.art_style) setArtStyle(t.art_style);
    if (t.rating) setRating(t.rating);
    if (typeof t.show_captions === 'boolean') setShowCaptions(t.show_captions);
    if (typeof t.show_daub_updates === 'boolean') setShowDaubUpdates(t.show_daub_updates);
  }, [selectedTableId, tables, hasSession]);

  // ---- Heartbeat ----
  useEffect(() => {
    if (!sessionToken || !isActive) {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = null;
      return;
    }

    heartbeatRef.current = setInterval(() => {
      sendHeartbeat(sessionToken).catch(() => {});
    }, HEARTBEAT_INTERVAL_MS);

    return () => {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = null;
    };
  }, [sessionToken, isActive]);

  // ---- Elapsed timer. Ticks while active; freezes when paused. ----
  useEffect(() => {
    if (!isActive || !sessionStartedAt) {
      clearInterval(timerRef.current);
      timerRef.current = null;
      return;
    }

    const tick = () => {
      const startMs =
        typeof sessionStartedAt === 'number'
          ? sessionStartedAt
          : new Date(sessionStartedAt).getTime();
      const activeMs = Date.now() - startMs - pauseAccumMs;
      setElapsed(Math.max(0, Math.floor(activeMs / 1000)));
    };

    tick();
    timerRef.current = setInterval(tick, 1000);

    return () => {
      clearInterval(timerRef.current);
      timerRef.current = null;
    };
  }, [isActive, sessionStartedAt, pauseAccumMs]);

  // ---- Thumbs-up a scene (positive quality signal) ----
  const handleThumbsUp = useCallback(async (sceneId) => {
    if (!sceneId) return;
    try {
      await thumbsUpScene(sceneId);
      if (isMountedRef.current) {
        setScenes((prev) => prev.map((s) =>
          s.id === sceneId ? { ...s, thumbs_up: true } : s
        ));
      }
    } catch (_) {
      // Silent — not worth interrupting flow for a feedback action.
    }
  }, []);

  // ---- Delete a scene from the feed ----
  const [deletingSceneId, setDeletingSceneId] = useState(null);
  const handleDeleteScene = useCallback(async (sceneId) => {
    if (!sceneId) return;
    const ok = await confirm(
      'Delete this scene from the feed? This cannot be undone.',
      { title: 'Delete Scene', confirmText: 'Delete', danger: true }
    );
    if (!ok) return;
    setDeletingSceneId(sceneId);
    try {
      await deleteScene(sceneId);
      if (isMountedRef.current) {
        setScenes((prev) => prev.filter((s) => s.id !== sceneId));
      }
    } catch (err) {
      if (isMountedRef.current) setError('Failed to delete scene.');
    } finally {
      if (isMountedRef.current) setDeletingSceneId(null);
    }
  }, []);

  // ---- Wall clock ticker (independent of session state) ----
  useEffect(() => {
    const id = setInterval(() => {
      setWallClock(
        new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      );
    }, 1000 * 15); // every 15s is plenty for HH:MM
    return () => clearInterval(id);
  }, []);

  // ---- Cleanup cooldown on unmount ----
  useEffect(() => {
    return () => clearInterval(cooldownRef.current);
  }, []);

  // ---- Handlers ----
  const handleStart = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const opts = {
        game_type: gameType,
        art_style: artStyle,
        rating: rating,
        show_captions: showCaptions,
      };
      if (selectedTableId) opts.table_id = selectedTableId;
      const data = await startSession(opts);
      if (!isMountedRef.current) return;
      setSessionToken(data.session_token);
      setSessionStatus('active');
      setSessionStartedAt(data.started_at || Date.now());
      setScenes([]);
      setElapsed(0);
      setPauseAccumMs(0);
      pauseStartRef.current = null;
      setForcePauseReason(null);
      setRegenInfo(null);
      setRegenOpen(false);
      setRegenGuidance('');
      // Fetch regen info for the new session
      try {
        const info = await getRegenInfo(data.session_token);
        if (isMountedRef.current) setRegenInfo(info);
      } catch (_) {}
    } catch (err) {
      if (!isMountedRef.current) return;
      setError(err?.response?.data?.error || 'Failed to start session.');
    } finally {
      if (isMountedRef.current) setLoading(false);
    }
  }, [gameType, artStyle, rating, selectedTableId]);

  const handlePause = useCallback(async () => {
    if (!sessionToken) return;
    try {
      await pauseSession(sessionToken);
      if (isMountedRef.current) setSessionStatus('paused');
    } catch (err) {
      if (isMountedRef.current) {
        setError(err?.response?.data?.error || 'Failed to pause session.');
      }
    }
  }, [sessionToken]);

  const handleResume = useCallback(async () => {
    if (!sessionToken) return;
    try {
      await resumeSession(sessionToken);
      if (isMountedRef.current) {
        setSessionStatus('active');
        setForcePauseReason(null);
      }
    } catch (err) {
      if (isMountedRef.current) {
        setError(err?.response?.data?.error || 'Failed to resume session.');
      }
    }
  }, [sessionToken]);

  const handleEnd = useCallback(async () => {
    if (!sessionToken) return;
    setShowEndConfirm(false);
    try {
      await endSession(sessionToken);
      if (isMountedRef.current) {
        setSessionToken(null);
        setSessionStatus(null);
        setSessionStartedAt(null);
        setElapsed(0);
        setForcePauseReason(null);
      }
    } catch (err) {
      if (isMountedRef.current) {
        setError(err?.response?.data?.error || 'Failed to end session.');
      }
    }
  }, [sessionToken]);

  const handleOpenDisplay = useCallback(() => {
    window.open('/display', '_blank', 'noopener');
  }, []);

  // ---- Live toggle for caption overlay on the Display. Persists to the
  // linked table; the Display picks it up on its next 3s poll. ----
  const handleToggleCaptions = useCallback(async () => {
    const next = !showCaptions;
    setShowCaptions(next);
    if (selectedTableId) {
      try {
        await updateTable(selectedTableId, { show_captions: next });
      } catch (_) {
        // Revert local state if the persist failed so UI stays truthful.
        if (isMountedRef.current) setShowCaptions(!next);
      }
    }
  }, [showCaptions, selectedTableId]);

  const handleToggleDaubUpdates = useCallback(async () => {
    const next = !showDaubUpdates;
    setShowDaubUpdates(next);
    if (selectedTableId) {
      try {
        await updateTable(selectedTableId, { show_daub_updates: next });
      } catch (_) {
        if (isMountedRef.current) setShowDaubUpdates(!next);
      }
    }
  }, [showDaubUpdates, selectedTableId]);

  const handleSceneUpdate = useCallback(
    (scene) => {
      if (!scene) return;
      setScenes((prev) => [scene, ...prev]);
      lastImageTimeRef.current = Date.now();
      startCooldownTimer();
    },
    [startCooldownTimer],
  );

  const handleAudioError = useCallback((err) => {
    console.error('AudioCapture error:', err);
  }, []);

  /** Handle rate-limit signals from chunk responses. */
  const handleChunkResponse = useCallback(
    (response) => {
      if (!response || !isMountedRef.current) return;

      // Track quality score for the auto-audit banner.
      if (typeof response.quality_score === 'number') {
        setQualityScore(response.quality_score);
      }

      // "New location detected" ping. Backend signals via
      // location_changed=true when Claude reports a real location
      // transition (different from the previous scene's location).
      // We show the short 3-5 word label for 4 seconds, then clear it.
      if (response.location_changed && response.location_label_short) {
        setLocationPing(response.location_label_short);
        setTimeout(() => {
          if (isMountedRef.current) setLocationPing(null);
        }, 4000);
      }

      // Force-pause: backend paused the session
      if (response.force_paused) {
        setSessionStatus('paused');
        setForcePauseReason(response.reason || 'cost_limit');
      }

      // Image skipped due to cooldown — kick off the countdown
      if (response.image_skipped && response.reason === 'cooldown') {
        lastImageTimeRef.current =
          lastImageTimeRef.current ||
          Date.now() - (COOLDOWN_SECONDS - 30) * 1000;
        startCooldownTimer();
      }
    },
    [startCooldownTimer],
  );

  // ---- Regen handlers ----
  const fetchRegenInfo = useCallback(async () => {
    if (!sessionToken) return;
    try {
      const info = await getRegenInfo(sessionToken);
      if (isMountedRef.current) setRegenInfo(info);
    } catch (_) {
      // Non-critical
    }
  }, [sessionToken]);

  const handleRegen = useCallback(async () => {
    if (!sessionToken || regenLoading) return;
    setRegenLoading(true);
    setRegenError(null);
    try {
      const result = await regenImage(sessionToken, regenGuidance.trim() || undefined);
      if (!isMountedRef.current) return;
      // Replace the latest scene (first in array) with the regenerated one
      if (result.scene) {
        setScenes((prev) => {
          if (prev.length === 0) return prev;
          const updated = [...prev];
          updated[0] = result.scene;
          return updated;
        });
      }
      setRegenOpen(false);
      setRegenGuidance('');
      // Refresh regen info after successful regen
      await fetchRegenInfo();
    } catch (err) {
      if (!isMountedRef.current) return;
      setRegenError(
        err?.response?.data?.error || 'Regeneration failed. Try again.'
      );
    } finally {
      if (isMountedRef.current) setRegenLoading(false);
    }
  }, [sessionToken, regenLoading, regenGuidance, fetchRegenInfo]);

  // ---- Derived values ----
  const imageCount = scenes.length;
  const imageProgress = Math.min(imageCount / SESSION_IMAGE_LIMIT, 1);
  const maxDurationSec = SESSION_MAX_DURATION_HR * 3600;

  // ---- Render ----
  if (initialLoading) {
    return (
      <div className="session-page">
        <PageHeader title="Session" />
        <p
          style={{
            color: 'var(--text-muted)',
            textAlign: 'center',
            padding: '48px 0',
          }}
        >
          Loading session...
        </p>
      </div>
    );
  }

  return (
    <div className="session-page">
      <PageHeader title="Session" subtitle="Live capture and scene generation." />
      <PageContent>
      {error && <div className="session-error">{error}</div>}

      {/* ---- Auto-Audit Notice — surfaces when quality_score crosses
              the audit threshold so the DM knows Daub is double-checking. ---- */}
      {hasSession && qualityScore >= 30 && (
        <div className="session-banner session-banner--audit">
          <div className="session-banner__content">
            <span className="session-banner__icon">★</span>
            <p className="session-banner__text">
              Sensing you're not digging the recent images. Daub is doubling down —
              auditing each new image before it hits the screen.
            </p>
          </div>
        </div>
      )}

      {/* ---- Force-Pause Banner ---- */}
      {forcePauseReason && hasSession && (
        <div className="session-banner session-banner--warning">
          <div className="session-banner__content">
            <span className="session-banner__icon">&#9888;</span>
            <p className="session-banner__text">
              {FORCE_PAUSE_MESSAGES[forcePauseReason] ||
                'Session paused due to a limit.'}
            </p>
          </div>
          {forcePauseReason !== 'max_duration' && (
            <button
              className="btn btn--resume btn--small"
              onClick={handleResume}
            >
              Resume
            </button>
          )}
        </div>
      )}

      {/* ---- Setup (no active session) ---- */}
      {!hasSession && (
        <div className="session-setup">
          <h2>New Session</h2>

          {tables.length > 0 && (
            <>
              <div className="session-setup__field session-setup__field--primary">
                <label htmlFor="session-table">Table</label>
                <span className="session-setup__hint">
                  The campaign group this session is part of
                </span>
                <select
                  id="session-table"
                  value={selectedTableId}
                  onChange={(e) => setSelectedTableId(e.target.value)}
                >
                  <option value="">None</option>
                  {tables.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </div>
              <hr className="session-setup__divider" />
            </>
          )}

          <div className="session-setup__fields">
            <div className="session-setup__field">
              <label htmlFor="game-type">Game Type</label>
              <span className="session-setup__hint">
                Choose the genre for AI-generated scene art
              </span>
              <select
                id="game-type"
                value={gameType}
                onChange={(e) => setGameType(e.target.value)}
              >
                {GAME_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="session-setup__field">
              <label htmlFor="art-style">Art Style</label>
              <span className="session-setup__hint">
                Visual style applied to every generated scene
              </span>
              <select
                id="art-style"
                value={artStyle}
                onChange={(e) => setArtStyle(e.target.value)}
              >
                {ART_STYLES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label} — {s.subtitle}
                  </option>
                ))}
              </select>
            </div>

            <div className="session-setup__field">
              <label htmlFor="rating">Rating</label>
              <span className="session-setup__hint">
                Caps the intensity of the generated imagery
              </span>
              <select
                id="rating"
                value={rating}
                onChange={(e) => setRating(e.target.value)}
              >
                {RATINGS.map((g) => (
                  <option key={g.value} value={g.value}>
                    {g.label} — {g.subtitle}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <label className="session-setup__toggle">
            <input
              type="checkbox"
              checked={showCaptions}
              onChange={(e) => setShowCaptions(e.target.checked)}
            />
            <span>
              Show captions on the display
              <span className="session-setup__hint" style={{ display: 'block', marginTop: 2 }}>
                Punchy comic-book line under each image on the Display screen
              </span>
            </span>
          </label>

          <div className="session-setup__actions">
            <button
              className="session-setup__start-btn"
              onClick={handleStart}
              disabled={loading}
            >
              {loading ? 'Starting...' : 'Start Session'}
            </button>
          </div>
        </div>
      )}

      {/* ---- Session Controls ---- */}
      {hasSession && (
        <>
          <div className="session-controls">
            <div className="session-controls__top-row">
              <span
                className={`session-controls__badge ${
                  isActive
                    ? 'session-controls__badge--active'
                    : 'session-controls__badge--paused'
                }`}
              >
                <span className="session-controls__badge-dot" />
                {isActive ? 'Active' : 'Paused'}
              </span>

              <div className="session-controls__buttons">
                {isActive ? (
                  <button className="btn btn--pause" onClick={handlePause}>
                    Pause
                  </button>
                ) : (
                  <button className="btn btn--resume" onClick={handleResume}>
                    Resume
                  </button>
                )}
                <button
                  className="btn btn--end"
                  onClick={() => setShowEndConfirm(true)}
                >
                  End Session
                </button>
                <button
                  className="btn btn--display"
                  onClick={handleOpenDisplay}
                >
                  Open Display View
                </button>
                <label
                  className="session-controls__toggle"
                  title="Toggle caption overlay on the Display"
                >
                  <input
                    type="checkbox"
                    checked={showCaptions}
                    onChange={handleToggleCaptions}
                  />
                  <span>Captions</span>
                </label>
                <label
                  className="session-controls__toggle"
                  title="Show 'Daub the Painter is gathering / painting…' on the Display"
                >
                  <input
                    type="checkbox"
                    checked={showDaubUpdates}
                    onChange={handleToggleDaubUpdates}
                  />
                  <span>See Daub's Updates</span>
                </label>
              </div>
            </div>

            <div className="session-stats">
              {/* Wall clock */}
              <div className="session-stat">
                <p className="session-stat__value">{wallClock}</p>
                <p className="session-stat__label">Time of day</p>
              </div>

              {/* Duration with /8hr context */}
              <div className="session-stat">
                <p className="session-stat__value">
                  {formatDuration(elapsed)}
                </p>
                <div className="session-stat__bar-wrap">
                  <div
                    className="session-stat__bar"
                    style={{
                      width: `${Math.min((elapsed / maxDurationSec) * 100, 100)}%`,
                    }}
                  />
                </div>
                <p className="session-stat__label">
                  Duration / {SESSION_MAX_DURATION_HR}hr
                </p>
              </div>

              {/* Image count with progress bar */}
              <div className="session-stat">
                <p className="session-stat__value">
                  {imageCount} / {SESSION_IMAGE_LIMIT}
                </p>
                <div className="session-stat__bar-wrap">
                  <div
                    className={`session-stat__bar${imageProgress >= 0.9 ? ' session-stat__bar--danger' : ''}`}
                    style={{ width: `${imageProgress * 100}%` }}
                  />
                </div>
                <p className="session-stat__label">Images</p>
              </div>

              {/* Listening status */}
              <div className="session-stat">
                <p className="session-stat__value">
                  {isActive ? 'On' : 'Off'}
                </p>
                <p className="session-stat__label">Listening</p>
              </div>

              {/* Cooldown indicator */}
              {cooldownRemaining > 0 && (
                <div className="session-stat session-stat--cooldown">
                  <p className="session-stat__value session-stat__value--cooldown">
                    {cooldownRemaining}s
                  </p>
                  <p className="session-stat__label">Next image in</p>
                </div>
              )}
            </div>
          </div>

          {/* ---- Audio Capture + Location Ping (both = "Daub heard X") ---- */}
          <div className="session-audio">
            <h3>Audio Capture</h3>
            <AudioCapture
              sessionToken={sessionToken}
              isListening={isActive}
              onSceneUpdate={handleSceneUpdate}
              onError={handleAudioError}
              onChunkResponse={handleChunkResponse}
            />
            {/* "New location detected" ping — sibling block at the same
                visual level as Audio Capture, intentionally so the DM
                groups both as "Daub's listening signals." Fades out
                after 4s via state cleared in handleChunkResponse. */}
            <div
              className="location-ping"
              style={{
                marginTop: 12,
                padding: '8px 12px',
                borderRadius: 6,
                background: locationPing ? 'rgba(74, 222, 128, 0.12)' : 'transparent',
                border: locationPing
                  ? '1px solid rgba(74, 222, 128, 0.55)'
                  : '1px solid transparent',
                color: '#a7f3d0',
                fontSize: 13,
                opacity: locationPing ? 1 : 0,
                transition: 'opacity 320ms ease, background 320ms ease, border-color 320ms ease',
                minHeight: 32,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <span aria-hidden="true">📍</span>
              <span style={{ fontStyle: 'italic' }}>
                {locationPing || ''}
              </span>
            </div>
          </div>

          {/* ---- Corrections ---- */}
          <CorrectionPanel
            sessionToken={sessionToken}
            isActive={isActive}
          />

          {/* ---- Change-Image (big button + optional guidance) ---- */}
          <div className="change-image-bar">
            <input
              type="text"
              className="change-image-bar__input"
              placeholder="Optional guidance (e.g. 'wider angle', 'night now', 'closer to the river')"
              value={changeImageGuidance}
              onChange={(e) => setChangeImageGuidance(e.target.value)}
              disabled={changeImageBusy}
            />
            <button
              className="change-image-bar__btn"
              onClick={handleChangeImage}
              disabled={changeImageBusy || changeImageCooldown > 0}
            >
              {changeImageBusy
                ? 'Painting…'
                : changeImageCooldown > 0
                  ? `Ready in ${changeImageCooldown}s`
                  : 'Make A New Image'}
            </button>
          </div>

          {/* ---- Scene Feed ---- */}
          <div className="session-scenes">
            <h3>Scene Feed</h3>
            {scenes.length === 0 ? (
              <p className="session-scenes__empty">
                No scenes generated yet. Scenes will appear here as you
                narrate.
              </p>
            ) : (
              <div className="session-scenes__grid">
                {scenes.map((scene, i) => {
                  const isLatest = i === 0;
                  const regenRemaining = regenInfo?.remaining ?? null;
                  const regenLimit = regenInfo?.regen_limit ?? null;
                  const canRegen = regenRemaining === null || regenRemaining > 0;

                  return (
                    <div key={scene.id || i} className="scene-card">
                      <div className="scene-card__image-wrap">
                        {scene.image_url && (
                          <img
                            className="scene-card__image"
                            src={scene.image_url}
                            alt={scene.description || 'Scene'}
                            loading="lazy"
                          />
                        )}
                        {/* Loading overlay while regenerating */}
                        {isLatest && regenLoading && (
                          <div className="scene-card__regen-overlay">
                            <div className="scene-card__regen-spinner" />
                          </div>
                        )}
                        {/* Regen button — only on latest scene */}
                        {isLatest && !regenLoading && (
                          <button
                            className="scene-card__regen-btn"
                            title={canRegen ? 'Regenerate this scene' : 'No regens remaining'}
                            disabled={!canRegen}
                            onClick={() => {
                              setRegenOpen((prev) => !prev);
                              setRegenError(null);
                            }}
                          >
                            &#x21bb;
                          </button>
                        )}
                        {/* Thumbs-up — positive quality signal */}
                        <button
                          className={`scene-card__thumbs-btn${scene.thumbs_up ? ' scene-card__thumbs-btn--active' : ''}`}
                          title={scene.thumbs_up ? 'You liked this scene' : 'Thumbs up — this one is good'}
                          disabled={scene.thumbs_up}
                          onClick={() => handleThumbsUp(scene.id)}
                        >
                          👍
                        </button>
                        {/* Delete button — remove a bad scene from the feed */}
                        <button
                          className="scene-card__delete-btn"
                          title="Delete this scene"
                          disabled={deletingSceneId === scene.id}
                          onClick={() => handleDeleteScene(scene.id)}
                        >
                          {deletingSceneId === scene.id ? '…' : '×'}
                        </button>
                      </div>

                      <div className="scene-card__body">
                        {scene.description && (
                          <p className="scene-card__description">
                            {scene.description}
                          </p>
                        )}
                        <p className="scene-card__time">
                          {formatTimestamp(scene.created_at || scene.timestamp)}
                        </p>

                        {/* Regen inline UI — only on latest scene */}
                        {isLatest && regenOpen && !regenLoading && (
                          <div className="scene-card__regen-panel">
                            <input
                              className="scene-card__regen-input"
                              type="text"
                              placeholder="What should change? (optional)"
                              value={regenGuidance}
                              onChange={(e) => setRegenGuidance(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleRegen();
                              }}
                            />
                            <button
                              className="scene-card__regen-submit"
                              onClick={handleRegen}
                              disabled={!canRegen}
                            >
                              Regenerate
                            </button>
                            {regenRemaining !== null && regenLimit !== null && (
                              <span className="scene-card__regen-count">
                                {regenRemaining}/{regenLimit} remaining
                              </span>
                            )}
                            {regenError && (
                              <span className="scene-card__regen-error">
                                {regenError}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}
      </PageContent>

      {/* ---- End Session Confirmation ---- */}
      {showEndConfirm && (
        <div
          className="session-confirm-overlay"
          onClick={() => setShowEndConfirm(false)}
        >
          <div
            className="session-confirm-dialog"
            onClick={(e) => e.stopPropagation()}
          >
            <h3>End Session?</h3>
            <p>
              This will stop audio capture and end the current game session.
              This action cannot be undone.
            </p>
            <div className="session-confirm-dialog__actions">
              <button
                className="btn btn--cancel"
                onClick={() => setShowEndConfirm(false)}
              >
                Cancel
              </button>
              <button className="btn btn--end" onClick={handleEnd}>
                End Session
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Session;
