import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Repository } from '../types';
import { GitBranch, Clock } from 'lucide-react';

interface IssueSummary {
  high: number;
  medium: number;
}

interface RepositoryCardProps {
  repo: Repository;
  issueSummary?: IssueSummary;
}

const getLanguageColor = (lang?: string): string => {
  if (!lang) return '#68686f';
  const colors: Record<string, string> = {
    Python: '#3572A5',
    TypeScript: '#3178c6',
    JavaScript: '#f1e05a',
    Go: '#00ADD8',
    Rust: '#dea584',
    Java: '#b07219',
    C: '#555555',
    'C++': '#f34b7d',
    Ruby: '#701516',
    PHP: '#4F5D95',
    HTML: '#e34c26',
    CSS: '#563d7c',
  };
  return colors[lang] || '#3b82f6';
};

function timeAgo(iso?: string): string {
  if (!iso) return 'Never scanned';
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export const RepositoryCard: React.FC<RepositoryCardProps> = ({ repo, issueSummary }) => {
  const navigate = useNavigate();
  const isPaused = repo.monitoring_status === 'paused';

  return (
    <button
      onClick={() => navigate(`/app/repositories/${repo.id}`)}
      className="w-full text-left p-5 rounded-xl bg-card border border-subtle card-interactive flex flex-col gap-3 group"
    >
      <div className="flex items-start justify-between gap-3">
        <span className="text-sm font-semibold text-text-primary group-hover:text-blue-400 transition-colors truncate font-mono">
          {repo.full_name}
        </span>
        <span
          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] font-semibold font-mono shrink-0 ${
            isPaused ? 'bg-amber-500/10 text-amber-400 border-amber-500/25' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25'
          }`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${isPaused ? 'bg-amber-400' : 'bg-emerald-400 animate-pulse'}`} />
          {repo.monitoring_status.toUpperCase()}
        </span>
      </div>

      <div className="flex items-center gap-3 text-xs text-text-secondary font-mono">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: getLanguageColor(repo.primary_language) }} />
          {repo.primary_language || 'Unknown'}
        </span>
        <span className="flex items-center gap-1 text-text-muted">
          <GitBranch className="w-3 h-3" />
          {repo.default_branch}
        </span>
      </div>

      {issueSummary && (issueSummary.high > 0 || issueSummary.medium > 0) ? (
        <div className="text-xs font-mono">
          {issueSummary.high > 0 && <span className="text-red-400 font-semibold">{issueSummary.high} High</span>}
          {issueSummary.high > 0 && issueSummary.medium > 0 && <span className="text-text-muted"> · </span>}
          {issueSummary.medium > 0 && <span className="text-amber-400 font-semibold">{issueSummary.medium} Medium</span>}
        </div>
      ) : (
        <div className="text-xs font-mono text-emerald-400/80">No open issues</div>
      )}

      <div className="flex items-center gap-1.5 text-[11px] text-text-muted pt-2 border-t border-subtle mt-auto">
        <Clock className="w-3 h-3" />
        <span>Last scan {timeAgo(repo.last_scanned_at)}</span>
      </div>
    </button>
  );
};
