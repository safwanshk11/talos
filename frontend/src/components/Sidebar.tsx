import React from 'react';
import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useDashboardStats } from '../hooks/useDashboardStats';
import {
  LayoutDashboard,
  GitFork,
  Wrench,
  GitPullRequest,
  Activity,
  Settings,
  ShieldCheck,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  // Real counts only — badges reflect actual backend state, refetched
  // whenever the sidebar (part of the persistent app shell) remounts data.
  const { stats } = useDashboardStats();

  const NAV_ITEMS = [
    { to: '/app', label: 'Command Center', icon: LayoutDashboard, end: true, badge: undefined as number | undefined },
    { to: '/app/repositories', label: 'Repositories', icon: GitFork, badge: undefined as number | undefined },
    { to: '/app/maintenance', label: 'Maintenance Bay', icon: Wrench, badge: stats?.active_issues_count },
    { to: '/app/review', label: 'Review Queue', icon: GitPullRequest, badge: stats?.awaiting_review_count },
    { to: '/app/activity', label: 'Activity Log', icon: Activity, badge: undefined as number | undefined },
  ];

  return (
    <aside className="w-64 bg-sidebar border-r border-subtle flex flex-col h-screen sticky top-0 select-none shrink-0">
      {/* Brand Header */}
      <div className="p-5 border-b border-subtle flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-blue-600/15 border border-blue-500/25 flex items-center justify-center text-blue-400 font-bold">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div>
          <h1 className="font-bold text-base tracking-wider text-text-primary font-mono">TALOS</h1>
          <p className="text-xs text-text-muted">Autonomous Maintenance</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `relative flex items-center gap-3 px-3 py-2.5 rounded-md font-medium text-sm transition-colors ${
                  isActive ? 'text-blue-400' : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.div
                      layoutId="sidebar-active-pill"
                      className="absolute inset-0 bg-blue-600/15 border border-blue-500/25 rounded-md"
                      transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                    />
                  )}
                  <Icon className={`w-4 h-4 relative shrink-0 ${isActive ? 'text-blue-400' : 'text-text-muted'}`} />
                  <span className="relative flex-1">{item.label}</span>
                  {!!item.badge && (
                    <span className="relative px-1.5 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/25 text-amber-400 text-[10px] font-mono font-bold leading-none">
                      {item.badge}
                    </span>
                  )}
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Settings + status footer */}
      <div className="p-3 border-t border-subtle space-y-3">
        <NavLink
          to="/app/settings"
          className={({ isActive }) =>
            `flex items-center gap-3 px-3 py-2.5 rounded-md font-medium text-sm transition-colors ${
              isActive ? 'text-blue-400 bg-blue-600/15 border border-blue-500/25' : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04]'
            }`
          }
        >
          <Settings className="w-4 h-4 shrink-0" />
          <span>Settings</span>
        </NavLink>

        <div className="px-3 py-2.5 text-xs">
          <div className="flex items-center justify-between text-text-secondary">
            <span className="font-mono text-[11px] text-text-muted">SYSTEM STATUS</span>
            <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              Operational
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
};
