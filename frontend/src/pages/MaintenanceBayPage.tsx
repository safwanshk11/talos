import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState } from '../components/ui/EmptyState';
import { StatusBadge } from '../components/ui/StatusBadge';
import { useCrossRepoData } from '../hooks/useCrossRepoData';
import { CLOSED_STATUSES } from '../lib/statusGroups';
import { Wrench, AlertTriangle, CheckCircle2, ChevronRight, Search, X } from 'lucide-react';

type FilterKey = 'all' | 'critical' | 'high' | 'medium' | 'low' | 'patch_ready' | 'verification_failed' | 'escalated';

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'critical', label: 'Critical' },
  { key: 'high', label: 'High' },
  { key: 'medium', label: 'Medium' },
  { key: 'low', label: 'Low' },
  { key: 'patch_ready', label: 'Patch Ready' },
  { key: 'verification_failed', label: 'Verification Failed' },
  { key: 'escalated', label: 'Escalated' },
];

export const MaintenanceBayPage: React.FC = () => {
  const navigate = useNavigate();
  const { issues, loading, error } = useCrossRepoData();
  const [filter, setFilter] = useState<FilterKey>('all');
  const [query, setQuery] = useState('');

  const openIssues = useMemo(() => issues.filter((i) => !CLOSED_STATUSES.includes(i.status)), [issues]);

  const filteredIssues = useMemo(() => {
    let result = openIssues;
    if (filter !== 'all') {
      if (['critical', 'high', 'medium', 'low'].includes(filter)) {
        result = result.filter((i) => i.severity.toLowerCase() === filter);
      } else {
        result = result.filter((i) => i.status.toLowerCase() === filter);
      }
    }
    const q = query.trim().toLowerCase();
    if (q) {
      result = result.filter((i) =>
        [i.repository.full_name, i.package_name, i.title].filter(Boolean).some((f) => f!.toLowerCase().includes(q))
      );
    }
    return result.sort((a, b) => {
      const rank: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, UNKNOWN: 4 };
      return (rank[a.severity] ?? 4) - (rank[b.severity] ?? 4);
    });
  }, [openIssues, filter, query]);

  const criticalRepos = useMemo(() => {
    const names = new Set<string>();
    openIssues.forEach((i) => {
      if (i.severity === 'CRITICAL' || i.severity === 'HIGH') names.add(i.repository.full_name);
    });
    return Array.from(names);
  }, [openIssues]);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <PageHeader eyebrow="Maintenance Bay" title="Maintenance Bay" subtitle="AI-detected issues that need attention, across every connected repository." />

      {error && <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>}

      {!loading && criticalRepos.length > 0 && (
        <div className="p-4 rounded-lg bg-red-500/[0.06] border border-red-500/20 flex items-center gap-2.5 text-sm text-red-300">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>
            {criticalRepos.length} repositor{criticalRepos.length === 1 ? 'y requires' : 'ies require'} immediate attention:{' '}
            <span className="font-mono">{criticalRepos.join(', ')}</span>
          </span>
        </div>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 flex-wrap">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`px-2.5 py-1 rounded-full text-[11px] font-mono font-semibold border transition-colors ${
                filter === f.key
                  ? 'bg-blue-600/20 text-blue-400 border-blue-500/30'
                  : 'bg-white/[0.03] text-text-muted border-subtle hover:text-text-secondary'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="relative w-full sm:w-64 shrink-0">
          <Search className="w-3.5 h-3.5 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search repository, package, title..."
            className="w-full bg-input border border-muted rounded-lg pl-9 pr-8 py-1.5 text-xs text-text-primary placeholder-text-muted focus:outline-none focus:border-blue-500"
          />
          {query && (
            <button onClick={() => setQuery('')} className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded hover:bg-white/10 text-text-muted hover:text-text-primary">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="h-36 skeleton rounded-xl" />
          <div className="h-36 skeleton rounded-xl" />
          <div className="h-36 skeleton rounded-xl" />
        </div>
      ) : filteredIssues.length === 0 ? (
        <EmptyState
          icon={<CheckCircle2 className="w-6 h-6" />}
          tone="success"
          title={openIssues.length === 0 ? 'No open maintenance issues detected' : 'No issues match this filter'}
          description={openIssues.length === 0 ? 'Every detected issue has been resolved, verified, or delivered.' : 'Try a different filter or search term.'}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredIssues.map((issue) => (
            <button
              key={issue.id}
              onClick={() => navigate(`/app/repositories/${issue.repository.id}?issue=${issue.id}`)}
              className="text-left p-5 rounded-xl bg-card border border-subtle card-interactive flex flex-col gap-3"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-mono text-text-muted truncate">{issue.repository.full_name}</span>
                <StatusBadge label={issue.severity} />
              </div>
              <div>
                <div className="text-sm font-semibold text-text-primary truncate">{issue.package_name || 'Maintenance issue'}</div>
                <p className="text-xs text-text-muted mt-1 line-clamp-2">{issue.title}</p>
              </div>
              <div className="flex items-center justify-between text-xs font-mono pt-2 border-t border-subtle mt-auto">
                <div className="flex items-center gap-2">
                  <span className="text-amber-400">{issue.current_version || '?'}</span>
                  <ChevronRight className="w-3 h-3 text-text-muted" />
                  <span className="text-emerald-400">{issue.recommended_version || 'latest'}</span>
                </div>
                <StatusBadge label={issue.status} className="!px-2 !py-0.5" />
              </div>
              <div className="flex items-center justify-end gap-1 text-xs text-blue-400 font-medium">
                <Wrench className="w-3.5 h-3.5" />
                <span>View Job</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
