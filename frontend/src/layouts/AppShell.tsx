import React, { useState, useEffect } from 'react';
import { Outlet, useLocation, useNavigate, useOutletContext } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { Sidebar } from '../components/Sidebar';
import { Header } from '../components/Header';
import { ConnectGithubModal } from '../components/ConnectGithubModal';
import { PageTransition } from '../components/ui/PageTransition';
import { api } from '../services/api';
import { User, GitHubConnectionStatus } from '../types';

interface AppShellContext {
  user: User | null;
  ghStatus: GitHubConnectionStatus | null;
  refreshStatus: () => void;
  openConnectModal: () => void;
}

export function useAppShell() {
  return useOutletContext<AppShellContext>();
}

export const AppShell: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [ghStatus, setGhStatus] = useState<GitHubConnectionStatus | null>(null);

  const fetchUserAndStatus = async () => {
    try {
      const [uData, statusData] = await Promise.all([api.getMe(), api.getGitHubStatus()]);
      setUser(uData);
      setGhStatus(statusData);
    } catch (err: any) {
      // In local development the backend auto-provisions a default user, so
      // this only fires on a genuine auth failure (e.g. ENVIRONMENT=production
      // with no/invalid session) — send the visitor to log in rather than
      // rendering an empty shell as if they were signed in.
      if (String(err?.message || '').includes('401')) {
        localStorage.removeItem('talos_token');
        navigate('/login', { replace: true });
      }
    }
  };

  useEffect(() => {
    fetchUserAndStatus();
  }, []);

  return (
    <div className="flex min-h-screen bg-dark text-text-primary font-sans">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0">
        <Header user={user} ghStatus={ghStatus} onOpenConnectModal={() => setIsConnectModalOpen(true)} />

        <main className="flex-1 overflow-y-auto">
          <AnimatePresence mode="wait">
            <PageTransition key={location.pathname}>
              <Outlet
                context={{
                  user,
                  ghStatus,
                  refreshStatus: fetchUserAndStatus,
                  openConnectModal: () => setIsConnectModalOpen(true),
                } satisfies AppShellContext}
              />
            </PageTransition>
          </AnimatePresence>
        </main>
      </div>

      <ConnectGithubModal
        isOpen={isConnectModalOpen}
        onClose={() => setIsConnectModalOpen(false)}
        onRepositoryConnected={fetchUserAndStatus}
        ghStatus={ghStatus}
        onRefreshStatus={fetchUserAndStatus}
      />
    </div>
  );
};
