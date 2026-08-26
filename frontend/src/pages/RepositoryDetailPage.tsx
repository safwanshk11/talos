import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import {
  Repository,
  RepositoryReadiness,
  MaintenanceIssue,
  ActionLog,
  PullRequest,
  AutomationPolicy,
  AutomationMode,
  TierAction,
} from '../types';
import { ReadinessCard } from '../components/ReadinessCard';
import { ScanProgressModal } from '../components/ScanProgressModal';
import { IssueDetailModal } from '../components/IssueDetailModal';
import { RemoveRepositoryModal } from '../components/RemoveRepositoryModal';
import { PullRequestCard } from '../components/PullRequestCard';
import {
  ArrowLeft,
  GitBranch,
  ExternalLink,
  RefreshCw,
  GitCommit,
  Clock,
  Play,
  Pause,
  AlertTriangle,
  FileCode2,
  CheckCircle2,
  ShieldAlert,
  Search,
  ChevronRight,
  Shield,
  Loader2,
  Trash2,
  PauseCircle,
  GitPullRequest,
  Gavel,
  Plus,
  X,
  Radar,
  Webhook,
} from 'lucide-react';

const SCHEDULE_OPTIONS: Array<'manual' | 'daily' | 'weekly'> = ['manual', 'daily', 'weekly'];

