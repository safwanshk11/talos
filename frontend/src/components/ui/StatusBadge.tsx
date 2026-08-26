import React from 'react';

export type StatusTone = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'purple';

const TONE_CLASSES: Record<StatusTone, string> = {
  success: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25',
  warning: 'bg-amber-500/10 text-amber-400 border-amber-500/25',
  danger: 'bg-red-500/10 text-red-400 border-red-500/25',
  info: 'bg-blue-500/10 text-blue-400 border-blue-500/25',
  purple: 'bg-purple-500/10 text-purple-400 border-purple-500/25',
  neutral: 'bg-white/[0.05] text-text-secondary border-subtle',
};

/** Maps common backend status/severity strings to a visual tone. Extend rather
 * than special-case callers — this is the one place status→color logic lives. */
export function toneForStatus(status: string): StatusTone {
  const s = status.toUpperCase();
  if (['VERIFIED', 'PASSED', 'ACTIVE', 'CONNECTED', 'DELIVERED', 'RESOLVED', 'MERGED'].includes(s)) return 'success';
  if (['FAILED', 'VERIFICATION_FAILED', 'DELIVERY_FAILED', 'CRITICAL', 'HIGH', 'ERROR', 'CLOSED'].includes(s)) return 'danger';
  // Bare "OPEN" always means a MaintenanceIssue still needs action in this
  // app's vocabulary — never treat it as a success/closed-out state.
  if (['OPEN', 'PAUSED', 'MEDIUM', 'PENDING', 'ESCALATED', 'TIMED_OUT', 'WARNING', 'APPROVAL_REQUIRED', 'WAITING_FOR_APPROVAL', 'BLOCKED_CONFLICT', 'BLOCKED_BY_CONFLICT'].includes(s)) return 'warning';
  if (['ANALYZING', 'PLANNING', 'PATCHING', 'VERIFYING', 'DELIVERING', 'RUNNING', 'SANDBOXING', 'AUTO_EXECUTE', 'PREPARE_ONLY'].includes(s)) return 'info';
  if (['IGNORED', 'REJECTED', 'REJECTED_BY_USER'].includes(s)) return 'neutral';
  return 'neutral';
}

interface StatusBadgeProps {
  label: string;
  tone?: StatusTone;
  dot?: boolean;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ label, tone, dot, className = '' }) => {
  const resolvedTone = tone ?? toneForStatus(label);
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-semibold font-mono ${TONE_CLASSES[resolvedTone]} ${className}`}>
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${resolvedTone === 'success' ? 'bg-emerald-400 animate-pulse' : resolvedTone === 'danger' ? 'bg-red-400' : resolvedTone === 'warning' ? 'bg-amber-400' : 'bg-current'}`} />}
      {label.toUpperCase()}
    </span>
  );
};
