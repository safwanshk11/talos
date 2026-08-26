/** Shared MaintenanceIssue.status groupings — the single source of truth for
 * which statuses count as "still in progress", "needs a human", or "closed
 * out", so Command Center / Maintenance Bay / Repository detail agree. */

export const ACTIVE_STATUSES = ['ANALYZING', 'PLANNING', 'PLANNED', 'SANDBOXING', 'PATCHING', 'VERIFYING', 'DELIVERING'];
export const ATTENTION_STATUSES = ['VERIFICATION_FAILED', 'DELIVERY_FAILED', 'ESCALATED', 'FAILED'];
export const CLOSED_STATUSES = ['RESOLVED', 'DELIVERED'];

export function isActiveStatus(status: string): boolean {
  return ACTIVE_STATUSES.includes(status);
}
export function needsAttention(status: string): boolean {
  return ATTENTION_STATUSES.includes(status);
}
export function isClosedStatus(status: string): boolean {
  return CLOSED_STATUSES.includes(status);
}
