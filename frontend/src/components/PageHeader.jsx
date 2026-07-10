// ==============================================================================
// File:      frontend/src/components/PageHeader.jsx
// Purpose:   Standardized page header. Consistent title, optional subtitle,
//            and optional right-side action across all pages.
// Callers:   Dashboard.jsx, Items.jsx, Members.jsx, Activity.jsx, Profile.jsx,
//            Inbox.jsx, GroupDetail.jsx, GroupAdmin.jsx, GroupCreate.jsx,
//            JoinGroup.jsx
// Modified:  2026-04-22
// ==============================================================================
import React from 'react';

function PageHeader({ title, subtitle, action }) {
  return (
    <div className="page-header">
      <div className="page-header__text">
        <h1 className="page-header__title">{title}</h1>
        {subtitle && <p className="page-header__subtitle">{subtitle}</p>}
      </div>
      {action && <div className="page-header__actions">{action}</div>}
    </div>
  );
}

export default PageHeader;
