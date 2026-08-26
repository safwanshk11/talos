import React, { useMemo, useState } from 'react';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState } from '../components/ui/EmptyState';
import { useCrossRepoData } from '../hooks/useCrossRepoData';
import { api } from '../services/api';
import { CheckCircle2, GitPullRequest, ExternalLink, Search, X, RefreshCw } from 'lucide-react';

export const ReviewQueuePage: React.FC = () => {
  const { pullRequests, loading, error, reload } = useCrossRepoData();
  const [query, setQuery] = useState('');
  const [syncing, setSyncing] = useState(false);

  const delivered = useMemo(
    () =>
      pullRequests
        .filter((pr) => pr.status === 'delivered')
        .filter((pr) => {
          const q = query.trim().toLowerCase();
          if (!q) return true;
          return [pr.repository.full_name, pr.title, pr.pr_number != null ? `#${pr.pr_number}` : null]
            .filter(Boolean)
            .some((f) => f!.toLowerCase().includes(q));
        })
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    [pullRequests, query]
  );

  const handleSync = async () => {
    setSyncing(true);
    try {
      await Promise.all(
        pullRequests
          .filter((pr) => pr.status === 'delivered' && pr.pr_number)
          .map((pr) => api.refreshPullRequestStatus(pr.repository_id, pr.id).catch(() => null))
      );
      await reload();
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <PageHeader
        eyebrow="Review Queue"
        title="Review Queue"
        subtitle="Pull requests TALOS has delivered, awaiting your review."
        actions={
          <button onClick={handleSync} disabled={syncing || delivered.length === 0} className="btn btn-secondary text-xs flex items-center gap-1.5 disabled:opacity-50">
            <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
            <span>{syncing ? 'Syncing...' : 'Sync Status'}</span>
          </button>
        }
      />

      {error && <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>}

      {pullRequests.filter((pr) => pr.status === 'delivered').length > 0 && (
        <div className="relative w-full sm:w-72">
          <Search className="w-3.5 h-3.5 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search repository, PR title, #number..."
            className="w-full bg-input border border-muted rounded-lg pl-9 pr-8 py-1.5 text-xs text-text-primary placeholder-text-muted focus:outline-none focus:border-blue-500"
          />
          {query && (
            <button onClick={() => setQuery('')} className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded hover:bg-white/10 text-text-muted hover:text-text-primary">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          <div className="h-20 skeleton rounded-xl" />
          <div className="h-20 skeleton rounded-xl" />
        </div>
      ) : delivered.length === 0 ? (
        <EmptyState
          icon={<CheckCircle2 className="w-6 h-6" />}
          tone="success"
          title={query ? 'No pull requests match your search' : 'No pull requests awaiting review'}
          description={query ? 'Try a different repository name, title, or PR number.' : 'Once TALOS delivers a verified patch, it will appear here for review.'}
        />
      ) : (
        <div className="space-y-3">
          {delivered.map((pr) => {
            const isOpen = pr.github_status === 'open';
            return (
              <a
                key={pr.id}
                href={pr.pr_url}
                target="_blank"
                rel="noreferrer"
                className="block p-5 rounded-xl bg-card border border-subtle card-interactive"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 text-xs font-mono text-text-muted mb-1.5">
                      <span>#{pr.pr_number}</span>
                      <span>·</span>
                      <span className="truncate">{pr.repository.full_name}</span>
                    </div>
                    <div className="text-sm font-semibold text-text-primary truncate">{pr.title}</div>
                    <div className="flex items-center gap-3 mt-2 text-xs font-mono text-text-muted">
                      <span>{pr.head_branch} → {pr.base_branch}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-bold font-mono ${
                        isOpen
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25'
                          : pr.github_status === 'merged'
                          ? 'bg-purple-500/10 text-purple-400 border-purple-500/25'
                          : 'bg-white/[0.05] text-text-secondary border-subtle'
                      }`}
                    >
                      <GitPullRequest className="w-3 h-3" />
                      {(pr.github_status || 'open').toUpperCase()}
                    </span>
                    <ExternalLink className="w-4 h-4 text-text-muted" />
                  </div>
                </div>
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
};
