import React, { useMemo, useState } from 'react';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState } from '../components/ui/EmptyState';
import { useCrossRepoData } from '../hooks/useCrossRepoData';
import { Activity as ActivityIcon, Search, X } from 'lucide-react';

const STEP_TONE: Record<string, string> = {
  DETECT: 'text-blue-400',
  UNDERSTAND: 'text-blue-400',
  PLAN: 'text-blue-400',
  PATCH: 'text-amber-400',
  VERIFY: 'text-emerald-400',
  DELIVER: 'text-purple-400',
  ESCALATE: 'text-red-400',
};

type FilterKey = 'all' | 'DETECT' | 'UNDERSTAND' | 'PATCH' | 'VERIFY' | 'DELIVER' | 'failures' | 'ESCALATE';

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'DETECT', label: 'Detection' },
  { key: 'UNDERSTAND', label: 'Analysis' },
  { key: 'PATCH', label: 'Patch' },
  { key: 'VERIFY', label: 'Verification' },
  { key: 'DELIVER', label: 'Delivery' },
  { key: 'failures', label: 'Failures' },
  { key: 'ESCALATE', label: 'Escalations' },
];

export const ActivityPage: React.FC = () => {
  const { logs, loading, error } = useCrossRepoData();
  const [filter, setFilter] = useState<FilterKey>('all');
  const [query, setQuery] = useState('');

  const filteredLogs = useMemo(() => {
    let result = logs;
    if (filter === 'failures') {
      result = result.filter((l) => l.level === 'ERROR');
    } else if (filter !== 'all') {
      result = result.filter((l) => l.step === filter);
    }
    const q = query.trim().toLowerCase();
    if (q) {
      result = result.filter((l) =>
        [l.repository?.full_name, l.message, l.step].filter(Boolean).some((f) => f!.toLowerCase().includes(q))
      );
    }
    return result;
  }, [logs, filter, query]);

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <PageHeader
        eyebrow="Activity Log"
        title="Activity Log"
        subtitle="A real-time audit ledger of every autonomous action TALOS has taken, across all repositories."
      />

      {error && <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>}

      {logs.length > 0 && (
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
              placeholder="Search repository, message..."
              className="w-full bg-input border border-muted rounded-lg pl-9 pr-8 py-1.5 text-xs text-text-primary placeholder-text-muted focus:outline-none focus:border-blue-500"
            />
            {query && (
              <button onClick={() => setQuery('')} className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded hover:bg-white/10 text-text-muted hover:text-text-primary">
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          <div className="h-10 skeleton rounded" />
          <div className="h-10 skeleton rounded" />
          <div className="h-10 skeleton rounded" />
        </div>
      ) : filteredLogs.length === 0 ? (
        <EmptyState
          icon={<ActivityIcon className="w-6 h-6" />}
          title={logs.length === 0 ? 'No activity recorded yet' : 'No activity matches this filter'}
          description={logs.length === 0 ? 'Connect a repository and run a scan to start building the ledger.' : 'Try a different filter or search term.'}
        />
      ) : (
        <div className="relative pl-6">
          <div className="absolute left-[7px] top-2 bottom-2 w-px bg-white/[0.08]" />
          <div className="space-y-5">
            {filteredLogs.map((log) => (
              <div key={log.id} className="relative">
                <span
                  className={`absolute -left-6 top-1 w-3.5 h-3.5 rounded-full border-2 border-dark ${
                    log.level === 'ERROR' ? 'bg-red-500' : log.level === 'WARNING' ? 'bg-amber-500' : 'bg-blue-500'
                  }`}
                />
                <div className="flex items-center gap-2.5 text-xs font-mono text-text-muted">
                  <span>{new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                  <span className={`font-semibold ${STEP_TONE[log.step] || 'text-text-secondary'}`}>{log.step}</span>
                  {log.repository && <span className="truncate">{log.repository.full_name}</span>}
                </div>
                <p className="text-sm text-text-primary mt-1 leading-relaxed">{log.message}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
