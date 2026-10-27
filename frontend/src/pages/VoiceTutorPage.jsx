import { useState, useEffect } from "react";
import VoiceTutor from "../components/VoiceTutor";
import "../components/Layout.css";

export default function VoiceTutorPage() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(false);
  }, []);

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="page-container">
      <h1>Voice Tutor & Practice</h1>
      <VoiceTutor />
    </div>
  );
}
