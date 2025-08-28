import { Box } from '@mui/material';
import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

import ProtectedRoute from './components/Auth/ProtectedRoute';
import Layout from './components/Layout/Layout';
import NotificationCenter from './components/Notifications/NotificationCenter';
import LoadingSpinner from './components/UI/LoadingSpinner';
import { useAuthStore } from './hooks/useAuthStore';
import { useWebSocket } from './hooks/useWebSocket';
import AIAnalyticsPage from './pages/AI/AIAnalyticsPage';
import LoginPage from './pages/Auth/LoginPage';
import RegisterPage from './pages/Auth/RegisterPage';
import DashboardPage from './pages/Dashboard/DashboardPage';
import DeviceDetailsPage from './pages/Devices/DeviceDetailsPage';
import DevicesPage from './pages/Devices/DevicesPage';
import ProfilePage from './pages/Profile/ProfilePage';
import StorageAnalysisPage from './pages/Storage/StorageAnalysisPage';

const App: React.FC = () => {
  const { isAuthenticated, isLoading, initializeAuth } = useAuthStore();

  // Initialize WebSocket connection when authenticated
  useWebSocket(isAuthenticated);

  // Initialize authentication state on app start
  React.useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <LoadingSpinner size={40} />
      </Box>
    );
  }

  return (
    <Box className="fade-in">
      <Routes>
        {/* Public routes */}
        <Route
          path="/login"
          element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />}
        />
        <Route
          path="/register"
          element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <RegisterPage />}
        />

        {/* Protected routes */}
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/devices" element={<DevicesPage />} />
                  <Route path="/devices/:deviceId" element={<DeviceDetailsPage />} />
                  <Route path="/storage" element={<StorageAnalysisPage />} />
                  <Route path="/storage/:deviceId" element={<StorageAnalysisPage />} />
                  <Route path="/ai-analytics" element={<AIAnalyticsPage />} />
                  <Route path="/ai-analytics/:deviceId" element={<AIAnalyticsPage />} />
                  <Route path="/profile" element={<ProfilePage />} />
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />

                  {/* Catch-all route */}
                  <Route
                    path="*"
                    element={
                      <Box
                        display="flex"
                        justifyContent="center"
                        alignItems="center"
                        minHeight="60vh"
                        flexDirection="column"
                      >
                        <h2>404 - Page Not Found</h2>
                        <p>The page you're looking for doesn't exist.</p>
                      </Box>
                    }
                  />
                </Routes>
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>

      {/* Global notification center */}
      <NotificationCenter />
    </Box>
  );
};

export default App;
