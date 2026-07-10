// ==============================================================================
// File:      frontend/src/pages/Display.jsx
// Purpose:   Fullscreen display view for showing the latest scene image.
//            Designed for a secondary screen (monitor, laptop, or cast to a
//            TV via HDMI/AirPlay/Chromecast). Polls for new scenes and
//            crossfades between images. Supports JWT auth from localStorage
//            or a ?token= query parameter for unauthenticated display devices.
// Callers:   App.jsx (route: /display)
// Callees:   React, api/session.js
// Modified:  2026-06-01
// ==============================================================================
import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getLatestScene } from '../api/session';

const POLL_INTERVAL_MS = 3_000;
const APP_NAME = import.meta.env.VITE_APP_NAME || 'Town Scryer';

function Display() {
  const [searchParams] = useSearchParams();
  const [currentUrl, setCurrentUrl] = useState(null);
  const [nextUrl, setNextUrl] = useState(null);
  const [showNext, setShowNext] = useState(false);
  const [idle, setIdle] = useState(true);
  const [caption, setCaption] = useState(null);
  const [showCaptions, setShowCaptions] = useState(true);
  const [titleCard, setTitleCard] = useState(null);
  const [showDaubUpdates, setShowDaubUpdates] = useState(true);
  const [daubState, setDaubState] = useState('gathering');
  const pollTimerRef = useRef(null);
  const isMountedRef = useRef(true);

  // If a session token is provided via query param, stash it so the axios
  // interceptor can pick it up (only if no existing JWT is present).
  useEffect(() => {
    const queryToken = searchParams.get('token');
    if (queryToken && !localStorage.getItem('token')) {
      localStorage.setItem('token', queryToken);
    }
  }, [searchParams]);

  const poll = useCallback(async () => {
    try {
      const data = await getLatestScene();
      if (!isMountedRef.current) return;

      const imageUrl = data?.image_url || null;
      if (typeof data?.show_captions === 'boolean') {
        setShowCaptions(data.show_captions);
      }
      if (typeof data?.show_daub_updates === 'boolean') {
        setShowDaubUpdates(data.show_daub_updates);
      }
      if (typeof data?.daub_state === 'string') {
        setDaubState(data.daub_state);
      }
      if (data?.title_card) {
        setTitleCard(data.title_card);
      }

      if (!imageUrl) {
        setIdle(true);
        setCaption(null);
        return;
      }

      setIdle(false);

      // If image URL changed, preload first so the crossfade actually
      // crossfades (otherwise the new <img> starts loading at opacity:0,
      // pops in the moment it finishes, and the user sees a hard cut).
      if (imageUrl !== currentUrl) {
        const preload = new window.Image();
        preload.onload = () => {
          if (!isMountedRef.current) return;
          setNextUrl(imageUrl);
          setShowNext(true);
          setTimeout(() => {
            if (!isMountedRef.current) return;
            setCurrentUrl(imageUrl);
            setCaption(data?.caption || null);
            setShowNext(false);
            setNextUrl(null);
          }, 1100);
        };
        preload.onerror = () => {
          // Skip the fade if the image won't load; nothing to crossfade to.
        };
        preload.src = imageUrl;
      } else if (data?.caption && data.caption !== caption) {
        // Same image, new caption (rare — but cover it)
        setCaption(data.caption);
      }
    } catch (_) {
      // Silently continue polling on errors (network blips, no session, etc.)
      if (isMountedRef.current) {
        setIdle(true);
      }
    }
  }, [currentUrl]);

  useEffect(() => {
    isMountedRef.current = true;
    poll(); // initial fetch
    pollTimerRef.current = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      isMountedRef.current = false;
      clearInterval(pollTimerRef.current);
    };
  }, [poll]);

  return (
    <div className="display-root">
      {/* Current scene image */}
      {currentUrl && (
        <img
          key={currentUrl}
          src={currentUrl}
          alt=""
          className={`display-scene ${showNext ? 'display-scene--hidden' : 'display-scene--visible'}`}
        />
      )}

      {/* Next scene image (fades in on top) */}
      {nextUrl && (
        <img
          key={nextUrl}
          src={nextUrl}
          alt=""
          className={`display-scene ${showNext ? 'display-scene--visible' : 'display-scene--hidden'}`}
        />
      )}

      {/* Caption overlay (comic-book panel line) */}
      {showCaptions && caption && !idle && (
        <div className="display-caption">{caption}</div>
      )}

      {/* Daub status overlay — small italic, bottom-left, NOT part of the
          AI image. Suppressed on the idle title card (it already has its
          own listening pulse) — appears only over real scene images. */}
      {showDaubUpdates && !idle && (
        <div className="display-daub-status">
          {daubState === 'painting'
            ? `${(titleCard?.scryer_name) || 'Daub'}, The Painter is painting…`
            : `${(titleCard?.scryer_name) || 'Daub'}, The Painter is gathering information…`}
        </div>
      )}

      {/* Idle state */}
      {idle && (
        titleCard ? (
          <div className="display-titlecard">
            {titleCard.image_url && (
              <img
                className="display-titlecard__bg"
                src={titleCard.image_url}
                alt=""
              />
            )}
            <div className="display-titlecard__scrim" />
            <div className="display-titlecard__inner">
              <div className="display-titlecard__eyebrow">{APP_NAME}</div>
              <h1 className="display-titlecard__name">
                {titleCard.table_name || 'A new campaign'}
              </h1>
              <div className="display-titlecard__tags">
                {titleCard.game_type && (
                  <span className="display-titlecard__tag">{titleCard.game_type}</span>
                )}
                {titleCard.art_style && (
                  <span className="display-titlecard__tag">{titleCard.art_style}</span>
                )}
                {titleCard.rating && (
                  <span className="display-titlecard__tag display-titlecard__tag--rating">
                    {titleCard.rating}
                  </span>
                )}
              </div>
              {titleCard.characters && titleCard.characters.length > 0 && (
                <div className="display-titlecard__party">
                  <div className="display-titlecard__party-heading">The Party</div>
                  <ul className="display-titlecard__party-list">
                    {titleCard.characters.map((c, i) => (
                      <li key={i}>
                        <span className="display-titlecard__char-name">{c.name}</span>
                        {c.description && (
                          <span className="display-titlecard__char-desc"> — {c.description}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            {/* Listening pulse — small, offset overlay, NOT part of the AI image */}
            <div className="display-titlecard__pulse">
              {(titleCard.scryer_name || 'Daub')}, The Painter is gathering information…
            </div>
          </div>
        ) : (
          <div className="display-idle">
            <div className="display-idle__title">{APP_NAME}</div>
            <div className="display-idle__subtitle">Waiting for session</div>
          </div>
        )
      )}
    </div>
  );
}

export default Display;
