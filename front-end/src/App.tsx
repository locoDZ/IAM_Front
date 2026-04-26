import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import React from "react";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import DepartmentPage from "./pages/DepartmentPage";
import AttackPage from "./pages/AttackPage";


// Basic Protected Route Component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const user = sessionStorage.getItem("user");
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route path="/" element={<Navigate to="/login" replace />} />
        {/* Fallback to login */}
        <Route path="/department/:id" element={
          <ProtectedRoute>
            <DepartmentPage />
          </ProtectedRoute>
        } />
        <Route path="*" element={<Navigate to="/login" replace />} />
        import AttackPage from "./pages/AttackPage";


        <Route path="/attacks" element={
          <ProtectedRoute>
            <AttackPage />
          </ProtectedRoute>
        } />
      </Routes>
    </Router>
  );
}
