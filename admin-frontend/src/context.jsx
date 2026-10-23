import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { fetchMeta, me } from "./api";

const AuthContext = createContext(null);
const MetaContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    me()
      .then((d) => setUser(d.user))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo(() => ({ user, setUser, loading }), [user, loading]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

export function MetaProvider({ children }) {
  const [resources, setResources] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchMeta()
      .then((d) => setResources(d.resources))
      .catch((e) => setError(e.message || "Failed to load metadata"));
  }, []);

  const value = useMemo(() => ({ resources, error }), [resources, error]);
  return <MetaContext.Provider value={value}>{children}</MetaContext.Provider>;
}

export function useMeta() {
  return useContext(MetaContext);
}
