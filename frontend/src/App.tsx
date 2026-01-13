import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { AuthProvider } from '@/contexts/AuthContext';
import { SetupProvider } from '@/contexts/SetupContext';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { AppLayout } from '@/components/Layout/AppLayout';
import { LoginPage } from '@/features/auth/LoginPage';
import { SetupPage } from '@/features/setup/SetupPage';
import { WorkflowListPage } from '@/features/workflows/WorkflowListPage';
import { WorkflowEditorPage } from '@/features/workflows/WorkflowEditorPage';
import { RequestListPage } from '@/features/requests/RequestListPage';
import { DiscoveryPage } from '@/features/discovery/DiscoveryPage';
import { SettingsPage } from '@/features/settings/SettingsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000, // 30 seconds
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <SetupProvider>
          <BrowserRouter>
            <Routes>
              {/* Setup route (public) */}
              <Route path="/setup" element={<SetupPage />} />

              {/* Login route (public) */}
              <Route path="/login" element={<LoginPage />} />

              {/* Protected routes with layout */}
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<Navigate to="/workflows" replace />} />
                <Route path="workflows" element={<WorkflowListPage />} />
                <Route path="requests" element={<RequestListPage />} />
                <Route path="discovery" element={<DiscoveryPage />} />
                <Route path="settings" element={<SettingsPage />} />
              </Route>

              {/* Full-page editor (protected, no sidebar) */}
              <Route
                path="/workflows/:id"
                element={
                  <ProtectedRoute>
                    <WorkflowEditorPage />
                  </ProtectedRoute>
                }
              />

              {/* Catch-all redirect */}
              <Route path="*" element={<Navigate to="/workflows" replace />} />
            </Routes>
          </BrowserRouter>
        </SetupProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
