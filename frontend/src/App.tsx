import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { ConnectGithubModal } from './components/ConnectGithubModal';
import { DashboardPage } from './pages/DashboardPage';
import { RepositoryDetailPage } from './pages/RepositoryDetailPage';
import { ActivityPage } from './pages/ActivityPage';
import { SettingsPage } from './pages/SettingsPage';
import { api } from './services/api';
import { User, GitHubConnectionStatus } from './types';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('overview');
  const [selectedRepoId, setSelectedRepoId] = useState<number | null>(null);
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);

  const [user, setUser] = useState<User | null>(null);
  const [ghStatus, setGhStatus] = useState<GitHubConnectionStatus | null>(null);

  const fetchUserAndStatus = async () => {
    try {
      const [uData, statusData] = await Promise.all([
        api.getMe(),
        api.getGitHubStatus(),
      ]);
      setUser(uData);
      setGhStatus(statusData);
    } catch {
      // API fallback handles local dev mode seamlessly
    }
  };

  useEffect(() => {
    fetchUserAndStatus();
  }, []);

  const handleSelectRepo = (id: number) => {
    setSelectedRepoId(id);
  };

  return (
    <div className="flex min-h-screen bg-[#090d16] text-slate-100 font-sans">
      {/* Sidebar Navigation */}
      <Sidebar
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        selectedRepoId={selectedRepoId}
        setSelectedRepoId={setSelectedRepoId}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          user={user}
          ghStatus={ghStatus}
          onOpenConnectModal={() => setIsConnectModalOpen(true)}
        />

        <main className="flex-1 overflow-y-auto">
          {selectedRepoId !== null ? (
            <RepositoryDetailPage
              repoId={selectedRepoId}
              onBack={() => setSelectedRepoId(null)}
            />
          ) : currentTab === 'overview' || currentTab === 'repositories' ? (
            <DashboardPage
              onSelectRepo={handleSelectRepo}
              onOpenConnectModal={() => setIsConnectModalOpen(true)}
            />
          ) : currentTab === 'activity' ? (
            <ActivityPage />
          ) : currentTab === 'settings' ? (
            <SettingsPage
              ghStatus={ghStatus}
              onRefreshStatus={fetchUserAndStatus}
              onOpenConnectModal={() => setIsConnectModalOpen(true)}
            />
          ) : null}
        </main>
      </div>

      {/* Connect GitHub Modal */}
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

export default App;
