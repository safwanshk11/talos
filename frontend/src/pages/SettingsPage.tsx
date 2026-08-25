import React, { useState } from 'react';
import { GitHubConnectionStatus } from '../types';
import { api } from '../services/api';
import { Shield, Github, Trash2, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

interface SettingsPageProps {
  ghStatus: GitHubConnectionStatus | null;
  onRefreshStatus: () => void;
  onOpenConnectModal: () => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({
  ghStatus,
  onRefreshStatus,
  onOpenConnectModal,
}) => {
  const [disconnecting, setDisconnecting] = useState(false);

  const handleDisconnect = async () => {
    if (!confirm('Are you sure you want to disconnect your GitHub account from TALOS?')) return;
    setDisconnecting(true);
    try {
      await api.disconnectGitHub();
      localStorage.removeItem('talos_token');
      onRefreshStatus();
    } catch (err: any) {
      alert(`Disconnect failed: ${err.message}`);
    } finally {
      setDisconnecting(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-100 font-mono tracking-tight">
          PLATFORM SETTINGS
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Manage GitHub credentials, security tokens, and platform integrations.
        </p>
      </div>

      <div className="p-6 rounded-xl bg-card border border-subtle space-y-6">
        <div className="flex items-center gap-3 border-b border-subtle pb-4">
          <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
            <Github className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-200">GitHub Connection</h2>
            <p className="text-xs text-slate-400">
              TALOS connects securely to GitHub to read repository metadata and track commits.
            </p>
          </div>
        </div>

        {ghStatus?.connected ? (
          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-slate-950/60 border border-emerald-500/30 flex items-center justify-between text-xs">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                <div>
                  <div className="font-semibold text-slate-200">
                    Connected as @{ghStatus.github_username}
                  </div>
                  <div className="text-slate-400 mt-0.5 font-mono">
                    Scopes: {ghStatus.scopes || 'repo, user'} • Connected: {ghStatus.connected_at ? new Date(ghStatus.connected_at).toLocaleDateString() : 'Active'}
                  </div>
                </div>
              </div>

              <button
                onClick={handleDisconnect}
                disabled={disconnecting}
                className="btn btn-danger text-xs flex items-center gap-1.5"
              >
                {disconnecting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Trash2 className="w-3.5 h-3.5" />
                )}
                <span>Disconnect</span>
              </button>
            </div>

            <button onClick={onOpenConnectModal} className="btn btn-secondary text-xs">
              Change Token / Connect Repositories
            </button>
          </div>
        ) : (
          <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-between text-xs">
            <div className="flex items-center gap-3 text-amber-400">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>No GitHub connection active. Connect a PAT or OAuth app to import repositories.</span>
            </div>
            <button onClick={onOpenConnectModal} className="btn btn-primary text-xs shrink-0">
              Connect GitHub
            </button>
          </div>
        )}
      </div>

      <div className="p-6 rounded-xl bg-card border border-subtle space-y-4">
        <div className="flex items-center gap-3 border-b border-subtle pb-4">
          <div className="p-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-300">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-200">Security Principles & Governance</h2>
            <p className="text-xs text-slate-400">
              TALOS operates under strict least-privilege security and isolated branch rules.
            </p>
          </div>
        </div>

        <ul className="text-xs text-slate-400 space-y-2 list-disc list-inside font-mono">
          <li>GitHub credentials are encrypted and strictly managed by the backend.</li>
          <li>Frontend never receives or stores raw access tokens or OAuth secrets.</li>
          <li>Primary branches are protected — TALOS never directly commits to main.</li>
          <li>Untrusted repository files are treated as data, preventing prompt injection attacks.</li>
        </ul>
      </div>
    </div>
  );
};
