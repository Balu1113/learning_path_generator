import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ShieldCheck, LoaderCircle } from "lucide-react";
import { login, logout } from "../api.js";
import { useAuth } from "../context.jsx";

export default function Login() {
  const { user, setUser, loading } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  if (!loading && user?.is_superuser) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const d = await login(username.trim(), password);
      if (!d.user?.is_superuser) {
        await logout().catch(() => {});
        setError("This account does not have admin access.");
        return;
      }
      setUser(d.user);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-screen">
      <form className="login-card" onSubmit={submit}>
        <div className="login-head">
          <span className="brand-mark big">
            <ShieldCheck size={20} />
          </span>
          <div>
            <h1>LearnPath Admin</h1>
            <p>Sign in with a superuser account</p>
          </div>
        </div>
        {error && <div className="banner error">{error}</div>}
        <label>
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            autoComplete="username"
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>
        <button className="btn primary block" disabled={busy || !username || !password}>
          {busy ? <LoaderCircle size={15} className="spin" /> : <ShieldCheck size={15} />} Sign in
        </button>
      </form>
    </div>
  );
}
