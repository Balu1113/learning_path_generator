import { useState, useEffect } from "react";
import PeerCodeReview from "../components/PeerCodeReview";
import "../components/Layout.css";

export default function PeerReview() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(false);
  }, []);

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="page-container">
      <h1>Peer Code Review</h1>
      <PeerCodeReview />
    </div>
  );
}
