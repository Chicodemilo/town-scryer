// ==============================================================================
// File:      frontend/src/pages/Help.jsx
// Purpose:   Quick-start guide for new users.
// Callers:   App.jsx (route: /help)
// Callees:   React, PageHeader.jsx, ContentCard.jsx
// Modified:  2026-06-05
// ==============================================================================
import React from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import PageContent from '../components/PageContent';
import ContentCard from '../components/ContentCard';

const STEPS = [
  {
    title: 'Create a Table',
    body: 'A Table is your campaign group. Head to Tables and click "New Table" — give it a name and a style preset (oil painting, comic, watercolor, etc). The style locks the look for every scene that follows.',
    cta: { label: 'Go to Tables', to: '/tables' },
  },
  {
    title: 'Add Player Characters',
    body: 'Inside the Table, add each player\'s character — name plus a short description or a reference image. This is what keeps the rogue looking like your rogue across scenes.',
  },
  {
    title: 'Open the Display screen',
    body: 'On whatever screen the players will see — a second monitor, a laptop you\'ve pointed at the table, an HDMI cable to a TV, or AirPlay/Chromecast to one — open the Display page and fullscreen the browser. That\'s the canvas the scene art paints onto.',
    cta: { label: 'Open Display', to: '/display' },
  },
  {
    title: 'Start a Session',
    body: 'Back on your DM laptop, hit Session → Start. The mic listens to your narration in ~30s chunks, detects scene changes, and triggers a new image. Tavern, dungeon, forest, boss room — it keeps up.',
    cta: { label: 'Start Session', to: '/session' },
  },
  {
    title: 'Stop and review',
    body: 'When the game wraps, stop the session. Every scene the table saw is saved to History so you can scroll back through the night\'s art (or share it with the players).',
    cta: { label: 'View History', to: '/history' },
  },
];

const TIPS = [
  'Quiet table = cleaner transcription. The mic struggles over loud music or three conversations at once.',
  'Image gen takes 5–30s — call out scene changes a beat earlier than you would normally.',
  'Stuck with an image you don\'t love? Thumbs-down regenerates the scene. Limited per session, so save it for the misses.',
  'Want to steer the AI mid-scene? Type a DM correction in the session view ("make the room bigger and lit by green torches") and the next image bakes it in.',
];

function Help() {
  return (
    <div>
      <PageHeader title="Quick Start" subtitle="Get your first session running in five steps." />

      <PageContent>
        <ol style={stepsList}>
          {STEPS.map((step, i) => (
            <li key={i} style={stepItem}>
              <ContentCard style={cardStyle}>
                <div style={stepHeader}>
                  <span style={stepNumber}>{i + 1}</span>
                  <h2 style={stepTitle}>{step.title}</h2>
                </div>
                <p style={stepBody}>{step.body}</p>
                {step.cta && (
                  <Link to={step.cta.to} style={ctaLink}>
                    {step.cta.label} →
                  </Link>
                )}
              </ContentCard>
            </li>
          ))}
        </ol>

        <ContentCard style={{ ...cardStyle, marginTop: 24 }}>
          <h2 style={tipsHeader}>Tips for a good run</h2>
          <ul style={tipsList}>
            {TIPS.map((tip, i) => (
              <li key={i} style={tipItem}>{tip}</li>
            ))}
          </ul>
        </ContentCard>
      </PageContent>
    </div>
  );
}

const stepsList = {
  listStyle: 'none',
  padding: 0,
  margin: 0,
};

const stepItem = { marginBottom: 16 };

const cardStyle = { padding: '20px 24px' };

const stepHeader = {
  display: 'flex',
  alignItems: 'center',
  gap: 12,
  marginBottom: 8,
};

const stepNumber = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 28,
  height: 28,
  borderRadius: '50%',
  backgroundColor: '#2563eb',
  color: '#ffffff',
  fontWeight: 600,
  fontSize: 14,
  flexShrink: 0,
};

const stepTitle = {
  margin: 0,
  fontSize: 18,
  color: 'var(--text-primary)',
};

const stepBody = {
  margin: '0 0 12px',
  color: 'var(--text-secondary)',
  lineHeight: 1.5,
  fontSize: 14,
};

const ctaLink = {
  display: 'inline-block',
  color: 'var(--brand-primary)',
  fontWeight: 500,
  fontSize: 14,
  textDecoration: 'none',
};

const tipsHeader = {
  margin: '0 0 12px',
  fontSize: 16,
  color: 'var(--text-primary)',
};

const tipsList = {
  margin: 0,
  paddingLeft: 18,
  color: 'var(--text-secondary)',
  fontSize: 14,
  lineHeight: 1.6,
};

const tipItem = { marginBottom: 6 };

export default Help;
