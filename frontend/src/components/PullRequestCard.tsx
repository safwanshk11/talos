import React from 'react';
import { PullRequest } from '../types';
import { GitPullRequest, GitMerge, XCircle, ExternalLink } from 'lucide-react';

interface PullRequestCardProps {
  pr: PullRequest;
}

const STATUS_CFG: Record<string, { cls: string; icon: React.ReactNode; label: string }> = {
  open: { cls: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/25', icon: <GitPullRequest className="w-3.5 h-3.5" />, label: 'OPEN' },
  merged: { cls: 'text-purple-400 bg-purple-500/10 border-purple-500/25', icon: <GitMerge className="w-3.5 h-3.5" />, label: 'MERGED' },
  closed: { cls: 'text-slate-400 bg-slate-800/60 border-subtle', icon: <XCircle className="w-3.5 h-3.5" />, label: 'CLOSED' },
};

export const PullRequestCard: React.FC<PullRequestCardProps> = ({ pr }) => {
  const cfg = STATUS_CFG[pr.github_status || 'open'] || STATUS_CFG.open;
  return (
    <a
      href={pr.pr_url}
      target="_blank"
      rel="noreferrer"
      className="p-3 rounded-lg bg-card border border-subtle hover:border-slate-700 transition-all flex items-center justify-between gap-3 font-mono text-xs"
    >
      <div className="flex items-center gap-2.5 overflow-hidden">
        <span className="text-slate-500 shrink-0">#{pr.pr_number}</span>
        <span className="text-slate-200 font-medium truncate">{pr.title}</span>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-[10px] font-bold ${cfg.cls}`}>
          {cfg.icon}
          {cfg.label}
        </span>
        <ExternalLink className="w-3.5 h-3.5 text-slate-500" />
      </div>
    </a>
  );
};
