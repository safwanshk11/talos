import React from 'react';
import { MaintenanceIssue } from '../types';
import {
  X,
  ShieldAlert,
  FileCode2,
  Lock,
  ExternalLink,
  Wrench,
} from 'lucide-react';

interface IssueDetailModalProps {
  issue: MaintenanceIssue | null;
  onClose: () => void;
}

export const IssueDetailModal: React.FC<IssueDetailModalProps> = ({ issue, onClose }) => {
  if (!issue) return null;

  const severityColor =
    issue.severity === 'CRITICAL'
      ? 'bg-red-500/15 text-red-400 border-red-500/30'
      : issue.severity === 'HIGH'
      ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
      : 'bg-blue-500/15 text-blue-400 border-blue-500/30';

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 select-none">
      <div className="bg-card border border-subtle w-full max-w-2xl rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="p-5 border-b border-subtle flex items-center justify-between bg-slate-900/50">
          <div className="flex items-center gap-3 overflow-hidden pr-2">
            <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 shrink-0">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div className="overflow-hidden">
              <div className="flex items-center gap-2">
                <span className={`badge ${severityColor} font-mono text-[10px]`}>
                  {issue.severity}
                </span>
                <span className="badge badge-gray text-[10px] uppercase font-mono">
                  {issue.source || 'OSV Advisory'}
                </span>
              </div>
              <h2 className="text-base font-semibold text-slate-100 truncate font-mono mt-1">
                {issue.title}
              </h2>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-slate-200 shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono">
            <div className="p-3 rounded bg-slate-950/60 border border-subtle/70">
              <span className="text-slate-500 block text-[11px] mb-1">PACKAGE NAME</span>
              <span className="text-slate-200 font-bold text-sm">{issue.package_name || 'N/A'}</span>
            </div>

            <div className="p-3 rounded bg-slate-950/60 border border-subtle/70">
              <span className="text-slate-500 block text-[11px] mb-1">INSTALLED VERSION</span>
              <span className="text-amber-400 font-bold text-sm">{issue.current_version || 'N/A'}</span>
            </div>

            <div className="p-3 rounded bg-slate-950/60 border border-subtle/70">
              <span className="text-slate-500 block text-[11px] mb-1">AFFECTED RANGE</span>
              <span className="text-slate-300 font-medium text-xs">{issue.affected_range || 'N/A'}</span>
            </div>

            <div className="p-3 rounded bg-slate-950/60 border border-subtle/70">
              <span className="text-slate-500 block text-[11px] mb-1">RECOMMENDED FIX</span>
              <span className="text-emerald-400 font-bold text-sm">{issue.recommended_version || 'Latest'}</span>
            </div>
          </div>

          {/* Advisory Info */}
          {issue.advisory_id && (
            <div className="p-3.5 rounded-lg bg-slate-950/40 border border-subtle font-mono text-slate-300 flex items-center justify-between">
              <span>Advisory Identifier: <strong>{issue.advisory_id}</strong></span>
              <a
                href={`https://github.com/advisories/${issue.advisory_id}`}
                target="_blank"
                rel="noreferrer"
                className="text-blue-400 hover:underline flex items-center gap-1 text-[11px]"
              >
                <span>View Advisory</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          )}

          {/* Description */}
          <div className="space-y-2">
            <h3 className="font-semibold text-slate-200 font-mono uppercase text-[11px] text-slate-400">
              VULNERABILITY DESCRIPTION
            </h3>
            <div className="p-4 rounded-lg bg-slate-950/60 border border-subtle text-slate-300 leading-relaxed max-h-40 overflow-y-auto font-mono whitespace-pre-wrap">
              {issue.description || 'No detailed vulnerability description provided.'}
            </div>
          </div>

          {/* Affected Source Files List */}
          <div className="space-y-2">
            <div className="flex items-center justify-between font-mono text-[11px]">
              <span className="font-semibold text-slate-400 uppercase flex items-center gap-1.5">
                <FileCode2 className="w-3.5 h-3.5 text-blue-400" />
                DIRECT REPOSITORY REFERENCES ({issue.affected_files?.length || 0})
              </span>
            </div>

            {!issue.affected_files || issue.affected_files.length === 0 ? (
              <div className="p-3 rounded bg-slate-950/40 border border-subtle text-slate-500 italic font-mono">
                No direct import/require references found in source code files. (Indirect/transitive dependency)
              </div>
            ) : (
              <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                {issue.affected_files.map((filePath, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded bg-slate-950/60 border border-subtle text-slate-200 font-mono flex items-center justify-between"
                  >
                    <span>{filePath}</span>
                    <span className="text-[10px] text-slate-500 uppercase">Source File</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-subtle bg-slate-900/50 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-500 font-mono text-[11px]">
            <Lock className="w-3.5 h-3.5 text-slate-500" />
            <span>Autonomous Patch Agent Disabled (Phase 3)</span>
          </div>

          <div className="flex items-center gap-3">
            <button onClick={onClose} className="btn btn-secondary text-xs">
              Close
            </button>
            <button
              disabled
              title="Fix with TALOS will be enabled in Phase 3: Patch Generation"
              className="btn bg-slate-800 text-slate-500 border-slate-700 text-xs cursor-not-allowed flex items-center gap-1.5"
            >
              <Wrench className="w-3.5 h-3.5" />
              <span>Fix with TALOS (Phase 3)</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
