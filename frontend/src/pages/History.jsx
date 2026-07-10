// ==============================================================================
// File:      frontend/src/pages/History.jsx
// Purpose:   Session history page. Shows a paginated list of past sessions with
//            accordion-style expansion to view scene galleries. Includes a
//            lightbox for viewing full-size scene images.
// Callers:   App.jsx (route: /history)
// Callees:   React, api/history.js, PageHeader.jsx
// Modified:  2026-06-01
// ==============================================================================
import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { getSessions, getSessionScenes, deleteSession } from '../api/history';
import { deleteScene } from '../api/session';
import PageHeader from '../components/PageHeader';
import PageContent from '../components/PageContent';
import { useConfirm } from '../components/ModalProvider';

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString(undefined, {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return '--';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

const SESSIONS_PER_PAGE = 20;
const SCENES_PER_PAGE = 50;

function History() {
  const confirm = useConfirm();
  const [sessions, setSessions] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Accordion: which session id is expanded
  const [expandedId, setExpandedId] = useState(null);

  // Scene data per session: { [sessionId]: { scenes, page, totalPages, loading } }
  const [sceneData, setSceneData] = useState({});

  // Lightbox
  const [lightbox, setLightbox] = useState(null); // { image_url, description }

  // Scene delete state
  const [deletingSceneId, setDeletingSceneId] = useState(null);
  // Session delete state
  const [deletingSessionId, setDeletingSessionId] = useState(null);

  // ---- Delete an entire past session ----
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const handleDeleteSession = useCallback(async (sessionId, e) => {
    if (e) e.stopPropagation(); // don't toggle the accordion
    const ok = await confirm(
      'Delete this entire session and all its scenes? This cannot be undone.',
      { title: 'Delete Session', confirmText: 'Delete', danger: true }
    );
    if (!ok) return;
    setDeletingSessionId(sessionId);
    try {
      await deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      setSceneData((prev) => {
        const next = { ...prev };
        delete next[sessionId];
        return next;
      });
      if (expandedId === sessionId) setExpandedId(null);
    } catch (_) {
      setError('Failed to delete session.');
    } finally {
      setDeletingSessionId(null);
    }
  }, [expandedId]);

  // ---- Delete a scene from a past session ----
  const handleDeleteScene = useCallback(async (sessionId, sceneId, e) => {
    if (e) e.stopPropagation(); // don't trigger lightbox open
    if (!sceneId) return;
    const ok = await confirm(
      'Delete this scene from history? This cannot be undone.',
      { title: 'Delete Scene', confirmText: 'Delete', danger: true }
    );
    if (!ok) return;
    setDeletingSceneId(sceneId);
    try {
      await deleteScene(sceneId);
      setSceneData((prev) => {
        const s = prev[sessionId];
        if (!s) return prev;
        return {
          ...prev,
          [sessionId]: {
            ...s,
            scenes: s.scenes.filter((sc) => sc.id !== sceneId),
          },
        };
      });
    } catch (_) {
      setError('Failed to delete scene.');
    } finally {
      setDeletingSceneId(null);
    }
  }, []);

  // ---- Fetch sessions ----
  const fetchSessions = useCallback(async (p) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getSessions(p, SESSIONS_PER_PAGE);
      setSessions(data.sessions || []);
      setTotalPages(data.total_pages || 1);
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to load sessions.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions(page);
  }, [page, fetchSessions]);

  // ---- Fetch scenes for a session ----
  const fetchScenes = useCallback(async (sessionId, scenePage = 1) => {
    setSceneData((prev) => ({
      ...prev,
      [sessionId]: {
        ...prev[sessionId],
        loading: true,
      },
    }));
    try {
      const data = await getSessionScenes(sessionId, scenePage, SCENES_PER_PAGE);
      setSceneData((prev) => ({
        ...prev,
        [sessionId]: {
          scenes: data.scenes || [],
          page: scenePage,
          totalPages: data.total_pages || 1,
          loading: false,
        },
      }));
    } catch {
      setSceneData((prev) => ({
        ...prev,
        [sessionId]: {
          ...prev[sessionId],
          scenes: prev[sessionId]?.scenes || [],
          loading: false,
        },
      }));
    }
  }, []);

  // ---- Toggle accordion ----
  const toggleSession = useCallback(
    (sessionId) => {
      if (expandedId === sessionId) {
        setExpandedId(null);
        return;
      }
      setExpandedId(sessionId);
      // Fetch scenes if not already loaded
      if (!sceneData[sessionId]) {
        fetchScenes(sessionId, 1);
      }
    },
    [expandedId, sceneData, fetchScenes]
  );

  // ---- Scene page navigation ----
  const handleScenePage = useCallback(
    (sessionId, newPage) => {
      fetchScenes(sessionId, newPage);
    },
    [fetchScenes]
  );

  // ---- Lightbox ----
  const openLightbox = useCallback((scene) => {
    setLightbox(scene);
  }, []);

  const closeLightbox = useCallback(() => {
    setLightbox(null);
  }, []);

  // Close lightbox on Escape
  useEffect(() => {
    if (!lightbox) return;
    const handleKey = (e) => {
      if (e.key === 'Escape') closeLightbox();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [lightbox, closeLightbox]);

  // ---- Render ----
  return (
    <div className="history-page">
      <PageHeader title="Session History" />

      <PageContent>
      {error && <div className="history-error">{error}</div>}

      {loading && <p className="history-loading">Loading sessions...</p>}

      {!loading && sessions.length === 0 && !error && (
        <div className="history-empty">
          <h2 className="history-empty__title">No sessions yet.</h2>
          <p className="history-empty__text">
            Start your first session to see it here!
          </p>
          <Link to="/session" className="history-empty__link">
            Start a session
          </Link>
        </div>
      )}

      {!loading &&
        sessions.map((session) => {
          const isOpen = expandedId === session.id;
          const sd = sceneData[session.id];

          return (
            <div
              key={session.id}
              className={`history-session${isOpen ? ' history-session--expanded' : ''}`}
            >
              {/* Session header (click to toggle) */}
              <div
                className="history-session__header"
                onClick={() => toggleSession(session.id)}
              >
                <span
                  className={`history-session__chevron${isOpen ? ' history-session__chevron--open' : ''}`}
                >
                  &#9654;
                </span>
                <span className="history-session__date">
                  {formatDate(session.started_at || session.created_at)}
                </span>
                <div className="history-session__meta">
                  {session.duration != null && (
                    <span className="history-session__tag">
                      <strong>{formatDuration(session.duration)}</strong>
                    </span>
                  )}
                  {session.image_count != null && (
                    <span className="history-session__tag">
                      {session.image_count} image{session.image_count !== 1 ? 's' : ''}
                    </span>
                  )}
                  {session.game_type && (
                    <span className="history-session__tag">{session.game_type}</span>
                  )}
                  {session.art_style && (
                    <span className="history-session__tag">{session.art_style}</span>
                  )}
                  {session.rating && (
                    <span className="history-session__tag">Rating: {session.rating}</span>
                  )}
                  <button
                    className="history-session__delete-btn"
                    title="Delete this entire session"
                    disabled={deletingSessionId === session.id}
                    onClick={(e) => handleDeleteSession(session.id, e)}
                  >
                    {deletingSessionId === session.id ? '…' : 'Delete'}
                  </button>
                </div>
              </div>

              {/* Accordion body */}
              <div className={`history-session__body${isOpen ? ' history-session__body--open' : ''}`}>
                <div className="history-session__body-inner">
                  {isOpen && (
                    <div className="history-session__content">
                      {sd?.loading && (
                        <p className="history-scenes__loading">Loading scenes...</p>
                      )}

                      {sd && !sd.loading && sd.scenes.length === 0 && (
                        <p className="history-scenes__empty">
                          No scenes were generated in this session.
                        </p>
                      )}

                      {sd && !sd.loading && sd.scenes.length > 0 && (
                        <>
                          <div className="history-scenes__grid">
                            {sd.scenes.map((scene, i) => (
                              <div
                                key={scene.id || i}
                                className="history-scene-thumb"
                                onClick={() => openLightbox(scene)}
                              >
                                {scene.image_url && (
                                  <img
                                    className="history-scene-thumb__image"
                                    src={scene.image_url}
                                    alt={scene.caption || scene.scene_description || 'Scene'}
                                    loading="lazy"
                                  />
                                )}
                                {(scene.caption || scene.scene_description) && (
                                  <p className="history-scene-thumb__desc">
                                    {scene.caption || scene.scene_description}
                                  </p>
                                )}
                                <button
                                  className="history-scene-thumb__delete-btn"
                                  title="Delete this scene"
                                  disabled={deletingSceneId === scene.id}
                                  onClick={(e) => handleDeleteScene(session.id, scene.id, e)}
                                >
                                  {deletingSceneId === scene.id ? '…' : '×'}
                                </button>
                              </div>
                            ))}
                          </div>

                          {sd.totalPages > 1 && (
                            <div className="history-scenes__pagination">
                              <button
                                disabled={sd.page <= 1}
                                onClick={() => handleScenePage(session.id, sd.page - 1)}
                              >
                                Prev
                              </button>
                              <span className="pagination__info">
                                Page {sd.page} of {sd.totalPages}
                              </span>
                              <button
                                disabled={sd.page >= sd.totalPages}
                                onClick={() => handleScenePage(session.id, sd.page + 1)}
                              >
                                Next
                              </button>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}

      {/* Sessions pagination */}
      {!loading && totalPages > 1 && (
        <div className="pagination">
          <button
            className="pagination__btn"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </button>
          <span className="pagination__info">
            Page {page} of {totalPages}
          </span>
          <button
            className="pagination__btn"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      )}

      {/* Lightbox */}
      {lightbox && (
        <div className="history-lightbox" onClick={closeLightbox}>
          <button
            className="history-lightbox__close"
            onClick={closeLightbox}
            aria-label="Close"
          >
            &times;
          </button>
          <div
            className="history-lightbox__card"
            onClick={(e) => e.stopPropagation()}
          >
            {lightbox.image_url && (
              <img
                className="history-lightbox__image"
                src={lightbox.image_url}
                alt={lightbox.caption || lightbox.scene_description || 'Scene'}
              />
            )}
            {(lightbox.caption || lightbox.scene_description) && (
              <div className="history-lightbox__body">
                {lightbox.caption && (
                  <p className="history-lightbox__caption">{lightbox.caption}</p>
                )}
                {lightbox.scene_description && (
                  <p className="history-lightbox__desc">{lightbox.scene_description}</p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
      </PageContent>
    </div>
  );
}

export default History;
