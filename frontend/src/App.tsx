import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from './layouts/AppShell';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { CommandCenterPage } from './pages/CommandCenterPage';
import { RepositoryRegistryPage } from './pages/RepositoryRegistryPage';
import { RepositoryDetailPage } from './pages/RepositoryDetailPage';
import { MaintenanceBayPage } from './pages/MaintenanceBayPage';
import { ReviewQueuePage } from './pages/ReviewQueuePage';
import { ActivityPage } from './pages/ActivityPage';
import { SettingsPage } from './pages/SettingsPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />

        <Route path="/app" element={<AppShell />}>
          <Route index element={<CommandCenterPage />} />
          <Route path="repositories" element={<RepositoryRegistryPage />} />
          <Route path="repositories/:id" element={<RepositoryDetailPage />} />
          <Route path="maintenance" element={<MaintenanceBayPage />} />
          <Route path="review" element={<ReviewQueuePage />} />
          <Route path="activity" element={<ActivityPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
