import React, { useEffect, useState } from 'react';
import { MaintenanceIssue, MaintenanceJob, ActionLog } from '../types';
import { api } from '../services/api';
import { DiffViewer } from './DiffViewer';
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
  { key: 'patching', label: 'PATCHING', statuses: ['patching', 'patch_ready'] },
  { key: 'verifying', label: 'VERIFYING', statuses: [] },
  { key: 'delivering', label: 'DELIVERING', statuses: [] },
];

const STEP_ORDER = ['analyzing', 'planning', 'sandboxing', 'patching'];

export const IssueDetailModal: React.FC<IssueDetailModalProps> = ({ issue, repoId, onClose, onJobUpdated }) => {
  const [job, setJob] = useState<MaintenanceJob | null>(null);
  const [preparing, setPreparing] = useState(false);
  const [prepareError, setPrepareError] = useState<string | null>(null);
  const [jobLogs, setJobLogs] = useState<ActionLog[]>([]);
  const [showLogs, setShowLogs] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    if (!issue) return;
    setJob(null);
    setPrepareError(null);
    setJobLogs([]);
    setLoadingHistory(true);
    api
      .getIssueJobs(repoId, issue.id)
      .then((jobs) => {
        if (jobs.length > 0) setJob(jobs[0]);
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

  const activeStepKey = (() => {
    if (!job) return preparing ? 'analyzing' : null;
    for (const step of PIPELINE_STEPS) {
      if (step.statuses.includes(job.status)) return step.key;
    }
    return null;
  })();

  const activeStepIndex = activeStepKey ? STEP_ORDER.indexOf(activeStepKey) : -1;
  const isTerminal = job && ['patch_ready', 'failed', 'escalated'].includes(job.status);
  const canPrepareFix = !preparing && (!job || isTerminal);

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
                const disabled = stepIndex === -1;
                const isActive = step.key === activeStepKey;
                const isDone = !disabled && activeStepIndex > stepIndex && !isActive;
                const isPatchReady = job?.status === 'patch_ready' && step.key === 'patching';

                let cls = 'bg-slate-950/50 border-subtle text-slate-600';
                if (disabled) {
                  cls = 'bg-slate-950/30 border-subtle text-slate-700';
                } else if (isActive) {
                  cls = 'bg-blue-500/10 border-blue-500/40 text-blue-300';
                } else if (isDone || isPatchReady) {
                  cls = 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400';
                }

                return (
                  <div key={step.key} className={`p-2 rounded border text-center uppercase tracking-wide ${cls}`}>
                    <div className="flex items-center justify-center gap-1">
                      {isActive && <Loader2 className="w-3 h-3 animate-spin" />}
                      {(isDone || isPatchReady) && <CheckCircle2 className="w-3 h-3" />}
                      <span>{step.label}</span>
                    </div>
                    {disabled && <span className="block text-[9px] normal-case text-slate-700">Phase 4/5</span>}
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

            {job?.status === 'patch_ready' && latestAttempt?.plan && (
              <div className="space-y-4">
                <div className="p-3.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-300 font-mono">
                  <strong>Patch prepared. Awaiting verification.</strong> This patch is untrusted until Phase 4 verifies it — TALOS has not proven it works yet.
                </div>

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
            {job?.status === 'patch_ready' ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                <span>Patch untrusted — Verification (Phase 4) not yet run</span>
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
            <button
              onClick={handlePrepareFix}
              disabled={!canPrepareFix}
              title={job?.status === 'patch_ready' ? 'Re-run to generate a new patch attempt' : 'Run the real Phase 3 planning + patch generation workflow'}
              className="btn btn-primary text-xs flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {preparing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Wrench className="w-3.5 h-3.5" />}
              <span>
                {preparing
                  ? 'TALOS Working...'
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
