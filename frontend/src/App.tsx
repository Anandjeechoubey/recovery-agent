import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import Layout from "./components/shared/Layout";
import DashboardLayout from "./components/shared/DashboardLayout";
import ProtectedRoute from "./components/shared/ProtectedRoute";
import BorrowersPage from "./pages/BorrowersPage";
import PromptsPage from "./pages/PromptsPage";
import AddBorrowerPage from "./pages/AddBorrowerPage";
import BillingPage from "./pages/BillingPage";
import BorrowerPage from "./pages/BorrowerPage";
import LandingPage from "./pages/LandingPage";
import LearningLoopPage from "./pages/LearningLoopPage";
import DocsPage from "./pages/DocsPage";
import LoginPage from "./pages/LoginPage";

function DashboardRoute({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <DashboardLayout>{children}</DashboardLayout>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />

          {/* Dashboard routes with sidebar */}
          <Route path="/dashboard/borrowers" element={<DashboardRoute><BorrowersPage /></DashboardRoute>} />
          <Route path="/dashboard/prompts" element={<DashboardRoute><PromptsPage /></DashboardRoute>} />
          <Route path="/dashboard/reports" element={<DashboardRoute><LearningLoopPage /></DashboardRoute>} />
          <Route path="/dashboard/add-borrower" element={<DashboardRoute><AddBorrowerPage /></DashboardRoute>} />
          <Route path="/dashboard/billing" element={<DashboardRoute><BillingPage /></DashboardRoute>} />
          <Route path="/dashboard/docs" element={<DashboardRoute><DocsPage /></DashboardRoute>} />

          {/* Redirect old /admin and /learning to new paths */}
          <Route path="/admin" element={<Navigate to="/dashboard/borrowers" replace />} />
          <Route path="/learning" element={<Navigate to="/dashboard/reports" replace />} />

          {/* Borrower portal (public, with simple layout) */}
          <Route
            path="/borrower"
            element={
              <Layout>
                <BorrowerPage />
              </Layout>
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
