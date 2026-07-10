/**
 * File: ErrorBoundary.jsx
 * Purpose: React Error Boundary. Catches runtime component crashes and shows
 *          a friendly fallback UI instead of a blank screen or raw error.
 * Callers: App.jsx (wraps AppShell)
 * Callees: React
 * Modified: 2026-04-22
 */
import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  handleReset = () => {
    this.setState({ hasError: false });
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <div className="error-boundary__card">
            <h1 className="error-boundary__title">Something went wrong</h1>
            <p className="error-boundary__message">
              An unexpected error occurred. Please try again.
            </p>
            <button onClick={this.handleReset} className="btn btn--primary">
              Return Home
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
