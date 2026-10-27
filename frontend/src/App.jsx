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
import Portfolio from "./pages/Portfolio";
import JobTarget from "./pages/JobTarget";
import Gamification from "./pages/Gamification";
import Analytics from "./pages/Analytics";
import SkillGraphPage from "./pages/SkillGraphPage";
import PeerReview from "./pages/PeerReview";
import MarketplacePage from "./pages/MarketplacePage";
import VideoLibrary from "./pages/VideoLibrary";
import VoiceTutorPage from "./pages/VoiceTutorPage";
import PracticeScenarioPage from "./pages/PracticeScenarioPage";

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
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/portfolio/:username" element={<Portfolio />} />
            <Route path="/job-target" element={<JobTarget />} />
            <Route path="/gamification" element={<Gamification />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/skills" element={<SkillGraphPage />} />
            <Route path="/peer-review" element={<PeerReview />} />
            <Route path="/marketplace" element={<MarketplacePage />} />
            <Route path="/videos" element={<VideoLibrary />} />
            <Route path="/voice-tutor" element={<VoiceTutorPage />} />
            <Route path="/practice" element={<PracticeScenarioPage />} />
            <Route path="/p/:slug" element={<SharePage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
