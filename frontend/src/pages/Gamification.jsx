import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Gamepad2, LogIn } from "lucide-react";
import GamificationPanel from "../components/GamificationPanel";
import { useAuth } from "../auth";
import "../components/Layout.css";

export default function Gamification() {
  const { user, loading: authLoading } = useAuth();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(false);
  }, []);

  if (authLoading || loading) return <div className="loading">Loading...</div>;

  if (!user) {
    return (
      <div className="page-container">
        <div className="page-header">
          <Gamepad2 size={28} />
          <div>
            <h2>Gamification & Achievements</h2>
            <p className="subtitle">Track XP, levels, quests, and leaderboard</p>
          </div>
        </div>
        <div className="study-guest">
          <div className="study-guest-card">
            <div className="study-card-title"><Gamepad2 size={20} /> Gamification</div>
            <h2>Earn XP as you learn</h2>
            <p>
              Complete topics, pass tests, solve challenges, and finish quests to earn XP,
              level up, maintain streaks, and climb the leaderboard.
            </p>
            <Link to="/login" className="btn-primary study-btn-lg">
              <LogIn size={16} /> Log in to track progress
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <Gamepad2 size={28} />
        <div>
          <h2>Gamification & Achievements</h2>
          <p className="subtitle">Track XP, levels, quests, and leaderboard</p>
        </div>
      </div>
      <GamificationPanel />
    </div>
  );
}
