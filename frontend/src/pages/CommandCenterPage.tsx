import React, { useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { PageHeader } from '../components/ui/PageHeader';
import { SectionCard } from '../components/ui/SectionCard';
import { EmptyState } from '../components/ui/EmptyState';
import { StatusBadge } from '../components/ui/StatusBadge';
import { MetricsOverview } from '../components/MetricsOverview';
import { useCrossRepoData } from '../hooks/useCrossRepoData';
import { useDashboardStats } from '../hooks/useDashboardStats';
import { usePolling } from '../hooks/usePolling';
import { ACTIVE_STATUSES, ATTENTION_STATUSES } from '../lib/statusGroups';
import { AlertTriangle, AlertCircle, GitPullRequest, CheckCircle2, ChevronRight, ExternalLink, Loader2, ArrowRight, Clock, Radar } from 'lucide-react';

const POLL_INTERVAL_MS = 8000;
const SCHEDULE_HOURS: Record<string, number> = { daily: 24, weekly: 24 * 7 };

function timeAgo(iso?: string): string {
  if (!iso) return 'Never';
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function timeUntil(target: Date): string {
  const mins = Math.round((target.getTime() - Date.now()) / 60000);
  if (mins <= 0) return 'due now';
  if (mins < 60) return `in ${mins}m`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `in ${hours}h`;
  return `in ${Math.round(hours / 24)}d`;
}

export const CommandCenterPage: React.FC = () => {
  const navigate = useNavigate();
  const { stats, loading: statsLoading, reload: reloadStats } = useDashboardStats();
  const { repositories, issues, pullRequests, logs, loading, error, reload } = useCrossRepoData();

  const activeOperations = useMemo(
    () => issues.filter((i) => ACTIVE_STATUSES.includes(i.status)),
    [issues]
  );

  // Live updates: the simplest reliable mechanism available (no SSE/WebSocket
  // infra in this project) — poll only while there's something actually in
  // flight, so an idle dashboard doesn't keep hammering the API.
  usePolling(() => { reload(); reloadStats(); }, POLL_INTERVAL_MS, activeOperations.length > 0);

  const attentionIssues = issues
    .filter((i) => ATTENTION_STATUSES.includes(i.status) || (i.status === 'OPEN' && ['CRITICAL', 'HIGH'].includes(i.severity)))
    .sort((a, b) => (a.severity === b.severity ? 0 : a.severity === 'CRITICAL' ? -1 : 1))
    .slice(0, 5);

  const awaitingReview = pullRequests.filter((pr) => pr.status === 'delivered' && pr.github_status === 'open').slice(0, 5);

  const recentLogs = logs.slice(0, 8);

  const healthRows = useMemo(() => {
    const issueCountByRepo: Record<number, number> = {};
    for (const issue of issues) {
      if (ATTENTION_STATUSES.includes(issue.status) || issue.status === 'OPEN' || ACTIVE_STATUSES.includes(issue.status)) {
        issueCountByRepo[issue.repository.id] = (issueCountByRepo[issue.repository.id] || 0) + 1;
      }
    }
    return [...repositories]
      .sort((a, b) => (issueCountByRepo[b.id] || 0) - (issueCountByRepo[a.id] || 0))
      .slice(0, 5)
      .map((r) => ({ repo: r, issueCount: issueCountByRepo[r.id] || 0 }));
  }, [repositories, issues]);

  // Phase 7: computed entirely from data already fetched — no new endpoint.
  // Only shown when it can be calculated accurately (at least one repo on a
  // real schedule with a known last-scan time).
  const monitoringSummary = useMemo(() => {
    const activeCount = repositories.filter((r) => r.monitoring_status === 'active').length;
    const pausedCount = repositories.length - activeCount;
    let nextCheck: Date | null = null;
    for (const r of repositories) {
      if (r.monitoring_status !== 'active' || !(r.monitoring_schedule in SCHEDULE_HOURS)) continue;
      const last = r.last_automatic_scan_at || r.last_scanned_at;
      const base = last ? new Date(last) : new Date();
      const due = last ? new Date(base.getTime() + SCHEDULE_HOURS[r.monitoring_schedule] * 3600_000) : base;
      if (!nextCheck || due < nextCheck) nextCheck = due;
    }
    return { activeCount, pausedCount, nextCheck };
  }, [repositories]);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <PageHeader
        eyebrow="Command Center"
        title="Command Center"
        subtitle="Real-time overview of autonomous repository operations."
      />

      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={reload} className="btn btn-secondary text-xs py-1 px-2.5">Retry</button>
        </div>
      )}

      {!loading && repositories.length > 0 && (
        <div className="flex items-center gap-2 text-xs text-text-muted font-mono">
          <Radar className="w-3.5 h-3.5 text-blue-400" />
          <span>
            {repositories.length} repositor{repositories.length === 1 ? 'y' : 'ies'} monitored — {monitoringSummary.activeCount} active
            {monitoringSummary.pausedCount > 0 ? `, ${monitoringSummary.pausedCount} paused` : ''}
          </span>
          {monitoringSummary.nextCheck && (
            <>
              <span className="text-text-muted/50">·</span>
              <span>Next scheduled health check {timeUntil(monitoringSummary.nextCheck)}</span>
            </>
          )}
        </div>
      )}

      <MetricsOverview stats={stats} loading={statsLoading} />

      <div className="grid lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3 space-y-6">
          <SectionCard
            icon={<AlertTriangle className="w-4 h-4" />}
            title="Needs Attention"
            subtitle={`${attentionIssues.length + awaitingReview.length} item(s) requiring a decision`}
            noPadding
          >
            {loading ? (
              <div className="p-6 space-y-2">
                <div className="h-14 skeleton rounded-lg" />
                <div className="h-14 skeleton rounded-lg" />
              </div>
            ) : attentionIssues.length === 0 && awaitingReview.length === 0 ? (
              <div className="p-6">
                <EmptyState
                  icon={<CheckCircle2 className="w-5 h-5" />}
                  title="Nothing requires your attention"
                  description="No high-severity issues, failures, or PRs awaiting review right now."
                  tone="success"
                />
              </div>
            ) : (
              <div className="divide-y divide-white/[0.06]">
                {attentionIssues.map((issue) => (
                  <button
                    key={`issue-${issue.id}`}
                    onClick={() => navigate(`/app/repositories/${issue.repository.id}?issue=${issue.id}`)}
                    className="w-full flex items-center justify-between gap-3 px-6 py-3.5 text-left hover:bg-white/[0.02] transition-colors"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <StatusBadge label={issue.status} />
                        <span className="text-sm text-text-primary font-medium truncate">{issue.package_name || issue.title}</span>
                      </div>
                      <div className="text-xs text-text-muted mt-1 font-mono truncate">{issue.repository.full_name}</div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-text-muted shrink-0" />
                  </button>
                ))}
                {awaitingReview.map((pr) => (
                  <a
                    key={`pr-${pr.id}`}
                    href={pr.pr_url}
                    target="_blank"
                    rel="noreferrer"
                    className="w-full flex items-center justify-between gap-3 px-6 py-3.5 text-left hover:bg-white/[0.02] transition-colors"
                  >
                    <div className="min-w-0 flex items-center gap-3">
                      <GitPullRequest className="w-4 h-4 text-purple-400 shrink-0" />
                      <div className="min-w-0">
                        <div className="text-sm text-text-primary font-medium truncate">#{pr.pr_number} {pr.title}</div>
                        <div className="text-xs text-text-muted mt-0.5 font-mono truncate">{pr.repository.full_name}</div>
                      </div>
                    </div>
                    <ExternalLink className="w-3.5 h-3.5 text-text-muted shrink-0" />
                  </a>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard
            icon={<Loader2 className={`w-4 h-4 ${activeOperations.length > 0 ? 'animate-spin' : ''}`} />}
            title="Active Operations"
            subtitle={activeOperations.length > 0 ? `${activeOperations.length} job(s) currently running` : 'TALOS is currently idle'}
            noPadding
          >
            {loading ? (
              <div className="p-6 space-y-2">
                <div className="h-12 skeleton rounded-lg" />
              </div>
            ) : activeOperations.length === 0 ? (
              <div className="p-6">
                <EmptyState icon={<CheckCircle2 className="w-5 h-5" />} title="No active operations" description="TALOS is currently idle." />
              </div>
            ) : (
              <div className="divide-y divide-white/[0.06]">
                {activeOperations.map((issue) => (
                  <button
                    key={issue.id}
                    onClick={() => navigate(`/app/repositories/${issue.repository.id}?issue=${issue.id}`)}
                    className="w-full flex items-center justify-between gap-3 px-6 py-3.5 text-left hover:bg-white/[0.02] transition-colors"
                  >
                    <div className="min-w-0">
                      <div className="text-sm text-text-primary font-medium truncate">{issue.package_name || issue.title}</div>
                      <div className="text-xs text-text-muted mt-0.5 font-mono truncate">{issue.repository.full_name}</div>
                    </div>
                    <StatusBadge label={issue.status} dot />
                  </button>
                ))}
              </div>
            )}
          </SectionCard>
        </div>

        <div className="lg:col-span-2 flex">
          <SectionCard title="Recent Outcomes" subtitle="Across all connected repositories" noPadding className="h-full w-full">
            {loading ? (
              <div className="p-6 space-y-2">
                <div className="h-8 skeleton rounded" />
                <div className="h-8 skeleton rounded" />
                <div className="h-8 skeleton rounded" />
              </div>
            ) : recentLogs.length === 0 ? (
              <div className="p-6">
                <EmptyState icon={<CheckCircle2 className="w-5 h-5" />} title="No activity yet" description="Scan a repository to get started." />
              </div>
            ) : (
              <div className="divide-y divide-white/[0.06] h-full overflow-y-auto">
                {recentLogs.map((log) => (
                  <div key={log.id} className="px-6 py-3 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="px-1.5 py-0.5 rounded bg-white/[0.05] text-blue-400 font-mono font-semibold text-[10px]">{log.step}</span>
                      <span className="text-text-muted text-[10px] font-mono shrink-0">
                        {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <p className="text-text-secondary mt-1.5 leading-snug">{log.message}</p>
                  </div>
                ))}
              </div>
            )}
          </SectionCard>
        </div>
      </div>

      <SectionCard title="Repository Health" subtitle="Repositories with open issues or recent activity" noPadding>
        {loading ? (
          <div className="p-6 space-y-2">
            <div className="h-10 skeleton rounded" />
          </div>
        ) : healthRows.length === 0 ? (
          <div className="p-6">
            <EmptyState icon={<CheckCircle2 className="w-5 h-5" />} title="No repositories connected yet" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-text-muted font-mono uppercase text-[10px] border-b border-subtle">
                  <th className="px-6 py-2.5 font-medium">Repository</th>
                  <th className="px-6 py-2.5 font-medium">Open Issues</th>
                  <th className="px-6 py-2.5 font-medium">Last Scan</th>
                  <th className="px-6 py-2.5 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {healthRows.map(({ repo, issueCount }) => (
                  <tr
                    key={repo.id}
                    onClick={() => navigate(`/app/repositories/${repo.id}`)}
                    className="border-b border-white/[0.04] last:border-0 hover:bg-white/[0.02] cursor-pointer transition-colors"
                  >
                    <td className="px-6 py-3 font-mono text-text-primary font-medium">{repo.full_name}</td>
                    <td className="px-6 py-3 font-mono">
                      {issueCount > 0 ? <span className="text-amber-400">{issueCount}</span> : <span className="text-emerald-400/80">None</span>}
                    </td>
                    <td className="px-6 py-3 text-text-muted font-mono flex items-center gap-1.5">
                      <Clock className="w-3 h-3" />
                      {timeAgo(repo.last_scanned_at)}
                    </td>
                    <td className="px-6 py-3">
                      <StatusBadge label={repo.monitoring_status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="px-6 py-3 border-t border-subtle">
          <Link to="/app/repositories" className="text-xs text-blue-400 hover:underline inline-flex items-center gap-1">
            View all repositories
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </SectionCard>
    </div>
  );
};
