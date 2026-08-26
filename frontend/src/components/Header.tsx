import React from 'react';
import { User, GitHubConnectionStatus } from '../types';
import { CheckCircle2, AlertCircle, Plus } from 'lucide-react';

interface HeaderProps {
  user: User | null;
  ghStatus: GitHubConnectionStatus | null;
  onOpenConnectModal: () => void;
}

export const Header: React.FC<HeaderProps> = ({ user, ghStatus, onOpenConnectModal }) => {
  return (
    <header className="h-14 border-b border-subtle bg-dark/80 backdrop-blur-md px-6 flex items-center justify-end sticky top-0 z-10 shrink-0">
      <div className="flex items-center gap-3">
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-white/[0.04] text-text-muted border border-subtle">
          v1.0.0-phase7
        </span>

        {ghStatus?.connected ? (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.03] border border-emerald-500/25 text-xs font-medium text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>@{ghStatus.github_username}</span>
          </div>
        ) : (
          <button
            onClick={onOpenConnectModal}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/25 text-xs font-medium text-amber-400 hover:bg-amber-500/15 transition-colors"
          >
            <AlertCircle className="w-3.5 h-3.5" />
            <span>GitHub Disconnected</span>
          </button>
        )}

        <button onClick={onOpenConnectModal} className="btn btn-primary text-xs flex items-center gap-1.5">
          <Plus className="w-4 h-4" />
          <span>Connect Repository</span>
        </button>

        {user && (
          <div className="flex items-center gap-2 pl-3 border-l border-subtle">
            <img
              src={user.avatar_url || 'https://github.com/identicons/talos.png'}
              alt={user.username}
              className="w-7 h-7 rounded-full border border-subtle object-cover"
            />
            <span className="text-xs font-medium text-text-secondary font-mono">{user.username}</span>
          </div>
        )}
      </div>
    </header>
  );
};
