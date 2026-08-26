import { useEffect, useState, useCallback } from 'react';
import { api } from '../services/api';
import { Repository, MaintenanceIssue, PullRequest, ActionLog } from '../types';

export interface RepoIssue extends MaintenanceIssue {
  repository: Repository;
}
export interface RepoPullRequest extends PullRequest {
  repository: Repository;
}
export interface RepoActionLog extends ActionLog {
  repository?: Repository;
}

/** Real cross-repository data for Command Center / Maintenance Bay / Review
 * Queue / Activity Log — aggregated client-side from the existing per-repo
 * endpoints (no backend changes). Every field here traces back to a genuine
 * API response; nothing is fabricated. */
export function useCrossRepoData() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [issues, setIssues] = useState<RepoIssue[]>([]);
  const [pullRequests, setPullRequests] = useState<RepoPullRequest[]>([]);
  const [logs, setLogs] = useState<RepoActionLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const repos = await api.getRepositories();
      setRepositories(repos);

      const [issueLists, prLists, logLists] = await Promise.all([
        Promise.all(repos.map((r) => api.getIssues(r.id).catch(() => []))),
        Promise.all(repos.map((r) => api.getRepositoryPullRequests(r.id).catch(() => []))),
        Promise.all(repos.map((r) => api.getLogs(r.id).catch(() => []))),
      ]);

      setIssues(repos.flatMap((r, i) => issueLists[i].map((issue) => ({ ...issue, repository: r }))));
      setPullRequests(repos.flatMap((r, i) => prLists[i].map((pr) => ({ ...pr, repository: r }))));
      setLogs(
        repos
          .flatMap((r, i) => logLists[i].map((log) => ({ ...log, repository: r })))
          .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      );
    } catch (err: any) {
      setError(err.message || 'Failed to load cross-repository data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { repositories, issues, pullRequests, logs, loading, error, reload: load };
}
