import { useState, useEffect } from "react";
import Marketplace from "../components/Marketplace";
import "../components/Layout.css";

export default function MarketplacePage() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(false);
  }, []);

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="page-container">
      <h1>Learning Path Marketplace</h1>
      <Marketplace />
    </div>
  );
}
