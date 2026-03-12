import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/shared/Layout";
import AdminPage from "./pages/AdminPage";
import BorrowerPage from "./pages/BorrowerPage";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/borrower" element={<BorrowerPage />} />
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
