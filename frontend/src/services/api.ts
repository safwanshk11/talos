import {
  User,
  GitHubConnectionStatus,
  Repository,
  GitHubRepoImportItem,
  DashboardStats,
  RepositoryScan,
  MaintenanceIssue,
  RepositoryReadiness,
  ActionLog,
  MaintenanceJob,
  VerificationRun,
  PullRequest,
  HealthStatus,
  AutomationPolicy,
  RepositoryEvent,
} from '../types';

const API_BASE = '/api/v1';

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('talos_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${url}`, {
      ...options,
      headers,
    });
  } catch {
    // fetch() itself rejects on DNS failure, connection refused, CORS, etc.
    // — distinct from a real HTTP error response, and worth telling apart in
    // the UI (e.g. "backend unreachable" vs. "the request failed").
    throw new Error('TALOS backend is unreachable. Check your connection and try again.');
  }

  if (!response.ok) {
    let errorMessage = `API Error (${response.status}): ${response.statusText}`;
    try {
      const errData = await response.json();
      if (errData.detail) {
        errorMessage = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // ignore parse error
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

export const api = {
  getHealth: () => request<HealthStatus>('/health'),

  // Auth & GitHub Status
  getMe: () => request<User>('/auth/me'),
  getGitHubStatus: () => request<GitHubConnectionStatus>('/auth/github/status'),
  connectPAT: (token: string) =>
    request<{ access_token: string }>('/auth/github/pat', {
      method: 'POST',
      body: JSON.stringify({ personal_access_token: token }),
    }),
  getOAuthUrl: () => request<{ url: string }>('/auth/github/oauth-url'),
  exchangeOAuthCode: (code: string) =>
    request<{ access_token: string }>('/auth/github/callback', {
      method: 'POST',
      body: JSON.stringify({ code }),
    }),
  disconnectGitHub: () =>
    request<{ message: string }>('/auth/github/disconnect', { method: 'DELETE' }),

  // Repositories
  getAvailableGitHubRepos: () => request<GitHubRepoImportItem[]>('/repositories/available'),
  getRepositories: () => request<Repository[]>('/repositories'),
  getDashboardStats: () => request<DashboardStats>('/repositories/stats'),
  connectRepository: (github_repo_id: string, full_name: string) =>
    request<Repository>('/repositories/connect', {
      method: 'POST',
      body: JSON.stringify({ github_repo_id, full_name }),
    }),
  getRepositoryDetail: (id: number) => request<Repository>(`/repositories/${id}`),
  removeRepository: (id: number) =>
    request<{ message: string; repository_id: number }>(`/repositories/${id}`, { method: 'DELETE' }),
  syncRepository: (id: number) => request<Repository>(`/repositories/${id}/sync`, { method: 'POST' }),
  toggleMonitoring: (id: number, status: 'active' | 'paused') =>
    request<Repository>(`/repositories/${id}/monitoring`, {
      method: 'PATCH',
      body: JSON.stringify({ monitoring_status: status }),
    }),

  // Phase 7: Continuous Autonomous Monitoring
  updateMonitoringSettings: (id: number, payload: { monitoring_schedule?: string; scan_on_relevant_push?: boolean }) =>
    request<Repository>(`/repositories/${id}/monitoring-settings`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  getRepositoryEvents: (id: number, limit = 30) =>
    request<RepositoryEvent[]>(`/repositories/${id}/events?limit=${limit}`),

  // Phase 2: Scanning & Issues
  triggerScan: (id: number) => request<RepositoryScan>(`/repositories/${id}/scan`, { method: 'POST' }),
  getScans: (id: number) => request<RepositoryScan[]>(`/repositories/${id}/scans`),
  getIssues: (id: number, statusFilter?: string) =>
    request<MaintenanceIssue[]>(`/repositories/${id}/issues${statusFilter ? `?status_filter=${statusFilter}` : ''}`),
  getIssueDetail: (repoId: number, issueId: number) =>
    request<MaintenanceIssue>(`/repositories/${repoId}/issues/${issueId}`),
  getReadiness: (id: number) => request<RepositoryReadiness | null>(`/repositories/${id}/readiness`),
  getLogs: (id: number) => request<ActionLog[]>(`/repositories/${id}/logs`),

  // Phase 3: Planning & Patch Generation
  prepareFix: (repoId: number, issueId: number) =>
    request<MaintenanceJob>(`/repositories/${repoId}/issues/${issueId}/prepare-fix`, { method: 'POST' }),
  getIssueJobs: (repoId: number, issueId: number) =>
    request<MaintenanceJob[]>(`/repositories/${repoId}/issues/${issueId}/jobs`),
  getJobDetail: (repoId: number, jobId: number) =>
    request<MaintenanceJob>(`/repositories/${repoId}/jobs/${jobId}`),

  // Phase 6.5: Decision Engine & Autonomy Governance
  getAutomationPolicy: (repoId: number) => request<AutomationPolicy>(`/repositories/${repoId}/automation-policy`),
  updateAutomationPolicy: (repoId: number, payload: Partial<AutomationPolicy>) =>
    request<AutomationPolicy>(`/repositories/${repoId}/automation-policy`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  approveJob: (repoId: number, issueId: number, jobId: number) =>
    request<MaintenanceJob>(`/repositories/${repoId}/issues/${issueId}/jobs/${jobId}/approve`, { method: 'POST' }),
  rejectJob: (repoId: number, issueId: number, jobId: number, reason?: string) =>
    request<MaintenanceJob>(`/repositories/${repoId}/issues/${issueId}/jobs/${jobId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  // Phase 4: Verification Engine
  runVerification: (repoId: number, jobId: number) =>
    request<VerificationRun>(`/repositories/${repoId}/jobs/${jobId}/verify`, { method: 'POST' }),
  getVerificationRuns: (repoId: number, jobId: number) =>
    request<VerificationRun[]>(`/repositories/${repoId}/jobs/${jobId}/verification-runs`),

  // Phase 5: GitHub Delivery & Pull Requests
  deliverPatch: (repoId: number, jobId: number) =>
    request<PullRequest>(`/repositories/${repoId}/jobs/${jobId}/deliver`, { method: 'POST' }),
  getJobPullRequest: (repoId: number, jobId: number) =>
    request<PullRequest | null>(`/repositories/${repoId}/jobs/${jobId}/pull-request`),
  getRepositoryPullRequests: (repoId: number) =>
    request<PullRequest[]>(`/repositories/${repoId}/pull-requests`),
  refreshPullRequestStatus: (repoId: number, prId: number) =>
    request<PullRequest>(`/repositories/${repoId}/pull-requests/${prId}/refresh-status`, { method: 'POST' }),
};
