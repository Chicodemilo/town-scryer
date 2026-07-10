// ==============================================================================
// File:      frontend/src/components/PageContent.jsx
// Purpose:   Shared content wrapper. Sits under PageHeader on every page so
//            horizontal padding and bottom spacing stay identical across the
//            app.
// Callers:   Dashboard.jsx, Tables.jsx, TableDetail.jsx, History.jsx,
//            Profile.jsx, Help.jsx, JoinTable.jsx, Session.jsx
// Callees:   React
// Modified:  2026-06-05
// ==============================================================================
import React from 'react';

function PageContent({ children, className = '' }) {
  const cls = className ? `page-content ${className}` : 'page-content';
  return <div className={cls}>{children}</div>;
}

export default PageContent;
