import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { loginUser, registerUser } from "../api/client";
import { LogIn, Loader2 } from "lucide-react";

export default function Login() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const fn = isRegister ? registerUser : loginUser;
      const d = await fn(username, password);
      if (d.error) setError(d.error);
      else {
        setUser(d.user);
        navigate("/history");
      }
    } catch {
      setError("Failed to connect to backend.");
    }
    setLoading(false);
  };

  return (
    <div className="page-container auth-page">
      <div className="auth-box">
        <h2><LogIn size={22} /> {isRegister ? "Create Account" : "Log In"}</h2>
        <p className="subtitle">
          {isRegister
            ? "Save your own path history, track progress, and more."
            : "Log in to see your saved paths and progress."}
        </p>
        {error && <div className="error-box">{error}</div>}
        <form onSubmit={submit} className="auth-form">
          <label>Username</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <button className="btn-primary" type="submit" disabled={loading || !username.trim() || !password}>
            {loading ? <Loader2 className="spin" size={18} /> : isRegister ? "Register" : "Log In"}
          </button>
        </form>
        <button className="auth-switch" onClick={() => setIsRegister((v) => !v)}>
          {isRegister ? "Already have an account? Log in" : "No account? Register"}
        </button>
      </div>
    </div>
  );
}
