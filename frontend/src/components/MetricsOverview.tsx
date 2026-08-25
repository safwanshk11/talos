import React from 'react';
import { DashboardStats } from '../types';
import { GitFork, AlertTriangle, CheckCircle2, GitPullRequest } from 'lucide-react';

interface MetricsOverviewProps {
  stats: DashboardStats | null;
  loading: boolean;
}

export const MetricsOverview: React.FC<MetricsOverviewProps> = ({ stats, loading }) => {
  const cards = [
    {
      title: 'Repositories',
      value: stats?.total_repositories ?? 0,
      sub: `${stats?.active_monitoring_count ?? 0} Active Monitoring`,
      icon: GitFork,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
      borderColor: 'border-blue-500/20',
    },
    {
      title: 'Active Issues',
      value: stats?.active_issues_count ?? 0,
      sub: 'Ready for TALOS Fix',
      icon: AlertTriangle,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10',
      borderColor: 'border-amber-500/20',
    },
    {
      title: 'Verified Patches',
      value: stats?.verified_patches_count ?? 0,
      sub: 'Phase 4 Verification',
      icon: CheckCircle2,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10',
      borderColor: 'border-emerald-500/20',
    },
    {
      title: 'Awaiting Review',
      value: stats?.awaiting_review_count ?? 0,
      sub: 'Phase 5 PR Delivery',
      icon: GitPullRequest,
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10',
      borderColor: 'border-purple-500/20',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className={`p-5 rounded-lg bg-card border ${card.borderColor} flex flex-col justify-between`}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                {card.title}
              </span>
              <div className={`p-2 rounded-md ${card.bgColor} ${card.color}`}>
                <Icon className="w-4 h-4" />
              </div>
            </div>

            {loading ? (
              <div className="space-y-2">
                <div className="h-7 w-16 skeleton"></div>
                <div className="h-3 w-28 skeleton"></div>
              </div>
            ) : (
              <div>
                <div className="text-2xl font-bold text-slate-100 font-mono">
                  {card.value}
                </div>
                <div className="text-xs text-slate-400 mt-1 font-mono">{card.sub}</div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
