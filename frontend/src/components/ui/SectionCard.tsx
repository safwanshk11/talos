import React from 'react';

interface SectionCardProps {
  icon?: React.ReactNode;
  title?: string;
  subtitle?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  noPadding?: boolean;
}

export const SectionCard: React.FC<SectionCardProps> = ({ icon, title, subtitle, action, children, className = '', noPadding }) => {
  return (
    <div className={`rounded-xl bg-card border border-subtle ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between gap-4 px-6 py-4 border-b border-subtle">
          <div className="flex items-center gap-3 min-w-0">
            {icon && (
              <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 shrink-0">
                {icon}
              </div>
            )}
            <div className="min-w-0">
              {title && <h3 className="text-sm font-semibold text-text-primary">{title}</h3>}
              {subtitle && <p className="text-xs text-text-muted mt-0.5 truncate">{subtitle}</p>}
            </div>
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      )}
      <div className={noPadding ? '' : 'p-6'}>{children}</div>
    </div>
  );
};
