import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Projects from "./pages/Projects";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Tasks from "./pages/Tasks";
import Users from "./pages/Users";
import Settings from "./pages/Settings";
import P049Dashboard from "./pages/P049Dashboard";
import P049Login from "./pages/P049Login";
import P049UserProfile from "./pages/P049UserProfile";
import P049ProjectMembers from "./pages/P049ProjectMembers";

export default function Router() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/p049/login" element={<P049Login />} />
        <Route path="/p049" element={<P049Dashboard />} />
        <Route path="/p049/profile" element={<P049UserProfile />} />
        <Route path="/p049/members" element={<P049ProjectMembers />} />
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/users" element={<Users />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
