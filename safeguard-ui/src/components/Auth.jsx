import { createContext, useContext, useState } from "react";
import { api } from "../api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const u = localStorage.getItem("sg_user");
    return u ? JSON.parse(u) : null;
  });

  async function login(username, password) {
    const res = await api.login(username, password);
    localStorage.setItem("sg_token", res.token);
    localStorage.setItem("sg_user", JSON.stringify({ username: res.username, role: res.role }));
    setUser({ username: res.username, role: res.role });
    return res;
  }

  async function logout() {
    await api.logout().catch(() => {});
    localStorage.removeItem("sg_token");
    localStorage.removeItem("sg_user");
    setUser(null);
  }

  return (
    <AuthCtx.Provider value={{ user, login, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
