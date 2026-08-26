import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Modal } from './ui/Modal';
import { GitHubRepoImportItem, GitHubConnectionStatus } from '../types';
import {
  X,
  Github,
  Key,
  Check,
  Loader2,
  Lock,
  Plus,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';

interface ConnectGithubModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRepositoryConnected: () => void;
  ghStatus: GitHubConnectionStatus | null;
  onRefreshStatus: () => void;
}

export const ConnectGithubModal: React.FC<ConnectGithubModalProps> = ({
  isOpen,
  onClose,
  onRepositoryConnected,
  ghStatus,
  onRefreshStatus,
}) => {
  const [patInput, setPatInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [availableRepos, setAvailableRepos] = useState<GitHubRepoImportItem[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [connectingFullName, setConnectingFullName] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'pat' | 'oauth'>('pat');

  useEffect(() => {
    if (isOpen && ghStatus?.connected) {
      fetchAvailableRepos();
    }
  }, [isOpen, ghStatus?.connected]);

  const fetchAvailableRepos = async () => {
    setLoadingRepos(true);
    setError(null);
    try {
      const repos = await api.getAvailableGitHubRepos();
      setAvailableRepos(repos);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch available GitHub repositories.');
    } finally {
      setLoadingRepos(false);
    }
  };

  const handleConnectPAT = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patInput.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const res = await api.connectPAT(patInput.trim());
      localStorage.setItem('talos_token', res.access_token);
      onRefreshStatus();
      setPatInput('');
      fetchAvailableRepos();
    } catch (err: any) {
      setError(err.message || 'Failed to connect with provided GitHub PAT.');
    } finally {
      setLoading(false);
    }
  };

  const handleOAuthRedirect = async () => {
    setError(null);
    try {
      const res = await api.getOAuthUrl();
      window.location.href = res.url;
    } catch (err: any) {
      setError(err.message || 'Failed to initialize GitHub OAuth flow.');
    }
  };

  const handleImportRepo = async (repo: GitHubRepoImportItem) => {
    setConnectingFullName(repo.full_name);
    setError(null);
    try {
      await api.connectRepository(repo.github_repo_id, repo.full_name);
      onRepositoryConnected();
      setAvailableRepos((prev) =>
        prev.map((r) =>
          r.github_repo_id === repo.github_repo_id ? { ...r, is_connected: true } : r
        )
      );
    } catch (err: any) {
      setError(err.message || `Failed to connect repository ${repo.full_name}`);
    } finally {
      setConnectingFullName(null);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} maxWidth="max-w-2xl">
        {/* Header */}
        <div className="p-5 border-b border-subtle flex items-center justify-between bg-slate-900/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <Github className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-100">
                Connect GitHub Repository
              </h2>
              <p className="text-xs text-slate-400">
                Select repositories for TALOS to monitor and maintain.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-slate-200"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {error && (
            <div className="p-3.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* GitHub Connection Step */}
          {!ghStatus?.connected ? (
            <div className="space-y-5">
              <div className="flex gap-2 border-b border-subtle pb-3">
                <button
                  onClick={() => setActiveTab('pat')}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    activeTab === 'pat'
                      ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Personal Access Token (Recommended)
                </button>
                <button
                  onClick={() => setActiveTab('oauth')}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    activeTab === 'oauth'
                      ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  GitHub OAuth App
                </button>
              </div>

              {activeTab === 'pat' ? (
                <form onSubmit={handleConnectPAT} className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1.5">
                      GitHub Personal Access Token (PAT)
                    </label>
                    <div className="relative">
                      <Key className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                      <input
                        type="password"
                        placeholder="github_pat_..."
                        value={patInput}
                        onChange={(e) => setPatInput(e.target.value)}
                        className="w-full bg-input border border-muted rounded-lg pl-9 pr-4 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
                        required
                      />
                    </div>
                    <p className="text-[11px] text-slate-500 mt-1.5 flex items-center gap-1">
                      <Lock className="w-3 h-3 text-slate-400" />
                      Requires <code className="text-slate-300">repo</code> scope. Token is encrypted and stored safely on the backend.
                    </p>
                  </div>

                  <button
                    type="submit"
                    disabled={loading || !patInput.trim()}
                    className="btn btn-primary w-full text-xs"
                  >
                    {loading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <span>Authenticate & Fetch Repositories</span>
                    )}
                  </button>
                </form>
              ) : (
                <div className="text-center py-6 space-y-4">
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    Authenticate directly through GitHub OAuth to grant repository monitoring permissions.
                  </p>
                  <button
                    onClick={handleOAuthRedirect}
                    className="btn btn-secondary text-xs inline-flex items-center gap-2"
                  >
                    <Github className="w-4 h-4 text-slate-100" />
                    <span>Authorize with GitHub OAuth</span>
                    <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                  </button>
                </div>
              )}
            </div>
          ) : (
            /* Repository Picker List */
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300 font-mono">
                  AVAILABLE GITHUB REPOSITORIES ({availableRepos.length})
                </span>
                <button
                  onClick={fetchAvailableRepos}
                  disabled={loadingRepos}
                  className="text-xs text-blue-400 hover:underline flex items-center gap-1"
                >
                  {loadingRepos && <Loader2 className="w-3 h-3 animate-spin" />}
                  Refresh
                </button>
              </div>

              {loadingRepos ? (
                <div className="space-y-2 py-4">
                  <div className="h-12 w-full skeleton"></div>
                  <div className="h-12 w-full skeleton"></div>
                  <div className="h-12 w-full skeleton"></div>
                </div>
              ) : availableRepos.length === 0 ? (
                <div className="text-center py-8 border border-dashed border-subtle rounded-lg text-slate-500 text-xs">
                  No repositories found for this GitHub account.
                </div>
              ) : (
                <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                  {availableRepos.map((repo) => {
                    const isConnecting = connectingFullName === repo.full_name;
                    return (
                      <div
                        key={repo.github_repo_id}
                        className="p-3.5 rounded-lg bg-slate-900/60 border border-subtle hover:border-slate-700 flex items-center justify-between text-xs"
                      >
                        <div className="overflow-hidden pr-3">
                          <div className="font-semibold text-slate-200 truncate font-mono">
                            {repo.full_name}
                          </div>
                          <div className="text-slate-400 text-[11px] flex items-center gap-2 mt-0.5">
                            <span>Language: {repo.primary_language || 'N/A'}</span>
                            <span>•</span>
                            <span>Branch: {repo.default_branch}</span>
                            <span>•</span>
                            <span className="uppercase">{repo.visibility}</span>
                          </div>
                        </div>

                        {repo.is_connected ? (
                          <span className="badge badge-green flex items-center gap-1 shrink-0">
                            <Check className="w-3 h-3" />
                            Connected
                          </span>
                        ) : (
                          <button
                            onClick={() => handleImportRepo(repo)}
                            disabled={isConnecting}
                            className="btn btn-secondary text-xs py-1 px-2.5 shrink-0 flex items-center gap-1"
                          >
                            {isConnecting ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />
                            ) : (
                              <>
                                <Plus className="w-3.5 h-3.5" />
                                <span>Connect</span>
                              </>
                            )}
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-subtle bg-slate-900/50 flex justify-end">
          <button onClick={onClose} className="btn btn-secondary text-xs">
            Done
          </button>
        </div>
    </Modal>
  );
};
