import React from 'react';
import { Repository } from '../types';
import { GitBranch, ChevronRight } from 'lucide-react';

interface RepositoryCardProps {
  repo: Repository;
  onSelect: (id: number) => void;
}

const getLanguageColor = (lang?: string): string => {
  if (!lang) return '#94a3b8';
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

export const RepositoryCard: React.FC<RepositoryCardProps> = ({ repo, onSelect }) => {
  const isPaused = repo.monitoring_status === 'paused';

  return (
    <button
      onClick={() => onSelect(repo.id)}
      className="w-full text-left p-5 rounded-lg bg-card border border-subtle hover:border-slate-700 hover:bg-card-hover transition-all duration-200 flex flex-col justify-between group"
    >
      {/* Top Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 overflow-hidden">
          <GitBranch className="w-4 h-4 text-blue-400 shrink-0" />
          <span className="text-base font-semibold text-slate-100 group-hover:text-blue-400 transition-colors truncate font-mono">
            {repo.full_name}
          </span>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className={`badge ${isPaused ? 'badge-amber' : 'badge-green'}`}>
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isPaused ? 'bg-amber-400' : 'bg-emerald-400 animate-pulse'
              }`}
            ></span>
            {repo.monitoring_status.toUpperCase()}
          </span>
          <span className="badge badge-gray uppercase">{repo.visibility}</span>
        </div>
      </div>

      {/* Commit / Branch info */}
      <div className="space-y-2 mb-4 bg-slate-950/40 p-3 rounded border border-subtle/60 text-xs font-mono">
        <div className="flex items-center justify-between text-slate-400">
          <div className="flex items-center gap-1.5">
            <GitBranch className="w-3.5 h-3.5 text-slate-500" />
            <span>{repo.default_branch}</span>
          </div>
          {repo.latest_commit?.sha && (
            <span className="text-slate-500 text-[11px]">
              {repo.latest_commit.sha.substring(0, 7)}
            </span>
          )}
        </div>

        {repo.latest_commit?.message ? (
          <p className="text-slate-300 truncate text-[11px] italic">
            "{repo.latest_commit.message.split('\n')[0]}"
          </p>
        ) : (
          <p className="text-slate-500 text-[11px] italic">No commit info cached</p>
        )}
      </div>

      {/* Card Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-subtle/50 text-xs">
        {/* Language pill */}
        <div className="flex items-center gap-2">
          <span
            className="w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: getLanguageColor(repo.primary_language) }}
          ></span>
          <span className="text-slate-300 font-medium">
            {repo.primary_language || 'Markdown / Config'}
          </span>
        </div>

        {/* Single navigation affordance */}
        <span className="flex items-center gap-1 text-slate-400 group-hover:text-blue-400 transition-colors font-medium">
          <span>View</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </span>
      </div>
    </button>
  );
};
