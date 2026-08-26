import React, { useMemo, useState } from 'react';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState } from '../components/ui/EmptyState';
import { RepositoryCard } from '../components/RepositoryCard';
import { useCrossRepoData } from '../hooks/useCrossRepoData';
import { useAppShell } from '../layouts/AppShell';
import { GitFork, Plus, ShieldAlert, Search, X, AlertCircle } from 'lucide-react';

export const RepositoryRegistryPage: React.FC = () => {
  const { openConnectModal } = useAppShell();
  const { repositories, issues, loading, error, reload } = useCrossRepoData();
  const [searchQuery, setSearchQuery] = useState('');

  const severityByRepo = useMemo(() => {
    const map: Record<number, { high: number; medium: number }> = {};
    for (const issue of issues) {
      if (issue.status === 'RESOLVED' || issue.status === 'DELIVERED') continue;
      const bucket = (map[issue.repository.id] ??= { high: 0, medium: 0 });
      if (issue.severity === 'CRITICAL' || issue.severity === 'HIGH') bucket.high += 1;
      else if (issue.severity === 'MEDIUM') bucket.medium += 1;
    }
    return map;
  }, [issues]);

  const filteredRepositories = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return repositories;
    return repositories.filter((r) =>
      [r.full_name, r.name, r.owner, r.primary_language].filter(Boolean).some((field) => field!.toLowerCase().includes(query))
    );
  }, [repositories, searchQuery]);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <PageHeader
        eyebrow="Repository Registry"
        title="Repository Registry"
        subtitle="Manage and monitor connected repositories."
        actions={
          <button onClick={openConnectModal} className="btn btn-primary text-xs flex items-center gap-1.5">
            <Plus className="w-4 h-4" />
            <span>Connect Repository</span>
          </button>
        }
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

      <div className="flex items-center justify-between gap-3 border-b border-subtle pb-3">
        <div className="flex items-center gap-2">
          <GitFork className="w-4 h-4 text-blue-400" />
          <h2 className="text-sm font-semibold text-text-secondary font-mono uppercase tracking-wide">
            {filteredRepositories.length} Connected{searchQuery ? ` / ${repositories.length}` : ''}
          </h2>
        </div>
        {repositories.length > 0 && (
          <div className="relative w-full sm:w-72">
            <Search className="w-3.5 h-3.5 text-text-muted absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search repositories..."
              className="w-full bg-input border border-muted rounded-lg pl-9 pr-8 py-1.5 text-xs text-text-primary placeholder-text-muted focus:outline-none focus:border-blue-500"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded hover:bg-white/10 text-text-muted hover:text-text-primary"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        )}
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="h-40 skeleton rounded-xl" />
          <div className="h-40 skeleton rounded-xl" />
          <div className="h-40 skeleton rounded-xl" />
        </div>
      ) : repositories.length === 0 ? (
        <EmptyState
          icon={<ShieldAlert className="w-6 h-6" />}
          tone="info"
          title="No Repositories Connected Yet"
          description="Connect your GitHub account to select repositories for TALOS to monitor."
          action={
            <button onClick={openConnectModal} className="btn btn-primary text-xs inline-flex items-center gap-1.5">
              <Plus className="w-4 h-4" />
              <span>Connect GitHub Repository</span>
            </button>
          }
        />
      ) : filteredRepositories.length === 0 ? (
        <EmptyState
          icon={<Search className="w-6 h-6" />}
          title={`No repositories found for "${searchQuery}"`}
          description="Try a different name, owner, or language."
          action={<button onClick={() => setSearchQuery('')} className="btn btn-secondary text-xs">Clear Search</button>}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredRepositories.map((repo) => (
            <RepositoryCard key={repo.id} repo={repo} issueSummary={severityByRepo[repo.id]} />
          ))}
        </div>
      )}
    </div>
  );
};
