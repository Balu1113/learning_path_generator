import { useState, useEffect } from "react";
import VideoPlayer from "../components/VideoPlayer";
import "../components/Layout.css";

export default function VideoLibrary() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(false);
  }, []);

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="page-container">
      <h1>Video Learning Library</h1>
      <VideoPlayer />
    </div>
  );
}
