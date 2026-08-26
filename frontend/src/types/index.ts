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
  connection_status: 'connected' | 'error' | 'syncing' | 'disconnected';
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

export type MaintenanceIssueStatus =
  | 'OPEN'
  | 'ANALYZING'
  | 'PLANNING'
  | 'PLANNED'
  | 'SANDBOXING'
  | 'PATCHING'
  | 'PATCH_READY'
  | 'VERIFYING'
  | 'VERIFIED'
  | 'VERIFICATION_FAILED'
  | 'DELIVERED'
  | 'FAILED'
  | 'ESCALATED'
  | 'RESOLVED'
  | 'APPROVAL_REQUIRED'
  | 'IGNORED'
  | 'REJECTED_BY_USER';

export interface MaintenanceIssue {
  id: number;
  repository_id: number;
  fingerprint?: string;
  title: string;
  description?: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN';
  category: string;
  status: MaintenanceIssueStatus;
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

// Phase 3 Entities

export interface MaintenancePlan {
  summary: string;
  root_cause: string;
  target_version: string;
  requires_code_changes: boolean;
  files_to_modify: string[];
  actions: string[];
  verification_recommendations: string[];
  risk: 'LOW' | 'MEDIUM' | 'HIGH';
  risk_reason: string;
  escalate: boolean;
  escalation_reason: string;
}

export interface ProblemAnalysis {
  root_cause: string;
  affected_component: string;
  reasoning: string;
  missing_information: string[];
  escalation_required: boolean;
  escalation_reason: string;
}

export interface PatchAttempt {
  id: number;
  job_id: number;
  attempt_number: number;
  branch_name: string;
  commit_sha?: string;
  status: 'created' | 'ready' | 'failed' | 'escalated';
  ai_provider?: string;
  ai_model?: string;
  analysis?: ProblemAnalysis;
  plan?: MaintenancePlan;
  files_modified?: string[];
  patch_diff?: string;
  failure_reason?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export type MaintenanceJobStatus =
  | 'analyzing'
  | 'planning'
  | 'planned'
  | 'sandboxing'
  | 'patching'
  | 'patch_ready'
  | 'verifying'
  | 'verified'
  | 'verification_failed'
  | 'delivering'
  | 'delivered'
  | 'delivery_failed'
  | 'resolved'
  | 'failed'
  | 'escalated'
  | 'waiting_for_approval'
  | 'blocked_conflict'
  | 'ignored'
  | 'rejected';

// Phase 6.5: Decision Engine & Autonomy Governance
export type DecisionType = 'AUTO_EXECUTE' | 'PREPARE_ONLY' | 'APPROVAL_REQUIRED' | 'ESCALATE' | 'IGNORE' | 'BLOCKED_BY_CONFLICT';
export type AutomationMode = 'CONSERVATIVE' | 'BALANCED' | 'AUTONOMOUS';
export type TierAction = 'AUTO_EXECUTE' | 'PREPARE_ONLY' | 'APPROVAL_REQUIRED' | 'ESCALATE';

export interface AutomationPolicy {
  id: number;
  repository_id: number;
  mode: AutomationMode;
  security_patch_action: TierAction;
  patch_update_action: TierAction;
  minor_update_action: TierAction;
  major_update_action: TierAction;
  protected_path_action: TierAction;
  protected_paths: string[];
  updated_at: string;
}

export interface MaintenanceJob {
  id: number;
  repository_id: number;
  issue_id?: number;
  status: MaintenanceJobStatus;
  risk_level?: 'low' | 'medium' | 'high';
  risk_reason?: string;
  decision?: DecisionType;
  decision_reason?: string;
  decision_policy?: string;
  decision_matched_rules?: string[];
  decision_blocked_by?: string[];
  requires_approval: boolean;
  approved_at?: string;
  rejected_at?: string;
  rejection_reason?: string;
  blocking_job_id?: number;
  created_at: string;
  completed_at?: string;
  attempts: PatchAttempt[];
}

// Phase 4 Entities

export type VerificationCheckType =
  | 'INSTALL'
  | 'BUILD'
  | 'TYPECHECK'
  | 'LINT'
  | 'TEST'
  | 'SECURITY_AUDIT'
  | 'VULNERABILITY_RESCAN';

export type VerificationCheckStatus = 'PENDING' | 'RUNNING' | 'PASSED' | 'FAILED' | 'SKIPPED' | 'TIMED_OUT';

export interface VerificationCheck {
  id: number;
  verification_run_id: number;
  type: VerificationCheckType;
  command?: string;
  status: VerificationCheckStatus;
  exit_code?: number;
  duration_ms?: number;
  stdout_excerpt?: string;
  stderr_excerpt?: string;
  check_metadata?: Record<string, any>;
  order_index: number;
  started_at?: string;
  completed_at?: string;
}

export type VerificationRunStatus = 'pending' | 'running' | 'verified' | 'verification_failed' | 'failed' | 'cancelled';

export interface VerificationRun {
  id: number;
  maintenance_job_id?: number;
  patch_attempt_id: number;
  status: VerificationRunStatus;
  sandbox_id?: string;
  started_at?: string;
  completed_at?: string;
  checks: VerificationCheck[];
}

// Phase 5 Entities

export type PullRequestStatus = 'pending' | 'committing' | 'pushing' | 'creating_pr' | 'delivered' | 'delivery_failed' | 'escalated';
export type GithubPrStatus = 'open' | 'merged' | 'closed';

export interface PullRequest {
  id: number;
  repository_id: number;
  maintenance_job_id: number;
  patch_attempt_id?: number;
  verification_run_id?: number;
  base_branch?: string;
  head_branch?: string;
  commit_sha?: string;
  title?: string;
  pr_number?: number;
  pr_url?: string;
  status: PullRequestStatus;
  github_status?: GithubPrStatus;
  failure_reason?: string;
  created_at: string;
  updated_at?: string;
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

export interface HealthStatus {
  status: string;
  service: string;
  database: string;
  version: string;
  ai_provider: string;
  ai_model: string;
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
