import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Repository } from '../types';
import {
  ArrowLeft,
  GitBranch,
  ExternalLink,
  RefreshCw,
  ShieldCheck,
  Lock,
  GitCommit,
  Clock,
  Play,
  Pause,
  AlertTriangle,
  FileCode2,
  Wrench,
  CheckCircle,
  GitPullRequest,
} from 'lucide-react';

interface RepositoryDetailPageProps {
  repoId: number;
  onBack: () => void;
}

export const RepositoryDetailPage: React.FC<RepositoryDetailPageProps> = ({
  repoId,
  onBack,
}) => {
  const [repo, setRepo] = useState<Repository | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);

  const fetchRepo = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getRepositoryDetail(repoId);
      setRepo(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load repository detail.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRepo();
  }, [repoId]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const updated = await api.syncRepository(repoId);
      setRepo(updated);
    } catch (err: any) {
      alert(`Sync failed: ${err.message}`);
    } finally {
      setSyncing(false);
    }
  };

  const handleToggleMonitoring = async () => {
    if (!repo) return;
    const nextStatus = repo.monitoring_status === 'active' ? 'paused' : 'active';
    try {
      const updated = await api.toggleMonitoring(repoId, nextStatus);
      setRepo(updated);
    } catch (err: any) {
      alert(`Failed to update status: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="p-8 max-w-7xl mx-auto space-y-6">
        <div className="h-6 w-32 skeleton"></div>
        <div className="h-32 w-full skeleton rounded-xl"></div>
        <div className="grid grid-cols-2 gap-6">
          <div className="h-64 skeleton rounded-xl"></div>
          <div className="h-64 skeleton rounded-xl"></div>
        </div>
      </div>
    );
  }

  if (error || !repo) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <button onClick={onBack} className="btn btn-secondary text-xs mb-6 flex items-center gap-1.5">
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Dashboard</span>
        </button>
        <div className="p-6 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          {error || 'Repository not found'}
        </div>
      </div>
    );
  }

  const isPaused = repo.monitoring_status === 'paused';

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Back Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="btn btn-secondary text-xs flex items-center gap-1.5"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Overview</span>
        </button>

        <div className="flex items-center gap-3">
          <button
            onClick={handleSync}
            disabled={syncing}
            className="btn btn-secondary text-xs flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin text-blue-400' : ''}`} />
            <span>Sync GitHub Metadata</span>
          </button>

          <button
            onClick={handleToggleMonitoring}
            className={`btn text-xs flex items-center gap-1.5 ${
              isPaused ? 'btn-primary' : 'btn-secondary'
            }`}
          >
            {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5 text-amber-400" />}
            <span>{isPaused ? 'Resume Monitoring' : 'Pause Monitoring'}</span>
          </button>
        </div>
      </div>

      {/* Main Metadata Banner */}
      <div className="p-6 rounded-xl bg-card border border-subtle space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-subtle pb-6">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <ShieldCheck className="w-7 h-7" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-xl font-bold text-slate-100 font-mono">
                  {repo.full_name}
                </h1>
                <span className={`badge ${isPaused ? 'badge-amber' : 'badge-green'}`}>
                  {repo.monitoring_status.toUpperCase()}
                </span>
                <span className="badge badge-gray uppercase">{repo.visibility}</span>
              </div>
              <p className="text-xs text-slate-400 mt-1 font-mono">
                Repository ID: {repo.github_repo_id} • Connected to TALOS
              </p>
            </div>
          </div>

          <a
            href={repo.html_url}
            target="_blank"
            rel="noreferrer"
            className="btn btn-secondary text-xs inline-flex items-center gap-1.5 self-start md:self-auto"
          >
            <span>View on GitHub</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>

        {/* Detailed Metadata Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono">
          <div className="p-3 rounded bg-slate-950/50 border border-subtle/70">
            <span className="text-slate-500 block text-[11px] mb-1">DEFAULT BRANCH</span>
            <div className="flex items-center gap-1.5 text-slate-200 font-semibold">
              <GitBranch className="w-3.5 h-3.5 text-blue-400" />
              <span>{repo.default_branch}</span>
            </div>
          </div>

          <div className="p-3 rounded bg-slate-950/50 border border-subtle/70">
            <span className="text-slate-500 block text-[11px] mb-1">PRIMARY LANGUAGE</span>
            <div className="flex items-center gap-1.5 text-slate-200 font-semibold">
              <FileCode2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>{repo.primary_language || 'Markdown / Config'}</span>
            </div>
          </div>

          <div className="p-3 rounded bg-slate-950/50 border border-subtle/70">
            <span className="text-slate-500 block text-[11px] mb-1">CONNECTION STATUS</span>
            <div className="flex items-center gap-1.5 text-emerald-400 font-semibold capitalize">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
              <span>{repo.connection_status}</span>
            </div>
          </div>

          <div className="p-3 rounded bg-slate-950/50 border border-subtle/70">
            <span className="text-slate-500 block text-[11px] mb-1">LAST CHECKED</span>
            <div className="flex items-center gap-1.5 text-slate-300 font-semibold">
              <Clock className="w-3.5 h-3.5 text-slate-500" />
              <span>{new Date(repo.last_checked_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
          </div>
        </div>

        {/* Latest Commit Details Card */}
        <div className="p-4 rounded-lg bg-slate-950/60 border border-subtle space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 border-b border-subtle/50 pb-2">
            <span className="flex items-center gap-2 text-slate-200 font-semibold">
              <GitCommit className="w-4 h-4 text-blue-400" />
              LATEST COMMIT ON {repo.default_branch.toUpperCase()}
            </span>
            {repo.latest_commit?.sha && (
              <span className="bg-slate-800 px-2 py-0.5 rounded text-blue-300 border border-slate-700">
                {repo.latest_commit.sha}
              </span>
            )}
          </div>

          {repo.latest_commit?.message ? (
            <div className="text-xs space-y-1">
              <p className="text-slate-200 font-mono">
                {repo.latest_commit.message}
              </p>
              <div className="flex items-center gap-3 text-slate-500 text-[11px]">
                <span>Author: {repo.latest_commit.author || 'GitHub User'}</span>
                {repo.latest_commit.date && (
                  <span>Committed: {new Date(repo.latest_commit.date).toLocaleString()}</span>
                )}
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-500 italic">No commit metadata synced yet.</p>
          )}
        </div>
      </div>

      {/* Explicitly Labeled Future Functionality Modules */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-subtle pb-3">
          <h2 className="text-base font-semibold text-slate-200 font-mono">
            MAINTENANCE PIPELINE MODULES
          </h2>
          <span className="badge badge-amber font-mono text-[11px]">
            FUTURE MODULES (PHASES 2 - 5)
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Phase 2 Placeholder */}
          <div className="p-5 rounded-lg bg-card/50 border border-dashed border-subtle space-y-3 opacity-80">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-semibold text-slate-300 font-mono">
                  Detection Engine & Vulnerability Scan
                </h3>
              </div>
              <span className="badge badge-gray text-[10px]">Phase 2</span>
            </div>
            <p className="text-xs text-slate-500">
              Scans repository dependencies and AST context for vulnerable packages, outdated locks, and broken build rules.
            </p>
            <div className="p-2 rounded bg-slate-950/60 border border-subtle text-[11px] text-slate-500 font-mono flex items-center gap-2">
              <Lock className="w-3 h-3 text-slate-600" />
              <span>Scanning module unavailable in Phase 1</span>
            </div>
          </div>

          {/* Phase 3 Placeholder */}
          <div className="p-5 rounded-lg bg-card/50 border border-dashed border-subtle space-y-3 opacity-80">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Wrench className="w-4 h-4 text-blue-400" />
                <h3 className="text-sm font-semibold text-slate-300 font-mono">
                  Patch Planning & Isolated Code Fix
                </h3>
              </div>
              <span className="badge badge-gray text-[10px]">Phase 3</span>
            </div>
            <p className="text-xs text-slate-500">
              Generates surgical code patches and dependency migrations in isolated temporary environments.
            </p>
            <div className="p-2 rounded bg-slate-950/60 border border-subtle text-[11px] text-slate-500 font-mono flex items-center gap-2">
              <Lock className="w-3 h-3 text-slate-600" />
              <span>Patch generation module unavailable in Phase 1</span>
            </div>
          </div>

          {/* Phase 4 Placeholder */}
          <div className="p-5 rounded-lg bg-card/50 border border-dashed border-subtle space-y-3 opacity-80">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-semibold text-slate-300 font-mono">
                  Verification Gate Sandbox
                </h3>
              </div>
              <span className="badge badge-gray text-[10px]">Phase 4</span>
            </div>
            <p className="text-xs text-slate-500">
              Runs dockerized builds, unit tests, regression suites, type checks, and security verification before PR delivery.
            </p>
            <div className="p-2 rounded bg-slate-950/60 border border-subtle text-[11px] text-slate-500 font-mono flex items-center gap-2">
              <Lock className="w-3 h-3 text-slate-600" />
              <span>Verification Sandbox module unavailable in Phase 1</span>
            </div>
          </div>

          {/* Phase 5 Placeholder */}
          <div className="p-5 rounded-lg bg-card/50 border border-dashed border-subtle space-y-3 opacity-80">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <GitPullRequest className="w-4 h-4 text-purple-400" />
                <h3 className="text-sm font-semibold text-slate-300 font-mono">
                  Automated Pull Request Delivery
                </h3>
              </div>
              <span className="badge badge-gray text-[10px]">Phase 5</span>
            </div>
            <p className="text-xs text-slate-500">
              Pushes isolated branches and opens review-ready pull requests containing verification evidence.
            </p>
            <div className="p-2 rounded bg-slate-950/60 border border-subtle text-[11px] text-slate-500 font-mono flex items-center gap-2">
              <Lock className="w-3 h-3 text-slate-600" />
              <span>PR delivery module unavailable in Phase 1</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
