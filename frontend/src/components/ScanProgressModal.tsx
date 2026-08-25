import React from 'react';
import { Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { ActionLog } from '../types';

interface ScanProgressModalProps {
  isOpen: boolean;
  onClose: () => void;
  scanning: boolean;
  logs: ActionLog[];
  error: string | null;
}

export const ScanProgressModal: React.FC<ScanProgressModalProps> = ({
  isOpen,
  onClose,
  scanning,
  logs,
  error,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 select-none">
      <div className="bg-card border border-subtle w-full max-w-xl rounded-xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-5 border-b border-subtle flex items-center justify-between bg-slate-900/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
              {scanning ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : error ? (
                <AlertCircle className="w-5 h-5 text-red-400" />
              ) : (
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              )}
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-100 font-mono">
                {scanning ? 'Repository Security Scan in Progress' : error ? 'Scan Failed' : 'Scan Completed'}
              </h2>
              <p className="text-xs text-slate-400">
                Evaluating repository manifest, dependencies, and OSV security database.
              </p>
            </div>
          </div>
        </div>

        {/* Log Output Stream */}
        <div className="p-6 space-y-4 max-h-96 overflow-y-auto font-mono text-xs">
          {error && (
            <div className="p-3.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="space-y-2">
            {logs.length === 0 ? (
              <div className="text-slate-500 italic text-center py-6">Initializing scanner agent...</div>
            ) : (
              logs.map((log) => (
                <div
                  key={log.id}
                  className="p-2.5 rounded bg-slate-950/60 border border-subtle flex items-start gap-3 text-[11px]"
                >
                  <span className="text-slate-500 text-[10px] shrink-0 pt-0.5">
                    {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                  <span className="px-1.5 py-0.5 rounded bg-slate-800 text-blue-400 font-semibold shrink-0">
                    {log.step}
                  </span>
                  <span className="text-slate-200">{log.message}</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-subtle bg-slate-900/50 flex justify-end">
          <button
            onClick={onClose}
            disabled={scanning}
            className="btn btn-secondary text-xs"
          >
            {scanning ? 'Scanning...' : 'Close Window'}
          </button>
        </div>
      </div>
    </div>
  );
};
