import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { api } from '../services/api';
import { ShieldCheck, Github, Key, Loader2, Lock, GitPullRequest, AlertCircle, ArrowLeft } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [patInput, setPatInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPat, setShowPat] = useState(false);

  const handleOAuthRedirect = async () => {
    setError(null);
    try {
      const res = await api.getOAuthUrl();
      window.location.href = res.url;
    } catch (err: any) {
      setError(err.message || 'Failed to initialize GitHub OAuth flow.');
    }
  };

  const handleConnectPAT = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patInput.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.connectPAT(patInput.trim());
      localStorage.setItem('talos_token', res.access_token);
      navigate('/app');
    } catch (err: any) {
      setError(err.message || 'Failed to connect with provided GitHub PAT.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-dark text-text-primary flex">
      {/* Left panel */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 border-r border-subtle relative overflow-hidden">
        <div
          className="absolute inset-0 -z-10 opacity-[0.04]"
          style={{
            backgroundImage: 'radial-gradient(circle, #fff 1px, transparent 1px)',
            backgroundSize: '28px 28px',
          }}
        />
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-xs text-text-muted hover:text-text-primary transition-colors w-fit"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to TALOS
        </button>

        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="flex items-center gap-2 mb-6">
            <ShieldCheck className="w-5 h-5 text-blue-400" />
            <span className="font-bold text-sm font-mono tracking-wider">TALOS</span>
          </div>
          <h1 className="text-4xl font-bold tracking-tight leading-[1.1]">
            Autonomous maintenance.
            <br />
            Human control.
          </h1>
          <p className="text-sm text-text-secondary mt-4 max-w-sm leading-relaxed">
            TALOS handles repetitive repository maintenance while keeping developers in control
            of every merge.
          </p>

          <div className="grid gap-3 mt-10 max-w-sm">
            <div className="p-4 rounded-xl border border-subtle bg-card card-interactive">
              <div className="flex items-center gap-2 text-emerald-400 text-xs font-mono font-semibold mb-1.5">
                <ShieldCheck className="w-3.5 h-3.5" />
                VERIFIED PATCHES
              </div>
              <p className="text-xs text-text-muted">Every patch is checked before delivery.</p>
            </div>
            <div className="p-4 rounded-xl border border-subtle bg-card card-interactive">
              <div className="flex items-center gap-2 text-blue-400 text-xs font-mono font-semibold mb-1.5">
                <GitPullRequest className="w-3.5 h-3.5" />
                HUMAN IN CONTROL
              </div>
              <p className="text-xs text-text-muted">TALOS creates PRs. You decide what gets merged.</p>
            </div>
          </div>
        </motion.div>

        <div />
      </div>

      {/* Right panel */}
      <div className="flex-1 flex items-center justify-center p-8">
        <motion.div
          className="w-full max-w-sm"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="lg:hidden flex items-center gap-2 mb-8 justify-center">
            <ShieldCheck className="w-5 h-5 text-blue-400" />
            <span className="font-bold text-sm font-mono tracking-wider">TALOS</span>
          </div>

          <h2 className="text-xl font-bold text-text-primary">Welcome back</h2>
          <p className="text-sm text-text-secondary mt-1 mb-8">Sign in to access your TALOS workspace.</p>

          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2 mb-4">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            onClick={handleOAuthRedirect}
            className="btn btn-primary w-full text-sm py-2.5 flex items-center justify-center gap-2"
          >
            <Github className="w-4 h-4" />
            <span>Continue with GitHub</span>
          </button>

          <div className="flex items-center gap-3 my-5">
            <div className="h-px flex-1 bg-subtle" />
            <span className="text-[11px] text-text-muted font-mono">OR USE A TOKEN</span>
            <div className="h-px flex-1 bg-subtle" />
          </div>

          {!showPat ? (
            <button onClick={() => setShowPat(true)} className="btn btn-secondary w-full text-xs py-2.5">
              <Key className="w-3.5 h-3.5" />
              <span>Sign in with a Personal Access Token</span>
            </button>
          ) : (
            <form onSubmit={handleConnectPAT} className="space-y-3">
              <div className="relative">
                <Key className="w-4 h-4 text-text-muted absolute left-3 top-3" />
                <input
                  type="password"
                  autoFocus
                  placeholder="github_pat_..."
                  value={patInput}
                  onChange={(e) => setPatInput(e.target.value)}
                  className="w-full bg-input border border-muted rounded-lg pl-9 pr-4 py-2.5 text-xs text-text-primary placeholder-text-muted focus:outline-none focus:border-blue-500"
                  required
                />
              </div>
              <button type="submit" disabled={loading || !patInput.trim()} className="btn btn-primary w-full text-xs py-2.5">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <span>Sign In</span>}
              </button>
            </form>
          )}

          <p className="text-[11px] text-text-muted mt-6 flex items-center gap-1.5 justify-center">
            <Lock className="w-3 h-3" />
            Tokens are encrypted and never leave the TALOS backend.
          </p>
        </motion.div>
      </div>
    </div>
  );
};