function timeAgo(iso?: string): string {
  if (!iso) return 'Never';
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

const TRIGGER_LABEL: Record<string, string> = {
  manual: 'Manual',
  scheduled_scan: 'Scheduled Health Check',
  github_push: 'Push Event',
};

const AUTOMATION_MODES: AutomationMode[] = ['CONSERVATIVE', 'BALANCED', 'AUTONOMOUS'];
const STANDARD_TIER_ACTIONS: TierAction[] = ['AUTO_EXECUTE', 'PREPARE_ONLY', 'APPROVAL_REQUIRED'];
const HARD_TIER_ACTIONS: TierAction[] = ['APPROVAL_REQUIRED', 'ESCALATE'];

const TIER_LABEL: Record<string, string> = {
  AUTO_EXECUTE: 'Auto Execute',
  PREPARE_ONLY: 'Prepare Only',
  APPROVAL_REQUIRED: 'Approval Required',
  ESCALATE: 'Escalate',
};

export const RepositoryDetailPage: React.FC = () => {
  const params = useParams<{ id: string }>();
  const repoId = Number(params.id);
  const navigate = useNavigate();
  const onBack = () => navigate('/app/repositories');
  const [searchParams, setSearchParams] = useSearchParams();

  const [repo, setRepo] = useState<Repository | null>(null);
  const [readiness, setReadiness] = useState<RepositoryReadiness | null>(null);
  const [issues, setIssues] = useState<MaintenanceIssue[]>([]);
  const [logs, setLogs] = useState<ActionLog[]>([]);
  const [pullRequests, setPullRequests] = useState<PullRequest[]>([]);
  const [policy, setPolicy] = useState<AutomationPolicy | null>(null);
  const [policySaving, setPolicySaving] = useState(false);
  const [newProtectedPath, setNewProtectedPath] = useState('');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);

  // Scan progress state
  const [scanning, setScanning] = useState(false);
  const [isScanModalOpen, setIsScanModalOpen] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);

  // Selected Issue for Detail Modal
  const [selectedIssue, setSelectedIssue] = useState<MaintenanceIssue | null>(null);

  // Remove Repository flow
  const [removeModalOpen, setRemoveModalOpen] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [removeError, setRemoveError] = useState<string | null>(null);

  const fetchRepoData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [repoData, readinessData, issuesData, logsData, pullRequestsData, policyData] = await Promise.all([
        api.getRepositoryDetail(repoId),
        api.getReadiness(repoId),
        api.getIssues(repoId),
        api.getLogs(repoId),
        api.getRepositoryPullRequests(repoId),
        api.getAutomationPolicy(repoId),
      ]);
      setRepo(repoData);
      setReadiness(readinessData);
      setIssues(issuesData);
      setLogs(logsData);
      setPullRequests(pullRequestsData);
      setPolicy(policyData);

      // Deep-link support: Command Center / Maintenance Bay link here with
      // ?issue=<id> to jump straight to a specific finding.
      const deepLinkIssueId = searchParams.get('issue');
      if (deepLinkIssueId) {
        const match = issuesData.find((i) => i.id === Number(deepLinkIssueId));
        if (match) setSelectedIssue(match);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load repository detail.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRepoData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const handleMonitoringSettingsChange = async (payload: { monitoring_schedule?: string; scan_on_relevant_push?: boolean }) => {
    try {
      const updated = await api.updateMonitoringSettings(repoId, payload);
      setRepo(updated);
    } catch (err: any) {
      alert(`Failed to update monitoring settings: ${err.message}`);
    }
  };

  const handlePolicyChange = async (payload: Partial<AutomationPolicy>) => {
    setPolicySaving(true);
    try {
      const updated = await api.updateAutomationPolicy(repoId, payload);
      setPolicy(updated);
    } catch (err: any) {
      alert(`Failed to update autonomy policy: ${err.message}`);
    } finally {
      setPolicySaving(false);
    }
  };

  const handleAddProtectedPath = async () => {
    const path = newProtectedPath.trim();
    if (!path || !policy) return;
    if (policy.protected_paths.includes(path)) {
      setNewProtectedPath('');
      return;
    }
    setNewProtectedPath('');
    await handlePolicyChange({ protected_paths: [...policy.protected_paths, path] });
  };

  const handleRemoveProtectedPath = async (path: string) => {
    if (!policy) return;
    await handlePolicyChange({ protected_paths: policy.protected_paths.filter((p) => p !== path) });
  };

  const handleConfirmRemove = async () => {
    setRemoving(true);
    setRemoveError(null);
    try {
      await api.removeRepository(repoId);
      // Repository removed -> monitoring stopped -> navigate back to Repositories,
      // where the list/dashboard counts refresh on mount.
      onBack();
    } catch (err: any) {
      // Already removed (e.g. a stale double-click) is effectively success.
      if (err.message?.includes('404') || err.message?.toLowerCase().includes('not found')) {
        onBack();
      } else {
        setRemoveError(err.message || 'Failed to remove repository.');
        setRemoving(false);
      }
    }
  };

  const handleTriggerScan = async () => {
    setScanning(true);
    setScanError(null);
    setIsScanModalOpen(true);

    try {
      await api.triggerScan(repoId);
      // Refresh repository, readiness, issues, and logs after scan completion
      await fetchRepoData();
    } catch (err: any) {
      setScanError(err.message || 'Repository scan failed.');
    } finally {
      setScanning(false);
      // Fetch latest logs
      try {
        const latestLogs = await api.getLogs(repoId);
        setLogs(latestLogs);
      } catch {
        // ignore
      }
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
  const openIssuesCount = issues.filter((i) => i.status === 'OPEN').length;
  // RESOLVED (no patch needed / no longer detected) and DELIVERED (already a real
  // PR — tracked in the Pull Requests section below) are closed out; the
  // vulnerabilities list only needs to show issues still requiring TALOS action.
  const activeIssues = issues.filter((i) => i.status !== 'RESOLVED' && i.status !== 'DELIVERED');

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Top Header Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="btn btn-secondary text-xs flex items-center gap-1.5"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Overview</span>
        </button>

        <div className="flex items-center gap-3">
          {/* Scan Repository Primary Button */}
          <button
            onClick={handleTriggerScan}
            disabled={scanning}
            className="btn btn-primary text-xs flex items-center gap-1.5 shadow-lg shadow-blue-600/20"
          >
            {scanning ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Search className="w-3.5 h-3.5" />
            )}
            <span>{scanning ? 'Scanning Repository...' : 'Scan Repository'}</span>
          </button>

          {isPaused ? (
            <>
              <button
                onClick={handleToggleMonitoring}
                className="btn btn-primary text-xs flex items-center gap-1.5"
              >
                <Play className="w-3.5 h-3.5" />
                <span>Resume Monitoring</span>
              </button>
              <button
                onClick={() => setRemoveModalOpen(true)}
                className="btn btn-danger text-xs flex items-center gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Remove Repository</span>
              </button>
            </>
          ) : (
            <button
              onClick={handleToggleMonitoring}
              className="btn btn-secondary text-xs flex items-center gap-1.5"
            >
              <Pause className="w-3.5 h-3.5 text-amber-400" />
              <span>Pause Monitoring</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Repository Metadata Card */}
      <div className="p-6 rounded-xl bg-card border border-subtle space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-subtle pb-6">
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <Shield className="w-7 h-7" />
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
                Repository ID: {repo.github_repo_id} • {openIssuesCount} Open Vulnerabilities
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

        {isPaused && (
          <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 flex items-center gap-2.5 text-xs">
            <PauseCircle className="w-4 h-4 shrink-0" />
            <span>TALOS is no longer automatically monitoring this repository.</span>
          </div>
        )}

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
            <span className="text-slate-500 block text-[11px] mb-1">LAST SCANNED</span>
            <div className="flex items-center gap-1.5 text-slate-300 font-semibold">
              <Clock className="w-3.5 h-3.5 text-slate-500" />
              <span>
                {repo.last_scanned_at
                  ? new Date(repo.last_scanned_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                  : 'Never'}
              </span>
            </div>
          </div>

          <div className="p-3 rounded bg-slate-950/50 border border-subtle/70">
            <span className="text-slate-500 block text-[11px] mb-1">OPEN ISSUES</span>
            <div className="flex items-center gap-1.5 font-bold text-amber-400">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>{openIssuesCount} Vulnerabilities</span>
            </div>
          </div>
        </div>

        {/* Latest Commit Card */}
        <div className="p-4 rounded-lg bg-slate-950/60 border border-subtle space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 border-b border-subtle/50 pb-2">
            <span className="flex items-center gap-2 text-slate-200 font-semibold">
              <GitCommit className="w-4 h-4 text-blue-400" />
              LATEST COMMIT ON {repo.default_branch.toUpperCase()}
            </span>
            {repo.latest_commit?.sha && (
              <span className="bg-slate-800 px-2 py-0.5 rounded text-blue-300 border border-slate-700">
                {repo.latest_commit.sha.substring(0, 7)}
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

      {/* Phase 7: Continuous Autonomous Monitoring */}
      <div className="p-5 rounded-xl bg-card border border-subtle space-y-4">
        <div className="flex items-center gap-2">
          <Radar className="w-4 h-4 text-blue-400" />
          <h2 className="text-xs font-semibold text-slate-200 font-mono uppercase tracking-wide">Monitoring</h2>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-3 rounded bg-slate-950/50 border border-subtle/70">
            <span className="text-slate-500 block text-[11px] mb-1">STATUS</span>
            <span className={isPaused ? 'text-amber-400 font-bold' : 'text-emerald-400 font-bold'}>{repo.monitoring_status.toUpperCase()}</span>
          </div>
          <div className="p-3 rounded bg-slate-950/50 border border-subtle/70 flex items-center justify-between gap-2">
            <div>
              <span className="text-slate-500 block text-[11px] mb-1">SCHEDULE</span>
              <span className="text-slate-200 font-semibold">{repo.monitoring_schedule.toUpperCase()}</span>
            </div>
            <select
              value={repo.monitoring_schedule}
              disabled={isPaused}
              onChange={(e) => handleMonitoringSettingsChange({ monitoring_schedule: e.target.value })}
              className="bg-input border border-muted rounded px-1.5 py-1 text-[10px] text-text-primary focus:outline-none focus:border-blue-500 disabled:opacity-50"
            >
              {SCHEDULE_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </div>
          <div className="p-3 rounded bg-slate-950/50 border border-subtle/70 flex items-center justify-between gap-2">
            <div>
              <span className="text-slate-500 block text-[11px] mb-1">RELEVANT PUSH SCAN</span>
              <span className={repo.scan_on_relevant_push ? 'text-emerald-400 font-semibold' : 'text-slate-500 font-semibold'}>
                {repo.scan_on_relevant_push ? 'ENABLED' : 'DISABLED'}
              </span>
            </div>
            <button
              onClick={() => handleMonitoringSettingsChange({ scan_on_relevant_push: !repo.scan_on_relevant_push })}
              disabled={isPaused}
              className="text-blue-400 hover:underline text-[10px] disabled:opacity-50 disabled:no-underline"
            >
              Toggle
            </button>
          </div>
          <div className="p-3 rounded bg-slate-950/50 border border-subtle/70">
            <span className="text-slate-500 block text-[11px] mb-1">LAST AUTOMATIC SCAN</span>
            <span className="text-slate-300 font-semibold">{timeAgo(repo.last_automatic_scan_at)}</span>
          </div>
        </div>
        {repo.last_trigger && (
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500 font-mono">
            <Webhook className="w-3 h-3" />
            <span>Last trigger: {TRIGGER_LABEL[repo.last_trigger] || repo.last_trigger}</span>
          </div>
        )}
        {isPaused && (
          <p className="text-[11px] text-amber-400/80 font-mono">Scheduled and push-triggered scans are skipped while monitoring is paused.</p>
        )}
        <p className="text-[11px] text-slate-500 font-mono">
          Continuous monitoring requires a GitHub webhook pointed at TALOS and/or the background scheduler — see Settings for setup status.
        </p>
      </div>

      {/* Automation Readiness Assessment Card */}
      <ReadinessCard readiness={readiness} />

      {/* Detected Security & Maintenance Issues Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-subtle pb-3">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            <h2 className="text-base font-semibold text-slate-200 font-mono">
              DETECTED SECURITY VULNERABILITIES ({activeIssues.length})
            </h2>
          </div>

          <button
            onClick={handleTriggerScan}
            disabled={scanning}
            className="text-xs text-blue-400 hover:underline flex items-center gap-1"
          >
            <RefreshCw className={`w-3 h-3 ${scanning ? 'animate-spin' : ''}`} />
            Run Security Scan
          </button>
        </div>

        {activeIssues.length === 0 ? (
          <div className="p-12 text-center border border-dashed border-subtle rounded-xl bg-slate-900/30 space-y-3">
            <div className="w-10 h-10 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 mx-auto flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div className="max-w-md mx-auto space-y-1">
              <h3 className="text-sm font-semibold text-slate-200 font-mono">
                No Open Vulnerabilities Detected
              </h3>
              <p className="text-xs text-slate-400">
                Click <strong>Scan Repository</strong> to clone the codebase and analyze dependencies against the OSV advisory database.
              </p>
            </div>
            <button onClick={handleTriggerScan} className="btn btn-secondary text-xs">
              Run Scan Now
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {activeIssues.map((issue) => {
              const sevColor =
                issue.severity === 'CRITICAL'
                  ? 'badge-amber'
                  : issue.severity === 'HIGH'
                  ? 'badge-amber'
                  : 'badge-blue';

              return (
                <div
                  key={issue.id}
                  className="p-4 rounded-lg bg-card border border-subtle hover:border-slate-700 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4 font-mono text-xs"
                >
                  <div className="space-y-1 overflow-hidden pr-2">
                    <div className="flex items-center gap-2">
                      <span className={`badge ${sevColor} text-[10px]`}>
                        {issue.severity}
                      </span>
                      <span className="font-bold text-slate-200 text-sm">
                        {issue.package_name}
                      </span>
                      <span className="text-slate-500">•</span>
                      <span className="text-slate-400 text-[11px] truncate">
                        {issue.title}
                      </span>
                    </div>

                    <div className="flex items-center gap-4 text-slate-400 text-[11px] pt-1">
                      <span>Installed: <strong className="text-amber-400">{issue.current_version}</strong></span>
                      <span>Target Fix: <strong className="text-emerald-400">{issue.recommended_version}</strong></span>
                      <span>Affected Files: <strong className="text-blue-400">{issue.affected_files?.length || 0}</strong></span>
                      <span>Advisory: <strong>{issue.advisory_id || 'OSV'}</strong></span>
                    </div>
                  </div>

                  <button
                    onClick={() => setSelectedIssue(issue)}
                    className="btn btn-secondary text-xs py-1.5 px-3 shrink-0 flex items-center gap-1 self-start md:self-auto"
                  >
                    <span>Inspect Issue</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Phase 5: TALOS-delivered Pull Requests — compact operational history */}
      {pullRequests.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 border-b border-subtle pb-3">
            <GitPullRequest className="w-4 h-4 text-purple-400" />
            <h2 className="text-base font-semibold text-slate-200 font-mono">
              TALOS PULL REQUESTS ({pullRequests.length})
            </h2>
          </div>
          <div className="space-y-2">
            {pullRequests.map((pr) => (
              <PullRequestCard key={pr.id} pr={pr} />
            ))}
          </div>
        </div>
      )}

      {/* Activity — real Action Ledger entries for this repository */}
      {logs.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 border-b border-subtle pb-3">
            <Clock className="w-4 h-4 text-blue-400" />
            <h2 className="text-base font-semibold text-slate-200 font-mono">
              ACTIVITY ({logs.length})
            </h2>
          </div>
          <div className="rounded-xl border border-subtle bg-card divide-y divide-white/[0.06] max-h-80 overflow-y-auto">
            {logs.slice(0, 30).map((log) => (
              <div key={log.id} className="px-4 py-2.5 text-xs flex items-start gap-3">
                <span className="text-slate-500 font-mono shrink-0 pt-0.5">
                  {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
                <span className="px-1.5 py-0.5 rounded bg-slate-800 text-blue-400 font-mono font-semibold shrink-0">{log.step}</span>
                <span className="text-slate-300">{log.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Phase 6.5: Decision Engine & Autonomy Governance */}
      {policy && (
        <div className="rounded-xl border border-subtle bg-card overflow-hidden">
          <div className="px-5 py-3.5 border-b border-subtle flex items-center gap-2">
            <Gavel className="w-4 h-4 text-blue-400" />
            <h2 className="text-xs font-semibold text-slate-200 font-mono uppercase tracking-wide">Autonomy Policy</h2>
            <span className="text-[11px] text-slate-500 ml-1">— controls how far TALOS may act without asking first</span>
          </div>
          <div className="p-5 space-y-5">
            <div>
              <p className="text-xs text-slate-400 mb-2">Automation Mode</p>
              <div className="flex items-center gap-2">
                {AUTOMATION_MODES.map((mode) => (
                  <button
                    key={mode}
                    onClick={() => handlePolicyChange({ mode })}
                    disabled={policySaving}
                    className={`px-3 py-1.5 rounded-full text-[11px] font-mono font-semibold border transition-colors disabled:opacity-50 ${
                      policy.mode === mode
                        ? 'bg-blue-600/20 text-blue-400 border-blue-500/30'
                        : 'bg-white/[0.03] text-text-muted border-subtle hover:text-text-secondary'
                    }`}
                  >
                    {mode.charAt(0) + mode.slice(1).toLowerCase()}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              {[
                { key: 'security_patch_action', label: 'Security Patches', options: STANDARD_TIER_ACTIONS },
                { key: 'patch_update_action', label: 'Patch Dependency Updates', options: STANDARD_TIER_ACTIONS },
                { key: 'minor_update_action', label: 'Minor Dependency Updates', options: STANDARD_TIER_ACTIONS },
                { key: 'major_update_action', label: 'Major Dependency Updates', options: HARD_TIER_ACTIONS },
              ].map((tier) => (
                <div key={tier.key} className="p-3 rounded-lg bg-slate-950/50 border border-subtle/70 flex items-center justify-between gap-3">
                  <span className="text-slate-300 font-medium">{tier.label}</span>
                  <select
                    value={(policy as any)[tier.key]}
                    disabled={policySaving}
                    onChange={(e) => handlePolicyChange({ [tier.key]: e.target.value } as Partial<AutomationPolicy>)}
                    className="bg-input border border-muted rounded-md px-2 py-1 text-[11px] font-mono text-text-primary focus:outline-none focus:border-blue-500 disabled:opacity-50"
                  >
                    {tier.options.map((opt) => (
                      <option key={opt} value={opt}>{TIER_LABEL[opt]}</option>
                    ))}
                  </select>
                </div>
              ))}
            </div>

            <div className="pt-4 border-t border-subtle/50 space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm text-slate-200 font-medium">Protected Areas</p>
                  <p className="text-xs text-slate-500 mt-0.5">Changes affecting these paths require additional human control, regardless of mode.</p>
                </div>
                <select
                  value={policy.protected_path_action}
                  disabled={policySaving}
                  onChange={(e) => handlePolicyChange({ protected_path_action: e.target.value as TierAction })}
                  className="bg-input border border-muted rounded-md px-2 py-1 text-[11px] font-mono text-text-primary focus:outline-none focus:border-blue-500 disabled:opacity-50 shrink-0"
                >
                  {HARD_TIER_ACTIONS.map((opt) => (
                    <option key={opt} value={opt}>{TIER_LABEL[opt]}</option>
                  ))}
                </select>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {policy.protected_paths.map((path) => (
                  <span key={path} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/[0.03] border border-subtle text-[11px] font-mono text-slate-300">
                    {path}
                    <button onClick={() => handleRemoveProtectedPath(path)} disabled={policySaving} className="text-slate-500 hover:text-red-400 disabled:opacity-50">
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={newProtectedPath}
                  onChange={(e) => setNewProtectedPath(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleAddProtectedPath(); }}
                  placeholder="e.g. src/billing/**"
                  className="flex-1 bg-input border border-muted rounded-lg px-3 py-1.5 text-xs font-mono text-text-primary placeholder-text-muted focus:outline-none focus:border-blue-500"
                />
                <button onClick={handleAddProtectedPath} disabled={policySaving || !newProtectedPath.trim()} className="btn btn-secondary text-xs flex items-center gap-1 disabled:opacity-50">
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add</span>
                </button>
              </div>
            </div>

            <p className="text-[11px] text-slate-500 pt-2 border-t border-subtle/50">
              Major dependency updates and protected-path changes can never be set to Auto Execute. TALOS never merges anything, in any mode.
            </p>
          </div>
        </div>
      )}

      {/* Repository Settings / Danger Zone */}
      <div className="rounded-xl border border-red-500/20 bg-red-500/[0.03] overflow-hidden">
        <div className="px-5 py-3 border-b border-red-500/20">
          <h2 className="text-xs font-semibold text-red-300 font-mono uppercase tracking-wide">
            Danger Zone
          </h2>
        </div>
        <div className="p-5 space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm text-slate-200 font-medium">Sync repository metadata</p>
              <p className="text-xs text-slate-500 mt-0.5">
                Re-fetch branch, language, and latest commit info from GitHub.
              </p>
            </div>
            <button
              onClick={handleSync}
              disabled={syncing}
              className="btn btn-secondary text-xs flex items-center gap-1.5 shrink-0"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin text-blue-400' : ''}`} />
              <span>Sync Metadata</span>
            </button>
          </div>

          <div className="flex items-center justify-between gap-4 pt-4 border-t border-subtle/50">
            <div>
              <p className="text-sm text-slate-200 font-medium">Remove this repository</p>
              <p className="text-xs text-slate-500 mt-0.5">
                Disconnect from TALOS. Your GitHub repository and its code are never modified or deleted.
              </p>
            </div>
            <button
              onClick={() => setRemoveModalOpen(true)}
              className="btn btn-danger text-xs flex items-center gap-1.5 shrink-0"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Remove Repository</span>
            </button>
          </div>
        </div>
      </div>

      {/* Real-time Scan Progress Modal */}
      <ScanProgressModal
        isOpen={isScanModalOpen}
        onClose={() => setIsScanModalOpen(false)}
        scanning={scanning}
        logs={logs}
        error={scanError}
      />

      {/* Issue Detail Panel/Modal */}
      <IssueDetailModal
        issue={selectedIssue}
        repoId={repoId}
        onClose={() => {
          setSelectedIssue(null);
          if (searchParams.has('issue')) {
            searchParams.delete('issue');
            setSearchParams(searchParams, { replace: true });
          }
        }}
        onJobUpdated={fetchRepoData}
      />

      {/* Remove Repository Confirmation */}
      <RemoveRepositoryModal
        repo={removeModalOpen ? repo : null}
        removing={removing}
        error={removeError}
        onCancel={() => {
          if (removing) return;
          setRemoveModalOpen(false);
          setRemoveError(null);
        }}
        onConfirm={handleConfirmRemove}
      />
    </div>
  );
};
