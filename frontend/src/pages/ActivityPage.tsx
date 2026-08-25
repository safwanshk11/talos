import React from 'react';
import { ShieldCheck, Database, GitFork } from 'lucide-react';

export const ActivityPage: React.FC = () => {
  const events = [
    {
      time: 'Just now',
      title: 'Platform Foundation Initialized',
      desc: 'TALOS Core API and GitHub OAuth/PAT synchronization pipeline ready.',
      type: 'system',
      icon: ShieldCheck,
    },
    {
      time: '1 min ago',
      title: 'PostgreSQL Relational Schema Synchronized',
      desc: 'Tables created for User, GitHubConnection, Repository, and stubs for future maintenance entities.',
      type: 'db',
      icon: Database,
    },
    {
      time: '3 mins ago',
      title: 'Repository Connection Service Active',
      desc: 'Monitoring loop standing by for incoming GitHub webhook events.',
      type: 'repo',
      icon: GitFork,
    },
  ];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100 font-mono tracking-tight">
          SYSTEM ACTIVITY LOG
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Audit ledger tracking backend platform events and repository monitoring state updates.
        </p>
      </div>

      <div className="p-6 rounded-xl bg-card border border-subtle space-y-6">
        <div className="space-y-4">
          {events.map((evt, idx) => {
            const Icon = evt.icon;
            return (
              <div
                key={idx}
                className="p-4 rounded-lg bg-slate-950/50 border border-subtle flex items-start gap-4"
              >
                <div className="p-2 rounded bg-blue-500/10 border border-blue-500/20 text-blue-400 shrink-0">
                  <Icon className="w-4 h-4" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-slate-200 font-mono">
                      {evt.title}
                    </h3>
                    <span className="text-xs text-slate-500 font-mono">{evt.time}</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">{evt.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
