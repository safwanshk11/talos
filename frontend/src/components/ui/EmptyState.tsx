import React from 'react';

interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  tone?: 'neutral' | 'success' | 'info';
}

const TONE_CLASSES: Record<string, string> = {
  neutral: 'bg-white/[0.05] border-subtle text-text-secondary',
  success: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
  info: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
};

export const EmptyState: React.FC<EmptyStateProps> = ({ icon, title, description, action, tone = 'neutral' }) => {
  return (
    <div className="p-12 text-center border border-dashed border-subtle rounded-xl bg-white/[0.015] space-y-4">
      <div className={`w-12 h-12 rounded-full mx-auto flex items-center justify-center border ${TONE_CLASSES[tone]}`}>
        {icon}
      </div>
      <div className="max-w-md mx-auto space-y-1">
        <h3 className="text-base font-semibold text-text-primary">{title}</h3>
        {description && <p className="text-xs text-text-muted">{description}</p>}
      </div>
      {action}
    </div>
  );
};
