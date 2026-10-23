import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import { AuthProvider } from "./auth";
import AgentMode from "./pages/AgentMode";
import QuickPath from "./pages/QuickPath";
import DomainOverview from "./pages/DomainOverview";
import PathHistory from "./pages/PathHistory";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Help from "./pages/Help";
import Study from "./pages/Study";
import Onboarding from "./pages/Onboarding";
import SharePage from "./pages/SharePage";
import Gallery from "./pages/Gallery";
import Groups from "./pages/Groups";
import ResourceExplorer from "./pages/ResourceExplorer";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<AgentMode />} />
            <Route path="/quick" element={<QuickPath />} />
            <Route path="/domains" element={<DomainOverview />} />
            <Route path="/resources" element={<ResourceExplorer />} />
            <Route path="/study" element={<Study />} />
            <Route path="/history" element={<PathHistory />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/login" element={<Login />} />
            <Route path="/help" element={<Help />} />
            <Route path="/onboarding" element={<Onboarding />} />
            <Route path="/gallery" element={<Gallery />} />
            <Route path="/groups" element={<Groups />} />
            <Route path="/p/:slug" element={<SharePage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
