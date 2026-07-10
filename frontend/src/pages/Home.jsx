/**
 * File: Home.jsx
 * Purpose: Landing page for guests, navigation hub for authenticated users.
 * Callers: App.jsx (route: /)
 * Callees: authStore.js
 * Modified: 2026-06-01
 */
import React, { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';
import '../styles/landing.css';

const APP_NAME = import.meta.env.VITE_APP_NAME || 'Town Scryer';

function Home() {
  const { user, isAuthenticated } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated() && user && !user.terms_accepted) {
      navigate('/terms');
    }
  }, [user]);

  if (isAuthenticated()) {
    return (
      <div>
        <div className="landing-hero">
          <div>
            <h1 className="landing-hero__title">{APP_NAME}</h1>
            <p className="landing-hero__subtitle">Welcome back, {user?.username}</p>
          </div>
        </div>
        <div className="home-cards">
          <Link to="/dashboard" className="home-card">
            <h3 className="home-card__title">Dashboard</h3>
            <p className="home-card__desc">View your dashboard</p>
          </Link>
          <Link to="/profile" className="home-card">
            <h3 className="home-card__title">Profile</h3>
            <p className="home-card__desc">Settings and preferences</p>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="landing-hero">
        <div>
          <h1 className="landing-hero__title">{APP_NAME}</h1>
          <p className="landing-hero__subtitle">Cinematic scenes for your tabletop, painted live as you play.</p>
        </div>
        <div className="landing-hero__actions">
          <Link to="/register" className="landing-hero__btn landing-hero__btn--primary">Get Started</Link>
          <Link to="/login" className="landing-hero__btn landing-hero__btn--secondary">Sign In</Link>
        </div>
      </div>

      <div className="landing-body">
        <div className="landing-intro">
          <h2 className="landing-intro__heading">Your campaign, on the wall.</h2>
          <p className="landing-intro__text">
            Town Scryer listens to your D&amp;D session and paints the scene on the screen behind you —
            tavern, dungeon, forest, boss room. The art keeps up while the story does.
          </p>
        </div>

        <div className="landing-footer">
          <p className="landing-footer__text">Town Scryer</p>
        </div>
      </div>
    </div>
  );
}

export default Home;
