import React, { useEffect, useState } from 'react';
import { MaintenanceIssue, MaintenanceJob, ActionLog, VerificationRun, PullRequest } from '../types';
import { api } from '../services/api';
import { DiffViewer } from './DiffViewer';
import { VerificationReport } from './VerificationReport';
import {
  X,
  ShieldAlert,
  FileCode2,
  ExternalLink,
  Wrench,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  GitBranch,
  Bot,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  GitPullRequest,
} from 'lucide-react';

interface IssueDetailModalProps {
  issue: MaintenanceIssue | null;
  repoId: number;
  onClose: () => void;
  onJobUpdated?: () => void;
}

const PIPELINE_STEPS: { key: string; label: string; statuses: string[] }[] = [
  { key: 'analyzing', label: 'ANALYZING', statuses: ['analyzing'] },
  { key: 'planning', label: 'PLANNING', statuses: ['planning', 'planned'] },
  { key: 'sandboxing', label: 'CREATING WORKSPACE', statuses: ['sandboxing'] },
  { key: 'patching', label: 'PATCHING', statuses: ['patching', 'patch_ready', 'resolved'] },
  { key: 'verifying', label: 'VERIFYING', statuses: ['verifying', 'verified', 'verification_failed'] },
  { key: 'delivering', label: 'DELIVERING', statuses: ['delivering', 'delivered', 'delivery_failed'] },
];

const STEP_ORDER = ['analyzing', 'planning', 'sandboxing', 'patching', 'verifying', 'delivering'];
const TERMINAL_JOB_STATUSES = ['patch_ready', 'verified', 'verification_failed', 'delivered', 'delivery_failed', 'resolved', 'failed', 'escalated'];

