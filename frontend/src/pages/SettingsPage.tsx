import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { useAppShell } from '../layouts/AppShell';
import { PageHeader } from '../components/ui/PageHeader';
import { SectionCard } from '../components/ui/SectionCard';
import { HealthStatus } from '../types';
import { Shield, Github, Trash2, CheckCircle2, AlertCircle, Loader2, Brain } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { ghStatus, refreshStatus, openConnectModal } = useAppShell();
  const [disconnecting, setDisconnecting] = useState(false);
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    api.getHealth().then(setHealth).catch(() => {});
  }, []);

  const handleDisconnect = async () => {
    if (!confirm('Are you sure you want to disconnect your GitHub account from TALOS?')) return;
    setDisconnecting(true);
    try {
      await api.disconnectGitHub();
      localStorage.removeItem('talos_token');
      refreshStatus();
    } catch (err: any) {
      alert(`Disconnect failed: ${err.message}`);
    } finally {
      setDisconnecting(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <PageHeader eyebrow="Settings" title="Settings" subtitle="Manage GitHub credentials, security tokens, and platform integrations." />

      <SectionCard icon={<Github className="w-5 h-5" />} title="GitHub Connection" subtitle="TALOS connects securely to GitHub to read repository metadata and track commits.">
        {ghStatus?.connected ? (
          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-white/[0.02] border border-emerald-500/25 flex items-center justify-between text-xs">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                <div>
                  <div className="font-semibold text-text-primary">Connected as @{ghStatus.github_username}</div>
                  <div className="text-text-muted mt-0.5 font-mono">
                    Scopes: {ghStatus.scopes || 'repo, user'} • Connected: {ghStatus.connected_at ? new Date(ghStatus.connected_at).toLocaleDateString() : 'Active'}
                  </div>
                </div>
              </div>
              <button onClick={handleDisconnect} disabled={disconnecting} className="btn btn-danger text-xs flex items-center gap-1.5">
                {disconnecting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                <span>Disconnect</span>
              </button>
            </div>
            <button onClick={openConnectModal} className="btn btn-secondary text-xs">Change Token / Connect Repositories</button>
          </div>
        ) : (
          <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-between text-xs">
            <div className="flex items-center gap-3 text-amber-400">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>No GitHub connection active. Connect a PAT or OAuth app to import repositories.</span>
            </div>
            <button onClick={openConnectModal} className="btn btn-primary text-xs shrink-0">Connect GitHub</button>
          </div>
        )}
      </SectionCard>

      {health && (
        <SectionCard icon={<Brain className="w-5 h-5" />} title="AI Provider" subtitle="Used for problem analysis and patch planning — deterministic package-manager commands still make the actual change.">
          <div className="p-4 rounded-lg bg-white/[0.02] border border-subtle flex items-center justify-between text-xs">
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-blue-400" />
              <div>
                <div className="font-semibold text-text-primary capitalize">{health.ai_provider}</div>
                <div className="text-text-muted mt-0.5 font-mono">{health.ai_model}</div>
              </div>
            </div>
            <span className="badge badge-blue uppercase">Active</span>
          </div>
        </SectionCard>
      )}

      <SectionCard icon={<Shield className="w-5 h-5" />} title="Security Principles & Governance" subtitle="TALOS operates under strict least-privilege security and isolated branch rules.">
        <ul className="text-xs text-text-secondary space-y-2.5 list-disc list-inside font-mono">
          <li>GitHub credentials are encrypted and strictly managed by the backend.</li>
          <li>Frontend never receives or stores raw access tokens or OAuth secrets.</li>
          <li>Primary branches are protected — TALOS never directly commits to main.</li>
          <li>Verification sandboxes never receive TALOS's credentials.</li>
          <li>Untrusted repository files are treated as data, preventing prompt injection attacks.</li>
        </ul>
      </SectionCard>
    </div>
  );
};
