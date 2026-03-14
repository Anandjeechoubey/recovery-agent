import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import Layout from "./components/shared/Layout";
import ProtectedRoute from "./components/shared/ProtectedRoute";
import AdminPage from "./pages/AdminPage";
import BorrowerPage from "./pages/BorrowerPage";
import LandingPage from "./pages/LandingPage";
import LearningLoopPage from "./pages/LearningLoopPage";
import LoginPage from "./pages/LoginPage";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/admin"
            element={
              <ProtectedRoute>
                <Layout>
                  <AdminPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/learning"
            element={
              <ProtectedRoute>
                <Layout>
                  <LearningLoopPage />
                </Layout>
              </ProtectedRoute>
            }
          />
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
