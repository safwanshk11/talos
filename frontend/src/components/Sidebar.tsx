import React from 'react';
import {
  LayoutDashboard,
  GitFork,
  Activity,
  Settings,
  ShieldCheck,
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  selectedRepoId: number | null;
  setSelectedRepoId: (id: number | null) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  setCurrentTab,
  setSelectedRepoId,
}) => {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'repositories', label: 'Repositories', icon: GitFork },
    { id: 'activity', label: 'Activity Log', icon: Activity },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  const handleNavClick = (tabId: string) => {
    setSelectedRepoId(null);
    setCurrentTab(tabId);
  };

  return (
    <aside className="w-64 bg-sidebar border-r border-subtle flex flex-col h-screen sticky top-0 select-none">
      {/* Brand Header */}
      <div className="p-5 border-b border-subtle flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 font-bold">
          <ShieldCheck className="w-5 h-5 text-blue-400" />
        </div>
        <div>
          <h1 className="font-bold text-base tracking-wider text-slate-100 font-mono">TALOS</h1>
          <p className="text-xs text-muted">Autonomous Maintenance</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => handleNavClick(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-md font-medium text-sm transition-colors ${
                isActive
                  ? 'bg-blue-600/15 text-blue-400 border border-blue-500/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-blue-400' : 'text-slate-500'}`} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* System Operational Status Footer */}
      <div className="p-4 border-t border-subtle bg-slate-950/40 text-xs">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="font-mono text-[11px] text-muted">SYSTEM STATUS</span>
          <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            Operational
          </span>
        </div>
        <p className="text-[11px] text-slate-500 font-mono mt-1">Verification Engine Ready</p>
      </div>
    </aside>
  );
};
