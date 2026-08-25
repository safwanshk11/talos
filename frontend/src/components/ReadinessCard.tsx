import React from 'react';
import { RepositoryReadiness } from '../types';
import { ShieldCheck, Check, X, ShieldAlert } from 'lucide-react';

interface ReadinessCardProps {
  readiness: RepositoryReadiness | null;
}

export const ReadinessCard: React.FC<ReadinessCardProps> = ({ readiness }) => {
  if (!readiness) {
    return (
      <div className="p-5 rounded-xl bg-card border border-subtle flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-400" />
          <span>Automation Readiness Not Assessed Yet. Trigger a repository scan to evaluate.</span>
        </div>
      </div>
    );
  }

  const items = [
    { label: 'Package Manifest', value: readiness.manifest_found },
    { label: 'Lockfile', value: readiness.lockfile_found },
    { label: 'Build Command', value: readiness.build_script_found },
    { label: 'Test Suite', value: readiness.test_script_found },
    { label: 'Linter', value: readiness.lint_script_found },
    { label: 'CI Configuration', value: readiness.ci_config_found },
  ];

  const scoreColor =
    readiness.score_level === 'HIGH'
      ? 'badge-green'
      : readiness.score_level === 'MEDIUM'
      ? 'badge-amber'
      : 'badge-gray';

  return (
    <div className="p-6 rounded-xl bg-card border border-subtle space-y-4">
      <div className="flex items-center justify-between border-b border-subtle pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-100 font-mono">
              AUTOMATION READINESS ASSESSMENT
            </h3>
            <p className="text-xs text-slate-400">
              Evaluates repository verification signals to determine autonomous repair safety.
            </p>
          </div>
        </div>

        <span className={`badge ${scoreColor} text-xs font-mono font-bold uppercase px-3 py-1`}>
          {readiness.score_level} READINESS
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {items.map((item, idx) => (
          <div
            key={idx}
            className="p-3 rounded-lg bg-slate-950/50 border border-subtle flex items-center justify-between text-xs"
          >
            <span className="text-slate-300 font-medium">{item.label}</span>
            {item.value ? (
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <Check className="w-3.5 h-3.5" />
              </span>
            ) : (
              <span className="text-slate-600 font-bold flex items-center gap-1">
                <X className="w-3.5 h-3.5" />
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
