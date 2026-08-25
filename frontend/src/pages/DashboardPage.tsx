import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Repository, DashboardStats } from '../types';
import { MetricsOverview } from '../components/MetricsOverview';
import { RepositoryCard } from '../components/RepositoryCard';
import {
  GitFork,
  Plus,
  RefreshCw,
  AlertCircle,
  ShieldAlert,
} from 'lucide-react';

interface DashboardPageProps {
  onSelectRepo: (id: number) => void;
  onOpenConnectModal: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  onSelectRepo,
  onOpenConnectModal,
}) => {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncingId, setSyncingId] = useState<number | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [reposData, statsData] = await Promise.all([
        api.getRepositories(),
        api.getDashboardStats(),
      ]);
      setRepositories(reposData);
      setStats(statsData);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSync = async (id: number) => {
    setSyncingId(id);
    try {
      const updated = await api.syncRepository(id);
      setRepositories((prev) => prev.map((r) => (r.id === id ? updated : r)));
    } catch (err: any) {
      alert(`Sync failed: ${err.message}`);
    } finally {
      setSyncingId(null);
    }
  };

  const handleToggleMonitoring = async (id: number, currentStatus: 'active' | 'paused') => {
    const nextStatus = currentStatus === 'active' ? 'paused' : 'active';
    try {
      const updated = await api.toggleMonitoring(id, nextStatus);
      setRepositories((prev) => prev.map((r) => (r.id === id ? updated : r)));
      // Refresh stats
      const newStats = await api.getDashboardStats();
      setStats(newStats);
    } catch (err: any) {
      alert(`Failed to update status: ${err.message}`);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Overview Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight font-mono">
            OPERATIONS DASHBOARD
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time monitoring and autonomous repository maintenance status.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchData}
            disabled={loading}
            className="btn btn-secondary text-xs flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Dashboard</span>
          </button>
          <button
            onClick={onOpenConnectModal}
            className="btn btn-primary text-xs flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4" />
            <span>Connect Repository</span>
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={fetchData} className="btn btn-secondary text-xs py-1 px-2.5">
            Retry
          </button>
        </div>
      )}

      {/* Real-State Backed Metrics */}
      <MetricsOverview stats={stats} loading={loading} />

      {/* Connected Repositories Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-subtle pb-3">
          <div className="flex items-center gap-2">
            <GitFork className="w-4 h-4 text-blue-400" />
            <h2 className="text-base font-semibold text-slate-200 font-mono">
              CONNECTED REPOSITORIES ({repositories.length})
            </h2>
          </div>
        </div>

        {/* Loading Skeletons */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="h-44 skeleton rounded-lg"></div>
            <div className="h-44 skeleton rounded-lg"></div>
            <div className="h-44 skeleton rounded-lg"></div>
          </div>
        ) : repositories.length === 0 ? (
          /* Empty State */
          <div className="p-12 text-center border border-dashed border-subtle rounded-xl bg-slate-900/30 space-y-4">
            <div className="w-12 h-12 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 mx-auto flex items-center justify-center">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div className="max-w-md mx-auto space-y-1">
              <h3 className="text-base font-semibold text-slate-200">
                No Repositories Connected Yet
              </h3>
              <p className="text-xs text-slate-400">
                Connect your GitHub account or paste a Personal Access Token to select repositories for TALOS to monitor.
              </p>
            </div>
            <button
              onClick={onOpenConnectModal}
              className="btn btn-primary text-xs inline-flex items-center gap-1.5"
            >
              <Plus className="w-4 h-4" />
              <span>Connect GitHub Repository</span>
            </button>
          </div>
        ) : (
          /* Repositories Grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {repositories.map((repo) => (
              <RepositoryCard
                key={repo.id}
                repo={repo}
                onSelect={onSelectRepo}
                onSync={handleSync}
                onToggleMonitoring={handleToggleMonitoring}
                syncingId={syncingId}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
