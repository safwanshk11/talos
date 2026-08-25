import React from 'react';
import { FileDiff } from 'lucide-react';

interface DiffViewerProps {
  diff: string;
}

interface DiffLine {
  type: 'add' | 'remove' | 'context' | 'meta';
  text: string;
}

interface ParsedFile {
  path: string;
  additions: number;
  deletions: number;
  lines: DiffLine[];
}

function parseDiff(diff: string): ParsedFile[] {
  const files: ParsedFile[] = [];
  let current: ParsedFile | null = null;

  for (const line of diff.split('\n')) {
    if (line.startsWith('diff --git')) {
      if (current) files.push(current);
      current = { path: '', additions: 0, deletions: 0, lines: [] };
      continue;
    }
    if (!current) continue;

    if (line.startsWith('+++ b/')) {
      current.path = line.slice(6);
    } else if (line.startsWith('+++') || line.startsWith('---') || line.startsWith('index ') || line.startsWith('new file') || line.startsWith('deleted file')) {
      // skip file metadata lines
    } else if (line.startsWith('@@')) {
      current.lines.push({ type: 'meta', text: line });
    } else if (line.startsWith('+')) {
      current.additions += 1;
      current.lines.push({ type: 'add', text: line.slice(1) });
    } else if (line.startsWith('-')) {
      current.deletions += 1;
      current.lines.push({ type: 'remove', text: line.slice(1) });
    } else if (line.startsWith(' ')) {
      current.lines.push({ type: 'context', text: line.slice(1) });
    }
  }
  if (current) files.push(current);
  return files;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({ diff }) => {
  if (!diff || !diff.trim()) {
    return (
      <div className="p-4 rounded bg-slate-950/40 border border-subtle text-slate-500 italic font-mono text-xs">
        No diff content available.
      </div>
    );
  }

  const files = parseDiff(diff);
  const totalAdd = files.reduce((s, f) => s + f.additions, 0);
  const totalDel = files.reduce((s, f) => s + f.deletions, 0);

  return (
    <div className="space-y-3 font-mono text-[11px]">
      <div className="flex items-center gap-3 text-slate-400">
        <span className="text-slate-300 font-semibold">{files.length} file{files.length === 1 ? '' : 's'} changed</span>
        <span className="text-emerald-400">+{totalAdd}</span>
        <span className="text-red-400">-{totalDel}</span>
      </div>

      {files.map((file, idx) => (
        <div key={idx} className="rounded-lg border border-subtle overflow-hidden">
          <div className="px-3 py-2 bg-slate-900/70 border-b border-subtle flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-slate-200">
              <FileDiff className="w-3.5 h-3.5 text-blue-400" />
              {file.path}
            </span>
            <span className="text-[10px]">
              <span className="text-emerald-400">+{file.additions}</span>{' '}
              <span className="text-red-400">-{file.deletions}</span>
            </span>
          </div>
          <div className="max-h-72 overflow-y-auto bg-slate-950/60">
            {file.lines.map((line, lineIdx) => {
              const bg =
                line.type === 'add'
                  ? 'bg-emerald-500/10 text-emerald-300'
                  : line.type === 'remove'
                  ? 'bg-red-500/10 text-red-300'
                  : line.type === 'meta'
                  ? 'bg-slate-800/60 text-slate-500'
                  : 'text-slate-400';
              const prefix = line.type === 'add' ? '+' : line.type === 'remove' ? '-' : line.type === 'meta' ? '' : ' ';
              return (
                <div key={lineIdx} className={`px-3 py-0.5 whitespace-pre-wrap break-all ${bg}`}>
                  {prefix}{line.text}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
};