export const IssueDetailModal: React.FC<IssueDetailModalProps> = ({ issue, repoId, onClose, onJobUpdated }) => {
  const [job, setJob] = useState<MaintenanceJob | null>(null);
  const [preparing, setPreparing] = useState(false);
  const [prepareError, setPrepareError] = useState<string | null>(null);
  const [jobLogs, setJobLogs] = useState<ActionLog[]>([]);
  const [showLogs, setShowLogs] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const [verificationRun, setVerificationRun] = useState<VerificationRun | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);

  const [pullRequest, setPullRequest] = useState<PullRequest | null>(null);
  const [delivering, setDelivering] = useState(false);
  const [deliverError, setDeliverError] = useState<string | null>(null);

  const loadLatestVerificationRun = async (jobId: number) => {
    try {
      const runs = await api.getVerificationRuns(repoId, jobId);
      setVerificationRun(runs.length > 0 ? runs[0] : null);
    } catch {
      // non-fatal
    }
  };

  const loadLatestPullRequest = async (jobId: number) => {
    try {
      const pr = await api.getJobPullRequest(repoId, jobId);
      setPullRequest(pr);
    } catch {
      // non-fatal
    }
  };

  useEffect(() => {
    if (!issue) return;
    setJob(null);
    setPrepareError(null);
    setVerificationRun(null);
    setVerifyError(null);
    setPullRequest(null);
    setDeliverError(null);
    setJobLogs([]);
    setLoadingHistory(true);
    api
      .getIssueJobs(repoId, issue.id)
      .then(async (jobs) => {
        if (jobs.length > 0) {
          setJob(jobs[0]);
          await loadLatestVerificationRun(jobs[0].id);
          await loadLatestPullRequest(jobs[0].id);
        }
      })
      .catch(() => {})
      .finally(() => setLoadingHistory(false));
  }, [issue, repoId]);

  if (!issue) return null;

  const severityColor =
    issue.severity === 'CRITICAL'
      ? 'bg-red-500/15 text-red-400 border-red-500/30'
      : issue.severity === 'HIGH'
      ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
      : 'bg-blue-500/15 text-blue-400 border-blue-500/30';

  const latestAttempt = job?.attempts?.[job.attempts.length - 1];

  const fetchJobLogs = async (jobId: number) => {
    try {
      const logs = await api.getLogs(repoId);
      setJobLogs(logs.filter((l) => (l as any).job_id === jobId));
    } catch {
      // non-fatal
    }
  };

  const handlePrepareFix = async () => {
    setPreparing(true);
    setPrepareError(null);
    setVerificationRun(null);
    setVerifyError(null);
    setPullRequest(null);
    setDeliverError(null);
    try {
      const result = await api.prepareFix(repoId, issue.id);
      setJob(result);
      await fetchJobLogs(result.id);
      onJobUpdated?.();
    } catch (err: any) {
      setPrepareError(err.message || 'Prepare fix failed.');
    } finally {
      setPreparing(false);
    }
  };

  const handleRunVerification = async () => {
    if (!job) return;
    setVerifying(true);
    setVerifyError(null);
    try {
      const run = await api.runVerification(repoId, job.id);
      setVerificationRun(run);
      const updatedJob = await api.getJobDetail(repoId, job.id);
      setJob(updatedJob);
      await fetchJobLogs(job.id);
      onJobUpdated?.();
    } catch (err: any) {
      setVerifyError(err.message || 'Verification failed to run.');
    } finally {
      setVerifying(false);
    }
  };

  const handleDeliver = async () => {
    if (!job) return;
    setDelivering(true);
    setDeliverError(null);
    try {
      const pr = await api.deliverPatch(repoId, job.id);
      setPullRequest(pr);
      const updatedJob = await api.getJobDetail(repoId, job.id);
      setJob(updatedJob);
      await fetchJobLogs(job.id);
      onJobUpdated?.();
    } catch (err: any) {
      setDeliverError(err.message || 'Delivery failed to run.');
      try {
        const updatedJob = await api.getJobDetail(repoId, job.id);
        setJob(updatedJob);
      } catch {
        // non-fatal
      }
    } finally {
      setDelivering(false);
    }
  };

  const activeStepKey = (() => {
    if (!job) return preparing ? 'analyzing' : null;
    if (delivering) return 'delivering';
    if (verifying) return 'verifying';
    for (const step of PIPELINE_STEPS) {
      if (step.statuses.includes(job.status)) return step.key;
    }
    return null;
  })();

  const activeStepIndex = activeStepKey ? STEP_ORDER.indexOf(activeStepKey) : -1;
  const isTerminal = job && TERMINAL_JOB_STATUSES.includes(job.status);
  const canPrepareFix = !preparing && !verifying && !delivering && (!job || isTerminal);
  const canRunVerification = !!job && !preparing && !verifying && !delivering && job.status === 'patch_ready';
  const canDeliver = !!job && !preparing && !verifying && !delivering && (job.status === 'verified' || job.status === 'delivery_failed');

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 select-none">
      <div className="bg-card border border-subtle w-full max-w-2xl rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-5 border-b border-subtle flex items-center justify-between bg-slate-900/50 shrink-0">
          <div className="flex items-center gap-3 overflow-hidden pr-2">
            <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 shrink-0">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div className="overflow-hidden">
              <div className="flex items-center gap-2">
                <span className={`badge ${severityColor} font-mono text-[10px]`}>
                  {issue.severity}
                </span>
                <span className="badge badge-gray text-[10px] uppercase font-mono">
                  {issue.source || 'OSV Advisory'}
                </span>
                <span className="badge badge-gray text-[10px] uppercase font-mono">
                  {issue.status}
                </span>
              </div>
              <h2 className="text-base font-semibold text-slate-100 truncate font-mono mt-1">
                {issue.title}
              </h2>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-slate-200 shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono">
            <div className="p-3 rounded bg-slate-950/60 border border-subtle/70">
              <span className="text-slate-500 block text-[11px] mb-1">PACKAGE NAME</span>
              <span className="text-slate-200 font-bold text-sm">{issue.package_name || 'N/A'}</span>
            </div>

            <div className="p-3 rounded bg-slate-950/60 border border-subtle/70">
              <span className="text-slate-500 block text-[11px] mb-1">INSTALLED VERSION</span>
              <span className="text-amber-400 font-bold text-sm">{issue.current_version || 'N/A'}</span>
            </div>

            <div className="p-3 rounded bg-slate-950/60 border border-subtle/70">
              <span className="text-slate-500 block text-[11px] mb-1">AFFECTED RANGE</span>
              <span className="text-slate-300 font-medium text-xs">{issue.affected_range || 'N/A'}</span>
            </div>

            <div className="p-3 rounded bg-slate-950/60 border border-subtle/70">
              <span className="text-slate-500 block text-[11px] mb-1">RECOMMENDED FIX</span>
              <span className="text-emerald-400 font-bold text-sm">{issue.recommended_version || 'Latest'}</span>
            </div>
          </div>

          {/* Advisory Info */}
          {issue.advisory_id && (
            <div className="p-3.5 rounded-lg bg-slate-950/40 border border-subtle font-mono text-slate-300 flex items-center justify-between">
              <span>Advisory Identifier: <strong>{issue.advisory_id}</strong></span>
              <a
                href={`https://github.com/advisories/${issue.advisory_id}`}
                target="_blank"
                rel="noreferrer"
                className="text-blue-400 hover:underline flex items-center gap-1 text-[11px]"
              >
                <span>View Advisory</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          )}

          {/* Description */}
          <div className="space-y-2">
            <h3 className="font-semibold text-slate-200 font-mono uppercase text-[11px] text-slate-400">
              VULNERABILITY DESCRIPTION
            </h3>
            <div className="p-4 rounded-lg bg-slate-950/60 border border-subtle text-slate-300 leading-relaxed max-h-40 overflow-y-auto font-mono whitespace-pre-wrap">
              {issue.description || 'No detailed vulnerability description provided.'}
            </div>
          </div>

          {/* Affected Source Files List */}
          <div className="space-y-2">
            <div className="flex items-center justify-between font-mono text-[11px]">
              <span className="font-semibold text-slate-400 uppercase flex items-center gap-1.5">
                <FileCode2 className="w-3.5 h-3.5 text-blue-400" />
                DIRECT REPOSITORY REFERENCES ({issue.affected_files?.length || 0})
              </span>
            </div>

            {!issue.affected_files || issue.affected_files.length === 0 ? (
              <div className="p-3 rounded bg-slate-950/40 border border-subtle text-slate-500 italic font-mono">
                No direct import/require references found in source code files. (Indirect/transitive dependency)
              </div>
            ) : (
              <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                {issue.affected_files.map((filePath, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded bg-slate-950/60 border border-subtle text-slate-200 font-mono flex items-center justify-between"
                  >
                    <span>{filePath}</span>
                    <span className="text-[10px] text-slate-500 uppercase">Source File</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Phase 3: TALOS Fix Pipeline */}
          <div className="space-y-3 border-t border-subtle pt-5">
            <h3 className="font-semibold text-slate-200 font-mono uppercase text-[11px] flex items-center gap-1.5">
              <Bot className="w-3.5 h-3.5 text-blue-400" />
              TALOS FIX PIPELINE
            </h3>

            {/* Step tracker */}
            <div className="grid grid-cols-3 md:grid-cols-6 gap-2 font-mono text-[10px]">
              {PIPELINE_STEPS.map((step) => {
                const stepIndex = STEP_ORDER.indexOf(step.key);
                const isActive = step.key === activeStepKey && (preparing || verifying || delivering || job?.status === 'verifying' || job?.status === 'delivering');
                const isDone = activeStepIndex > stepIndex && !isActive;
                const isPatchReady = job?.status === 'patch_ready' && step.key === 'patching';
                const isVerified = (job?.status === 'verified' || job?.status === 'delivering' || job?.status === 'delivered' || job?.status === 'delivery_failed') && step.key === 'verifying';
                const isVerificationFailed = job?.status === 'verification_failed' && step.key === 'verifying';
                const isDelivered = job?.status === 'delivered' && step.key === 'delivering';
                const isDeliveryFailed = job?.status === 'delivery_failed' && step.key === 'delivering';

                let cls = 'bg-slate-950/50 border-subtle text-slate-600';
                if (isVerificationFailed || isDeliveryFailed) {
                  cls = 'bg-red-500/10 border-red-500/30 text-red-400';
                } else if (isActive) {
                  cls = 'bg-blue-500/10 border-blue-500/40 text-blue-300';
                } else if (isDone || isPatchReady || isVerified || isDelivered) {
                  cls = 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400';
                }

                return (
                  <div key={step.key} className={`p-2 rounded border text-center uppercase tracking-wide ${cls}`}>
                    <div className="flex items-center justify-center gap-1">
                      {isActive && <Loader2 className="w-3 h-3 animate-spin" />}
                      {(isDone || isPatchReady || isVerified || isDelivered) && <CheckCircle2 className="w-3 h-3" />}
                      {(isVerificationFailed || isDeliveryFailed) && <XCircle className="w-3 h-3" />}
                      <span>{step.label}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {loadingHistory && (
              <div className="text-slate-500 italic font-mono text-[11px]">Checking prior fix attempts...</div>
            )}

            {prepareError && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 flex items-center gap-2 font-mono">
                <XCircle className="w-4 h-4 shrink-0" />
                <span>{prepareError}</span>
              </div>
            )}

            {job?.status === 'escalated' && (
              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-start gap-2 font-mono">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold">ESCALATED — human review required</div>
                  <div className="text-slate-300 mt-1">{job.risk_reason || latestAttempt?.failure_reason || 'TALOS determined this change requires human judgment.'}</div>
                </div>
              </div>
            )}

            {job?.status === 'failed' && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 flex items-start gap-2 font-mono">
                <XCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold">PATCH GENERATION FAILED</div>
                  <div className="text-slate-300 mt-1">{latestAttempt?.failure_reason || 'Unknown failure.'}</div>
                </div>
              </div>
            )}

            {job?.status === 'resolved' && (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-start gap-2 font-mono">
                <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold">ALREADY RESOLVED — NO PATCH NEEDED</div>
                  <div className="text-slate-300 mt-1">
                    TALOS re-checked the repository's default branch and confirmed (via a real OSV re-query) that
                    this advisory is no longer present — most likely already fixed directly on the default branch.
                    No patch was generated because none was needed.
                  </div>
                </div>
              </div>
            )}

            {verifyError && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 flex items-center gap-2 font-mono">
                <XCircle className="w-4 h-4 shrink-0" />
                <span>{verifyError}</span>
              </div>
            )}

            {deliverError && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 flex items-center gap-2 font-mono">
                <XCircle className="w-4 h-4 shrink-0" />
                <span>{deliverError}</span>
              </div>
            )}

            {['patch_ready', 'verifying', 'verified', 'verification_failed', 'delivering', 'delivered', 'delivery_failed'].includes(job?.status || '') && latestAttempt?.plan && (
              <div className="space-y-4">
                {job?.status === 'patch_ready' && (
                  <div className="p-3.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-300 font-mono">
                    <strong>Patch prepared. Awaiting verification.</strong> This patch is untrusted until Phase 4 verifies it — TALOS has not proven it works yet.
                  </div>
                )}
                {job?.status === 'verified' && (
                  <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 font-mono flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 shrink-0" />
                    <span><strong>Verified.</strong> Real build/test/security checks passed and the original vulnerability is confirmed removed.</span>
                  </div>
                )}
                {job?.status === 'verification_failed' && (
                  <div className="p-3.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-300 font-mono flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 shrink-0" />
                    <span><strong>Rejected.</strong> Verification found a real failure — see the report below. TALOS will not claim this issue is fixed.</span>
                  </div>
                )}
                {job?.status === 'delivered' && pullRequest?.pr_url && (
                  <div className="p-3.5 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-300 font-mono space-y-2">
                    <div className="flex items-center gap-2">
                      <GitPullRequest className="w-4 h-4 shrink-0" />
                      <span><strong>Delivered.</strong> Pull request #{pullRequest.pr_number} created from the exact verified commit. Human review required before merge.</span>
                    </div>
                    <a
                      href={pullRequest.pr_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1.5 text-blue-400 hover:underline text-[11px]"
                    >
                      <span>View on GitHub</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                )}
                {job?.status === 'delivery_failed' && (
                  <div className="p-3.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-300 font-mono">
                    <div className="flex items-center gap-2">
                      <XCircle className="w-4 h-4 shrink-0" />
                      <strong>Delivery failed.</strong>
                    </div>
                    <p className="text-slate-300 mt-1">{pullRequest?.failure_reason || 'The verified patch could not be delivered. Safe to retry.'}</p>
                  </div>
                )}

                {/* Plan View */}
                <div className="space-y-2">
                  <h4 className="font-semibold text-slate-300 font-mono uppercase text-[11px]">TALOS Analysis</h4>
                  <div className="p-3 rounded bg-slate-950/60 border border-subtle text-slate-300 font-mono whitespace-pre-wrap">
                    {latestAttempt.plan.summary}
                  </div>
                </div>

                <div className="space-y-2">
                  <h4 className="font-semibold text-slate-300 font-mono uppercase text-[11px]">Proposed Change</h4>
                  <ul className="list-disc list-inside space-y-1 p-3 rounded bg-slate-950/60 border border-subtle text-slate-300 font-mono">
                    {latestAttempt.plan.actions.map((action, idx) => (
                      <li key={idx}>{action}</li>
                    ))}
                  </ul>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <h4 className="font-semibold text-slate-300 font-mono uppercase text-[11px]">Files ({latestAttempt.files_modified?.length || 0})</h4>
                    <div className="p-3 rounded bg-slate-950/60 border border-subtle text-slate-300 font-mono space-y-1 max-h-28 overflow-y-auto">
                      {(latestAttempt.files_modified || []).map((f, idx) => (
                        <div key={idx} className="flex items-center gap-1.5">
                          <FileCode2 className="w-3 h-3 text-blue-400 shrink-0" />
                          <span>{f}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <h4 className="font-semibold text-slate-300 font-mono uppercase text-[11px]">Risk</h4>
                    <div className="p-3 rounded bg-slate-950/60 border border-subtle font-mono space-y-1">
                      <span className={`badge ${latestAttempt.plan.risk === 'HIGH' ? 'badge-amber' : latestAttempt.plan.risk === 'MEDIUM' ? 'badge-blue' : 'badge-green'}`}>
                        {latestAttempt.plan.risk}
                      </span>
                      <p className="text-slate-400 text-[11px]">{latestAttempt.plan.risk_reason}</p>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <h4 className="font-semibold text-slate-300 font-mono uppercase text-[11px]">Verification Plan (Phase 4)</h4>
                  <div className="flex flex-wrap gap-1.5">
                    {latestAttempt.plan.verification_recommendations.map((v, idx) => (
                      <span key={idx} className="badge badge-gray text-[10px] uppercase">{v}</span>
                    ))}
                  </div>
                </div>

                <div className="space-y-2">
                  <h4 className="font-semibold text-slate-300 font-mono uppercase text-[11px] flex items-center gap-1.5">
                    <GitBranch className="w-3.5 h-3.5 text-blue-400" />
                    Diff — {latestAttempt.branch_name}
                  </h4>
                  <DiffViewer diff={latestAttempt.patch_diff || ''} />
                </div>

                {verificationRun && (
                  <div className="space-y-2">
                    <h4 className="font-semibold text-slate-300 font-mono uppercase text-[11px] flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
                      Verification Report
                    </h4>
                    <VerificationReport
                      status={verificationRun.status}
                      checks={verificationRun.checks}
                      sandboxId={verificationRun.sandbox_id}
                    />
                  </div>
                )}
              </div>
            )}

            {/* Execution Ledger */}
            {(jobLogs.length > 0) && (
              <div className="space-y-2">
                <button
                  onClick={() => setShowLogs((v) => !v)}
                  className="flex items-center gap-1.5 text-slate-400 hover:text-slate-200 font-mono text-[11px] uppercase"
                >
                  {showLogs ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  Execution Ledger ({jobLogs.length})
                </button>
                {showLogs && (
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {jobLogs.map((log) => (
                      <div key={log.id} className="p-2 rounded bg-slate-950/60 border border-subtle flex items-start gap-2 text-[11px] font-mono">
                        <span className="text-slate-500 text-[10px] shrink-0 pt-0.5">
                          {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </span>
                        <span className="px-1.5 py-0.5 rounded bg-slate-800 text-blue-400 font-semibold shrink-0">{log.step}</span>
                        <span className="text-slate-200">{log.message}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-subtle bg-slate-900/50 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2 text-slate-500 font-mono text-[11px]">
            {job?.status === 'delivered' ? (
              <>
                <GitPullRequest className="w-3.5 h-3.5 text-purple-400" />
                <span>Delivered as a real GitHub pull request — TALOS never merges</span>
              </>
            ) : job?.status === 'delivery_failed' ? (
              <>
                <XCircle className="w-3.5 h-3.5 text-red-500" />
                <span>Delivery failed — the verified patch is untouched, safe to retry</span>
              </>
            ) : job?.status === 'verified' ? (
              <>
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                <span>Verified by real build/test/security checks — not AI confidence</span>
              </>
            ) : job?.status === 'verification_failed' ? (
              <>
                <ShieldAlert className="w-3.5 h-3.5 text-red-500" />
                <span>Rejected — a real deterministic check failed</span>
              </>
            ) : job?.status === 'patch_ready' ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                <span>Patch untrusted — verification not yet run</span>
              </>
            ) : job?.status === 'resolved' ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                <span>Already resolved on the default branch — confirmed via OSV, not assumed</span>
              </>
            ) : (
              <>
                <Wrench className="w-3.5 h-3.5 text-slate-500" />
                <span>Real AI-generated patch — reviewed against Phase 2 findings only</span>
              </>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button onClick={onClose} className="btn btn-secondary text-xs">
              Close
            </button>
            {canRunVerification && (
              <button
                onClick={handleRunVerification}
                disabled={verifying}
                title="Run the real Phase 4 verification pipeline: isolated sandbox, deterministic checks, and a re-scan of the original vulnerability"
                className="btn btn-primary text-xs flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {verifying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                <span>{verifying ? 'Verifying...' : 'Run Verification'}</span>
              </button>
            )}
            {canDeliver && (
              <button
                onClick={handleDeliver}
                disabled={delivering}
                title="Push the exact verified commit on its TALOS branch and open a real GitHub pull request. TALOS never merges."
                className="btn btn-primary text-xs flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {delivering ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <GitPullRequest className="w-3.5 h-3.5" />}
                <span>{delivering ? 'Delivering...' : job?.status === 'delivery_failed' ? 'Retry Delivery' : 'Create Pull Request'}</span>
              </button>
            )}
            <button
              onClick={handlePrepareFix}
              disabled={!canPrepareFix}
              title={job ? 'Re-run to generate a new patch attempt' : 'Run the real Phase 3 planning + patch generation workflow'}
              className={`btn text-xs flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed ${canRunVerification || canDeliver ? 'btn-secondary' : 'btn-primary'}`}
            >
              {preparing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Wrench className="w-3.5 h-3.5" />}
              <span>
                {preparing
                  ? 'TALOS Working...'
                  : job?.status === 'verified' || job?.status === 'verification_failed' || job?.status === 'delivered' || job?.status === 'delivery_failed'
                  ? 'Prepare New Fix'
                  : job?.status === 'patch_ready'
                  ? 'Regenerate Fix'
                  : job?.status === 'escalated' || job?.status === 'failed'
                  ? 'Retry Prepare Fix'
                  : 'Prepare Fix'}
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
