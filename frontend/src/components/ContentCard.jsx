// ==============================================================================
// File:      frontend/src/components/ContentCard.jsx
// Purpose:   Standardized content card. Provides consistent padding, width,
//            and spacing for page content sections.
// Callers:   Dashboard.jsx, Items.jsx, Members.jsx, Activity.jsx, Profile.jsx,
//            Inbox.jsx, GroupDetail.jsx, GroupAdmin.jsx, GroupCreate.jsx,
//            JoinGroup.jsx
// Modified:  2026-04-22
// ==============================================================================
import React from 'react';

function ContentCard({ children, className, onClick }) {
  return (
    <div
      className={`content-card${className ? ` ${className}` : ''}`}
      onClick={onClick}
      style={onClick ? { cursor: 'pointer' } : undefined}
    >
      {children}
    </div>
  );
}

export default ContentCard;
