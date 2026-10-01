import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AppShell } from "./components/layout/AppShell";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { SubmitReportPage } from "./pages/SubmitReportPage";
import { ReviewQueuePage } from "./pages/ReviewQueuePage";
import { AlertsPage } from "./pages/AlertsPage";
import { SitesPage } from "./pages/SitesPage";
import { SettingsPage } from "./pages/SettingsPage";
import { ReportDetailPage } from "./pages/ReportDetailPage";
import { RiskMapPage } from "./pages/RiskMapPage";

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Login Route */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected Application Routes wrapped in AppShell */}
          <Route
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/map" element={<RiskMapPage />} />
            <Route path="/risk-map" element={<Navigate to="/map" replace />} />
            <Route path="/reports/:id" element={<ReportDetailPage />} />
            <Route path="/submit" element={<SubmitReportPage />} />
            <Route path="/review-queue" element={<ReviewQueuePage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/sites" element={<SitesPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>

          {/* Catch-all Fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
