import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import { useAuth } from "./context.jsx";
import { logout } from "./api.js";
import Dashboard from "./pages/Dashboard.jsx";
import Login from "./pages/Login.jsx";
import Resource from "./pages/Resource.jsx";

function Splash({ text = "Loading…" }) {
  return (
    <div className="splash">
      <p>{text}</p>
    </div>
  );
}

function NoAccess() {
  const { user, setUser } = useAuth();
  const signOut = async () => {
    await logout().catch(() => {});
    setUser(null);
  };
  return (
    <div className="splash">
      <p>
        <strong>{user?.username}</strong> has no admin access.
      </p>
      <button className="btn" onClick={signOut}>
        Sign out
      </button>
    </div>
  );
}

function RequireAdmin({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <Splash />;
  if (!user) return <Navigate to="/login" replace />;
  if (!user.is_superuser) return <NoAccess />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RequireAdmin>
            <Layout />
          </RequireAdmin>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/r/:resource" element={<Resource />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
