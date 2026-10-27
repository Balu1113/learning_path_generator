import React, { useState, useEffect, useRef } from 'react';
import { getCsrfToken } from '../api/client';

const VideoPlayer = ({ videoId }) => {
  const [video, setVideo] = useState(null);
  const [progress, setProgress] = useState(null);
  const [notes, setNotes] = useState([]);
  const [newNote, setNewNote] = useState('');
  const [currentTime, setCurrentTime] = useState(0);
  const [loading, setLoading] = useState(false);
  const playerRef = useRef(null);

  useEffect(() => {
    loadVideo();
  }, [videoId]);

  const loadVideo = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/videos/${videoId}`);
      const data = await res.json();
      setVideo(data);
      setProgress(data.progress);
      setNotes(data.notes || []);
    } catch (error) {
      console.error('Failed to load video:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateProgress = async (seconds) => {
    try {
      const token = await getCsrfToken();
      const res = await fetch(`/api/videos/${videoId}/progress`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ seconds_watched: seconds }),
      });

      if (res.ok) {
        const data = await res.json();
        setProgress(data);
      }
    } catch (error) {
      console.error('Failed to update progress:', error);
    }
  };

  const addNote = async () => {
    if (!newNote.trim()) return;

    try {
      const token = await getCsrfToken();
      const res = await fetch(`/api/videos/${videoId}/note`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          timestamp_seconds: currentTime,
          note: newNote,
        }),
      });

      if (res.ok) {
        const note = await res.json();
        setNotes([...notes, note]);
        setNewNote('');
      }
    } catch (error) {
      console.error('Failed to add note:', error);
    }
  };

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading || !video) {
    return <div className="video-loading">Loading video...</div>;
  }

  const progressPercent = progress ? (progress.seconds_watched / video.duration_seconds) * 100 : 0;

  return (
    <div className="video-player-container">
      <div className="video-player">
        {video.platform === 'youtube' && (
          <iframe
            ref={playerRef}
            width="100%"
            height="400"
            src={`https://www.youtube.com/embed/${video.video_id}`}
            title={video.title}
            frameBorder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        )}
        {video.platform === 'vimeo' && (
          <iframe
            ref={playerRef}
            width="100%"
            height="400"
            src={`https://player.vimeo.com/video/${video.video_id}`}
            title={video.title}
            frameBorder="0"
            allow="autoplay; fullscreen; picture-in-picture"
            allowFullScreen
          />
        )}
      </div>

      <div className="video-info">
        <h2>{video.title}</h2>
        <p className="description">{video.description}</p>

        {progress && (
          <div className="progress-section">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <div className="progress-text">
              {formatTime(progress.seconds_watched)} / {formatTime(video.duration_seconds)}
              {progress.completed && <span className="completed-badge">✓ Completed</span>}
            </div>
          </div>
        )}
      </div>

      <div className="video-content">
        <div className="notes-section">
          <h3>Notes</h3>
          <div className="note-input">
            <input
              type="text"
              value={newNote}
              onChange={e => setNewNote(e.target.value)}
              placeholder="Add a note at current timestamp..."
              onKeyPress={e => e.key === 'Enter' && addNote()}
            />
            <button onClick={addNote} className="btn-add-note">
              Add Note @ {formatTime(currentTime)}
            </button>
          </div>

          <div className="notes-list">
            {notes.length === 0 ? (
              <div className="empty-notes">No notes yet</div>
            ) : (
              notes.map(note => (
                <div key={note.id} className="note-item">
                  <div className="note-timestamp">{formatTime(note.timestamp)}</div>
                  <div className="note-text">{note.note}</div>
                </div>
              ))
            )}
          </div>
        </div>

        {video.transcript && (
          <div className="transcript-section">
            <h3>Transcript</h3>
            <div className="transcript-content">
              {video.transcript}
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .video-player-container {
          padding: 20px;
          background: var(--bg-secondary);
          border-radius: 8px;
        }

        .video-player {
          margin-bottom: 20px;
          border-radius: 8px;
          overflow: hidden;
          background: #000;
        }

        .video-player iframe {
          display: block;
        }

        .video-info {
          margin-bottom: 20px;
        }

        .video-info h2 {
          margin: 0 0 10px 0;
          color: var(--text-primary);
        }

        .description {
          margin: 0 0 15px 0;
          color: var(--text-secondary);
          line-height: 1.6;
        }

        .progress-section {
          margin-top: 15px;
        }

        .progress-bar {
          width: 100%;
          height: 8px;
          background: var(--border-color);
          border-radius: 4px;
          overflow: hidden;
          margin-bottom: 8px;
        }

        .progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #4CAF50, #8BC34A);
          transition: width 0.3s;
        }

        .progress-text {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 12px;
          color: var(--text-secondary);
        }

        .completed-badge {
          background: #4CAF50;
          color: white;
          padding: 2px 8px;
          border-radius: 3px;
          font-weight: bold;
        }

        .video-content {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
        }

        .notes-section {
          background: var(--bg-primary);
          padding: 15px;
          border-radius: 8px;
          border: 1px solid var(--border-color);
        }

        .notes-section h3 {
          margin-top: 0;
          margin-bottom: 15px;
        }

        .note-input {
          display: flex;
          gap: 10px;
          margin-bottom: 15px;
        }

        .note-input input {
          flex: 1;
          padding: 8px 12px;
          border: 1px solid var(--border-color);
          border-radius: 4px;
          background: var(--bg-secondary);
          color: var(--text-primary);
        }

        .btn-add-note {
          padding: 8px 12px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: bold;
          white-space: nowrap;
        }

        .btn-add-note:hover {
          opacity: 0.9;
        }

        .notes-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
          max-height: 400px;
          overflow-y: auto;
        }

        .empty-notes {
          text-align: center;
          padding: 20px;
          color: var(--text-secondary);
          font-size: 12px;
        }

        .note-item {
          padding: 10px;
          background: var(--bg-secondary);
          border-radius: 4px;
          border-left: 3px solid var(--primary-color);
        }

        .note-timestamp {
          font-size: 11px;
          color: var(--primary-color);
          font-weight: bold;
          margin-bottom: 4px;
        }

        .note-text {
          font-size: 13px;
          color: var(--text-primary);
        }

        .transcript-section {
          background: var(--bg-primary);
          padding: 15px;
          border-radius: 8px;
          border: 1px solid var(--border-color);
        }

        .transcript-section h3 {
          margin-top: 0;
          margin-bottom: 15px;
        }

        .transcript-content {
          font-size: 12px;
          line-height: 1.6;
          color: var(--text-secondary);
          max-height: 400px;
          overflow-y: auto;
          white-space: pre-wrap;
          word-wrap: break-word;
        }

        .video-loading {
          padding: 40px;
          text-align: center;
          color: var(--text-secondary);
        }

        @media (max-width: 768px) {
          .video-content {
            grid-template-columns: 1fr;
          }

          .video-player iframe {
            height: 250px;
          }
        }
      `}</style>
    </div>
  );
};

export default VideoPlayer;
