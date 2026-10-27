import { useState, useEffect } from "react";
import PracticeScenarios from "../components/PracticeScenarios";
import "../components/Layout.css";

export default function PracticeScenarioPage() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(false);
  }, []);

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="page-container">
      <h1>Practice Scenarios</h1>
      <PracticeScenarios />
    </div>
  );
}
