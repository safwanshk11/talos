export interface User {
  id: number;
  username: string;
  email?: string;
  avatar_url?: string;
  is_github_connected: boolean;
  github_username?: string;
  created_at: string;
}

export interface GitHubConnectionStatus {
  connected: boolean;
  github_username?: string;
  connected_at?: string;
  scopes?: string;
}

export interface LatestCommit {
  sha?: string;
  message?: string;
  author?: string;
  date?: string;
}

export interface Repository {
  id: number;
  user_id: number;
  github_repo_id: string;
  name: string;
  full_name: string;
  owner: string;
  default_branch: string;
  primary_language?: string;
  visibility: 'public' | 'private' | string;
  clone_url: string;
  html_url: string;
  latest_commit: LatestCommit;
  monitoring_status: 'active' | 'paused';
  connection_status: 'connected' | 'error' | 'syncing';
  last_checked_at: string;
  last_scanned_at?: string;
  created_at: string;
  updated_at: string;
}

export interface GitHubRepoImportItem {
  github_repo_id: string;
  name: string;
  full_name: string;
  owner: string;
  default_branch: string;
  primary_language?: string;
  visibility: string;
  clone_url: string;
  html_url: string;
  description?: string;
  is_connected: boolean;
}

export interface DashboardStats {
  total_repositories: number;
  active_monitoring_count: number;
  active_issues_count: number;
  verified_patches_count: number;
  awaiting_review_count: number;
}

// Phase 2 Entities
export interface RepositoryScan {
  id: number;
  repository_id: number;
  status: 'queued' | 'running' | 'completed' | 'failed';
  ecosystem?: string;
  total_dependencies: number;
  issues_detected: number;
  started_at: string;
  completed_at?: string;
  error_message?: string;
}

export interface MaintenanceIssue {
  id: number;
  repository_id: number;
  fingerprint?: string;
  title: string;
  description?: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN';
  category: string;
  status: 'OPEN' | 'ANALYZING' | 'PATCHING' | 'VERIFIED' | 'DELIVERED' | 'FAILED' | 'ESCALATED' | 'RESOLVED';
  package_name?: string;
  current_version?: string;
  affected_range?: string;
  recommended_version?: string;
  advisory_id?: string;
  source?: string;
  affected_files?: string[];
  details?: Record<string, any>;
  detected_at: string;
  last_seen_at: string;
  resolved_at?: string;
}

export interface RepositoryReadiness {
  id: number;
  repository_id: number;
  manifest_found: boolean;
  lockfile_found: boolean;
  build_script_found: boolean;
  test_script_found: boolean;
  lint_script_found: boolean;
  typecheck_script_found: boolean;
  ci_config_found: boolean;
  score_level: 'HIGH' | 'MEDIUM' | 'LOW';
  details?: Record<string, any>;
  updated_at: string;
}

export interface ActionLog {
  id: number;
  repository_id?: number;
  scan_id?: number;
  timestamp: string;
  step: string;
  message: string;
  level: string;
}
