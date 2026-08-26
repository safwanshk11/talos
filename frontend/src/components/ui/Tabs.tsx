import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export interface TabDef {
  key: string;
  label: string;
  badge?: React.ReactNode;
}

interface TabsProps {
  tabs: TabDef[];
  active: string;
  onChange: (key: string) => void;
}

export const TabBar: React.FC<TabsProps> = ({ tabs, active, onChange }) => (
  <div className="flex items-center gap-1 border-b border-subtle -mx-6 px-6 overflow-x-auto">
    {tabs.map((tab) => {
      const isActive = tab.key === active;
      return (
        <button
          key={tab.key}
          onClick={() => onChange(tab.key)}
          className={`relative px-3 py-2.5 text-xs font-semibold font-mono uppercase tracking-wide whitespace-nowrap transition-colors ${
            isActive ? 'text-blue-400' : 'text-text-muted hover:text-text-secondary'
          }`}
        >
          <span className="flex items-center gap-1.5">
            {tab.label}
            {tab.badge}
          </span>
          {isActive && (
            <motion.div layoutId="job-tab-underline" className="absolute left-0 right-0 -bottom-px h-0.5 bg-blue-500" transition={{ type: 'spring', stiffness: 500, damping: 40 }} />
          )}
        </button>
      );
    })}
  </div>
);

export const TabPanel: React.FC<{ tabKey: string; active: string; children: React.ReactNode }> = ({ tabKey, active, children }) => (
  <AnimatePresence mode="wait">
    {tabKey === active && (
      <motion.div
        key={tabKey}
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15 }}
      >
        {children}
      </motion.div>
    )}
  </AnimatePresence>
);
