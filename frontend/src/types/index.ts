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
