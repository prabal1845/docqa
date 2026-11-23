import type { ReactNode } from "react";
import { Navigate, NavLink, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import ChatPage from "./pages/ChatPage";
import DocumentsPage from "./pages/DocumentsPage";
import LoginPage from "./pages/LoginPage";

function Protected({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="center muted">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">
          <span className="logo">Q</span> DocQA
        </span>
        <nav>
          <NavLink to="/chat">Chat</NavLink>
          <NavLink to="/documents">Documents</NavLink>
        </nav>
        <UserMenu />
      </header>
      <main>{children}</main>
    </div>
  );
}

function UserMenu() {
  const { user, logout } = useAuth();
  return (
    <div className="user">
      <span className="muted email">{user?.email}</span>
      <button className="link" onClick={logout}>
        Log out
      </button>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/documents"
        element={
          <Protected>
            <DocumentsPage />
          </Protected>
        }
      />
      <Route
        path="/chat"
        element={
          <Protected>
            <ChatPage />
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/chat" replace />} />
    </Routes>
  );
}
