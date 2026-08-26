import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error('TALOS interface error:', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-dark px-6">
          <div className="max-w-md w-full text-center space-y-4 p-8 rounded-xl border border-subtle bg-white/[0.02]">
            <div className="w-12 h-12 rounded-full mx-auto flex items-center justify-center border bg-amber-500/10 border-amber-500/20 text-amber-400">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h1 className="text-base font-semibold text-text-primary">TALOS encountered an interface error.</h1>
            <p className="text-xs text-text-muted">
              Your repository operation has not been cancelled — any scan, patch, or verification already running
              continues server-side and can be checked after reloading.
            </p>
            <button className="btn btn-primary text-xs" onClick={() => window.location.reload()}>
              Reload Interface
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
