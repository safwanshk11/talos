import React from 'react';
import { User, GitHubConnectionStatus } from '../types';
import { CheckCircle2, AlertCircle, Plus } from 'lucide-react';

interface HeaderProps {
  user: User | null;
  ghStatus: GitHubConnectionStatus | null;
  onOpenConnectModal: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  user,
  ghStatus,
  onOpenConnectModal,
}) => {
  return (
    <header className="h-16 border-b border-subtle bg-slate-950/60 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-10">
      {/* Title / Breadcrumb context */}
      <div className="flex items-center gap-3">
        <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
          v1.0.0-phase2
        </span>
        <span className="text-slate-500 text-sm">/</span>
        <span className="text-slate-300 font-medium text-sm">Repository Maintenance Control</span>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-4">
        {/* Connection status badge */}
        {ghStatus?.connected ? (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-emerald-500/30 text-xs font-medium text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>GitHub Connected (@{ghStatus.github_username})</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-xs font-medium text-amber-400">
            <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
            <span>GitHub Disconnected</span>
          </div>
        )}

        {/* Connect / Import Repository button */}
        <button
          onClick={onOpenConnectModal}
          className="btn btn-primary text-xs flex items-center gap-1.5"
        >
          <Plus className="w-4 h-4" />
          <span>Connect Repository</span>
        </button>

        {/* User profile avatar */}
        {user && (
          <div className="flex items-center gap-2 pl-2 border-l border-subtle">
            <img
              src={user.avatar_url || 'https://github.com/identicons/talos.png'}
              alt={user.username}
              className="w-7 h-7 rounded-full border border-slate-700 object-cover"
            />
            <span className="text-xs font-medium text-slate-300 font-mono">
              {user.username}
            </span>
          </div>
        )}
      </div>
    </header>
  );
};
