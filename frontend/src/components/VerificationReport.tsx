import React, { useState } from 'react';
import { VerificationCheck, VerificationRunStatus } from '../types';
import { CheckCircle2, XCircle, MinusCircle, Clock, ChevronDown, ChevronUp, ShieldCheck, ShieldAlert } from 'lucide-react';

interface VerificationReportProps {
  status: VerificationRunStatus;
  checks: VerificationCheck[];
  sandboxId?: string;
}

const CHECK_LABELS: Record<string, string> = {
  INSTALL: 'Install Dependencies',
  BUILD: 'Build',
  TYPECHECK: 'Type Check',
  LINT: 'Lint',
  TEST: 'Tests',
  SECURITY_AUDIT: 'Security Audit',
  VULNERABILITY_RESCAN: 'Original Vulnerability',
};

const StatusPill: React.FC<{ status: string }> = ({ status }) => {
  const map: Record<string, { cls: string; icon: React.ReactNode; label: string }> = {
    PASSED: { cls: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/25', icon: <CheckCircle2 className="w-3.5 h-3.5" />, label: 'PASS' },
    FAILED: { cls: 'text-red-400 bg-red-500/10 border-red-500/25', icon: <XCircle className="w-3.5 h-3.5" />, label: 'FAIL' },
    SKIPPED: { cls: 'text-slate-400 bg-slate-800/60 border-subtle', icon: <MinusCircle className="w-3.5 h-3.5" />, label: 'SKIPPED' },
    TIMED_OUT: { cls: 'text-amber-400 bg-amber-500/10 border-amber-500/25', icon: <Clock className="w-3.5 h-3.5" />, label: 'TIMED OUT' },
    PENDING: { cls: 'text-slate-500 bg-slate-800/40 border-subtle', icon: <Clock className="w-3.5 h-3.5" />, label: 'PENDING' },
    RUNNING: { cls: 'text-blue-400 bg-blue-500/10 border-blue-500/25', icon: <Clock className="w-3.5 h-3.5 animate-spin" />, label: 'RUNNING' },
  };
  const cfg = map[status] || map.PENDING;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded border text-[11px] font-bold font-mono ${cfg.cls}`}>
      {cfg.icon}
      {cfg.label}
    </span>
  );
};

const CheckRow: React.FC<{ check: VerificationCheck }> = ({ check }) => {
  const [expanded, setExpanded] = useState(false);
  const label = CHECK_LABELS[check.type] || check.type;
  const hasOutput = !!(check.stdout_excerpt || check.stderr_excerpt);

  let subtext: string | null = null;
  if (check.type === 'VULNERABILITY_RESCAN' && check.check_metadata) {
    const m = check.check_metadata;
    if (m.reason) subtext = m.reason;
    else subtext = check.status === 'PASSED'
      ? `${m.package_name} ${m.previous_version} → ${m.verified_version}: advisory ${m.original_advisory_id} removed`
      : `${m.package_name} ${m.verified_version}: advisory ${m.original_advisory_id} still present`;
  } else if (check.type === 'SECURITY_AUDIT' && check.check_metadata?.vulnerability_counts) {
    const c = check.check_metadata.vulnerability_counts;
    subtext = `${c.critical || 0} critical, ${c.high || 0} high, ${c.moderate || 0} moderate, ${c.low || 0} low`;
  } else if (check.status === 'SKIPPED' && check.check_metadata?.reason) {
    subtext = check.check_metadata.reason;
  } else if (check.command) {
    subtext = check.command;
  }

  return (
    <div className="rounded-lg border border-subtle overflow-hidden">
      <button
        onClick={() => hasOutput && setExpanded((v) => !v)}
        className={`w-full flex items-center justify-between p-3 bg-slate-950/50 text-left ${hasOutput ? 'hover:bg-slate-900/60 cursor-pointer' : 'cursor-default'}`}
      >
        <div className="flex items-center gap-2.5 overflow-hidden">
          {hasOutput && (expanded ? <ChevronUp className="w-3.5 h-3.5 text-slate-500 shrink-0" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-500 shrink-0" />)}
          <div className="overflow-hidden">
            <div className="text-sm font-semibold text-slate-200 font-mono">{label}</div>
            {subtext && <div className="text-[11px] text-slate-500 font-mono truncate">{subtext}</div>}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0 pl-2">
          {check.duration_ms != null && <span className="text-[10px] text-slate-500 font-mono">{check.duration_ms}ms</span>}
          <StatusPill status={check.status} />
        </div>
      </button>
      {expanded && hasOutput && (
        <div className="p-3 bg-slate-950/80 border-t border-subtle font-mono text-[11px] space-y-2 max-h-56 overflow-y-auto">
          {check.stdout_excerpt && (
            <div>
              <div className="text-slate-500 mb-1">stdout</div>
              <pre className="whitespace-pre-wrap text-slate-300">{check.stdout_excerpt}</pre>
            </div>
          )}
          {check.stderr_excerpt && (
            <div>
              <div className="text-slate-500 mb-1">stderr</div>
              <pre className="whitespace-pre-wrap text-red-300/90">{check.stderr_excerpt}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export const VerificationReport: React.FC<VerificationReportProps> = ({ status, checks, sandboxId }) => {
  const verified = status === 'verified';
  const failed = status === 'verification_failed';

  return (
    <div className="space-y-3">
      <div
        className={`p-3.5 rounded-lg border flex items-center gap-2.5 font-mono text-sm font-semibold ${
          verified
            ? 'bg-emerald-500/10 border-emerald-500/25 text-emerald-400'
            : failed
            ? 'bg-red-500/10 border-red-500/25 text-red-400'
            : 'bg-slate-800/40 border-subtle text-slate-300'
        }`}
      >
        {verified ? <ShieldCheck className="w-4 h-4" /> : <ShieldAlert className="w-4 h-4" />}
        <span>Result: {verified ? 'VERIFIED' : failed ? 'REJECTED' : status.toUpperCase()}</span>
        {sandboxId && <span className="ml-auto text-[10px] text-slate-500 font-normal">sandbox {sandboxId}</span>}
      </div>

      <div className="space-y-2">
        {checks.map((check) => (
          <CheckRow key={check.id} check={check} />
        ))}
      </div>
    </div>
  );
};
