import React, { useEffect, useState } from 'react';
import { Repository } from '../types';
import { AlertTriangle, Loader2, X } from 'lucide-react';
import { Modal } from './ui/Modal';

interface RemoveRepositoryModalProps {
  repo: Repository | null;
  removing: boolean;
  error: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

export const RemoveRepositoryModal: React.FC<RemoveRepositoryModalProps> = ({
  repo,
  removing,
  error,
  onCancel,
  onConfirm,
}) => {
  // Keep the last known repo around through the exit animation — `repo` goes
  // null the instant the caller closes this, before Modal finishes fading out.
  const [lastRepo, setLastRepo] = useState<Repository | null>(repo);
  useEffect(() => {
    if (repo) setLastRepo(repo);
  }, [repo]);

  const displayRepo = repo ?? lastRepo;
  if (!displayRepo) return null;

  return (
    <Modal isOpen={!!repo} onClose={removing ? undefined : onCancel} maxWidth="max-w-md">
        {/* Header */}
        <div className="p-5 border-b border-subtle flex items-center justify-between bg-slate-900/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <h2 className="text-base font-semibold text-slate-100">Remove repository?</h2>
          </div>
          <button
            onClick={onCancel}
            disabled={removing}
            className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-slate-200 disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4 text-sm">
          <p className="text-slate-300">TALOS will stop monitoring:</p>
          <div className="p-3 rounded-lg bg-slate-950/60 border border-subtle font-mono text-slate-100 text-sm">
            {displayRepo.full_name}
          </div>
          <p className="text-xs text-slate-400">
            Existing GitHub code will not be modified or deleted. Scan history, detected issues,
            and past patch attempts are preserved but will no longer be visible while disconnected.
          </p>

          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-subtle bg-slate-900/50 flex items-center justify-end gap-3">
          <button onClick={onCancel} disabled={removing} className="btn btn-secondary text-xs">
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={removing}
            className="btn btn-danger text-xs flex items-center gap-1.5"
          >
            {removing && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            <span>{removing ? 'Removing...' : 'Remove Repository'}</span>
          </button>
        </div>
    </Modal>
  );
};
