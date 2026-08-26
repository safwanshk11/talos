import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import { TalosMark } from '../components/ui/TalosMark';

type Phase = 'exchanging' | 'error';

/**
 * Return leg of the GitHub OAuth redirect (LoginPage.handleOAuthRedirect is
 * the outbound leg). GitHub sends the browser back here with ?code=... —
 * this page's only job is to hand that code to the existing
 * api.exchangeOAuthCode() and get the visitor into /app. Never renders the
 * raw query string or a stack trace; failures fall back to a "return to
 * login" affordance rather than staying stuck on this route.
 */
export const AuthCallbackPage: React.FC = () => {
  const navigate = useNavigate();
  const [phase, setPhase] = useState<Phase>('exchanging');
  const [error, setError] = useState<string | null>(null);
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const oauthError = params.get('error');

    if (oauthError) {
      setPhase('error');
      setError('GitHub authorization was cancelled or denied.');
      return;
    }

    if (!code) {
      setPhase('error');
      setError('Missing authorization code from GitHub. Please try signing in again.');
      return;
    }

    (async () => {
      try {
        const res = await api.exchangeOAuthCode(code);
        localStorage.setItem('talos_token', res.access_token);
        navigate('/app', { replace: true });
      } catch (err: any) {
        setPhase('error');
        const message: string = err?.message || '';
        if (message.includes('401') || message.includes('Not authenticated')) {
          setError('Your session expired before GitHub authorization completed. Please sign in again.');
        } else if (message.includes('unreachable')) {
          setError('TALOS backend is unreachable right now. Please try again shortly.');
        } else {
          setError('GitHub sign-in failed. The authorization code may have expired or already been used.');
        }
      }
    })();
  }, [navigate]);

  return (
    <div className="min-h-screen bg-dark text-text-primary flex items-center justify-center p-8">
      <motion.div
        className="w-full max-w-sm text-center"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="flex items-center justify-center gap-2 mb-8">
          <TalosMark size={22} />
          <span className="font-bold text-sm font-mono tracking-wider">TALOS</span>
        </div>

        {phase === 'exchanging' ? (
          <>
            <Loader2 className="w-6 h-6 text-blue-400 animate-spin mx-auto mb-4" />
            <p className="text-sm text-text-secondary">Connecting GitHub...</p>
          </>
        ) : (
          <>
            <div className="w-10 h-10 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="w-5 h-5 text-red-400" />
            </div>
            <p className="text-sm text-text-primary font-medium mb-1">Sign-in didn't complete</p>
            <p className="text-xs text-text-muted mb-6">{error}</p>
            <button
              onClick={() => navigate('/login', { replace: true })}
              className="btn btn-primary text-sm py-2.5 px-6"
            >
              Back to Login
            </button>
          </>
        )}
      </motion.div>
    </div>
  );
};
