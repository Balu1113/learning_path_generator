import React, { useState, useEffect } from 'react';
import { getCsrfToken } from '../api/client';

const PeerCodeReview = () => {
  const [pendingProjects, setPendingProjects] = useState([]);
  const [selectedReview, setSelectedReview] = useState(null);
  const [reviewDetails, setReviewDetails] = useState(null);
  const [reputation, setReputation] = useState(null);
  const [myReviews, setMyReviews] = useState([]);
  const [activeTab, setActiveTab] = useState('pending');
  const [loading, setLoading] = useState(false);
  const [newComment, setNewComment] = useState('');

  useEffect(() => {
    loadReviewData();
  }, []);

  const loadReviewData = async () => {
    setLoading(true);
    try {
      const [pendingRes, reputationRes, myReviewsRes] = await Promise.all([
        fetch('/api/reviews/pending').then(r => r.json()),
        fetch('/api/reviews/reputation').then(r => r.json()),
        fetch('/api/reviews/my-reviews').then(r => r.json()),
      ]);

      setPendingProjects(pendingRes.projects || []);
      setReputation(reputationRes);
      setMyReviews(myReviewsRes.reviews || []);
    } catch (error) {
      console.error('Failed to load review data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadReviewDetails = async (reviewId) => {
    try {
      const res = await fetch(`/api/reviews/${reviewId}`);
      const data = await res.json();
      setReviewDetails(data);
    } catch (error) {
      console.error('Failed to load review details:', error);
    }
  };

  const startReview = async (projectId) => {
    try {
      const token = await getCsrfToken();
      const res = await fetch(`/api/reviews/create/${projectId}`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({}),
      });

      if (res.ok) {
        const data = await res.json();
        setSelectedReview(data.id);
        loadReviewDetails(data.id);
      }
    } catch (error) {
      console.error('Failed to start review:', error);
    }
  };

  const addComment = async (lineNumber, codeSnippet) => {
    if (!newComment.trim() || !selectedReview) return;

    try {
      const token = await getCsrfToken();
      const res = await fetch(`/api/reviews/${selectedReview}/comment`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          line_number: lineNumber,
          code_snippet: codeSnippet,
          comment: newComment,
        }),
      });

      if (res.ok) {
        setNewComment('');
        loadReviewDetails(selectedReview);
      }
    } catch (error) {
      console.error('Failed to add comment:', error);
    }
  };

  const submitReview = async (status, rating, summary) => {
    try {
      const token = await getCsrfToken();
      const res = await fetch(`/api/reviews/${selectedReview}/submit`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ status, rating, summary }),
      });

      if (res.ok) {
        loadReviewData();
        setSelectedReview(null);
        setReviewDetails(null);
      }
    } catch (error) {
      console.error('Failed to submit review:', error);
    }
  };

  return (
    <div className="peer-review-container">
      <div className="review-header">
        <h2>Peer Code Review</h2>
        {reputation && (
          <div className="reputation-badge">
            <span className="karma-label">Karma:</span>
            <span className="karma-value">{reputation.total_karma}</span>
            <span className="reputation-level">{reputation.reputation_level}</span>
          </div>
        )}
      </div>

      <div className="review-tabs">
        <button
          className={`tab ${activeTab === 'pending' ? 'active' : ''}`}
          onClick={() => setActiveTab('pending')}
        >
          Pending Reviews ({pendingProjects.length})
        </button>
        <button
          className={`tab ${activeTab === 'my-reviews' ? 'active' : ''}`}
          onClick={() => setActiveTab('my-reviews')}
        >
          My Reviews ({myReviews.length})
        </button>
      </div>

      {activeTab === 'pending' && (
        <div className="review-content">
          {selectedReview && reviewDetails ? (
            <ReviewEditor
              review={reviewDetails}
              onAddComment={addComment}
              onSubmit={submitReview}
              onBack={() => {
                setSelectedReview(null);
                setReviewDetails(null);
              }}
            />
          ) : (
            <div className="projects-list">
              {pendingProjects.length === 0 ? (
                <div className="empty-state">No projects pending review</div>
              ) : (
                pendingProjects.map(project => (
                  <div key={project.id} className="project-card">
                    <div className="project-header">
                      <h4>{project.title}</h4>
                      <span className="author">by {project.author}</span>
                    </div>
                    <div className="project-meta">
                      <span className="phase">{project.phase}</span>
                      <span className="reviews">{project.review_count} reviews</span>
                    </div>
                    <p className="project-url">{project.submission_url}</p>
                    <button
                      className="btn-review"
                      onClick={() => {
                        startReview(project.id);
                        setSelectedReview(project.id);
                      }}
                    >
                      Start Review
                    </button>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === 'my-reviews' && (
        <div className="review-content">
          <div className="my-reviews-list">
            {myReviews.length === 0 ? (
              <div className="empty-state">No reviews given yet</div>
            ) : (
              myReviews.map(review => (
                <div key={review.id} className="review-item">
                  <div className="review-title">{review.project_title}</div>
                  <div className="review-meta">
                    <span className="author">by {review.author}</span>
                    <span className={`status ${review.status}`}>{review.status}</span>
                    {review.rating && <span className="rating">⭐ {review.rating}/5</span>}
                  </div>
                  <div className="review-date">{new Date(review.created_at).toLocaleDateString()}</div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      <style jsx>{`
        .peer-review-container {
          padding: 20px;
          background: var(--bg-secondary);
          border-radius: 8px;
        }

        .review-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }

        .review-header h2 {
          margin: 0;
          color: var(--text-primary);
        }

        .reputation-badge {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 8px 15px;
          background: var(--primary-color);
          color: white;
          border-radius: 20px;
          font-size: 14px;
        }

        .karma-label {
          font-weight: bold;
        }

        .karma-value {
          font-size: 18px;
          font-weight: bold;
        }

        .reputation-level {
          font-size: 12px;
          opacity: 0.9;
        }

        .review-tabs {
          display: flex;
          gap: 10px;
          margin-bottom: 20px;
          border-bottom: 2px solid var(--border-color);
        }

        .tab {
          background: none;
          border: none;
          padding: 10px 15px;
          cursor: pointer;
          color: var(--text-secondary);
          font-weight: 500;
          border-bottom: 3px solid transparent;
          transition: all 0.3s;
        }

        .tab.active {
          color: var(--primary-color);
          border-bottom-color: var(--primary-color);
        }

        .review-content {
          min-height: 300px;
        }

        .projects-list {
          display: flex;
          flex-direction: column;
          gap: 15px;
        }

        .project-card {
          padding: 15px;
          background: var(--bg-primary);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          transition: all 0.3s;
        }

        .project-card:hover {
          border-color: var(--primary-color);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .project-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 10px;
        }

        .project-header h4 {
          margin: 0;
          color: var(--text-primary);
        }

        .author {
          font-size: 12px;
          color: var(--text-secondary);
        }

        .project-meta {
          display: flex;
          gap: 15px;
          margin-bottom: 10px;
          font-size: 12px;
        }

        .phase {
          padding: 4px 8px;
          background: var(--border-color);
          border-radius: 4px;
        }

        .reviews {
          color: var(--text-secondary);
        }

        .project-url {
          margin: 8px 0;
          font-size: 12px;
          color: var(--primary-color);
          word-break: break-all;
        }

        .btn-review {
          padding: 8px 16px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: bold;
        }

        .btn-review:hover {
          opacity: 0.9;
        }

        .my-reviews-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .review-item {
          padding: 15px;
          background: var(--bg-primary);
          border-left: 4px solid var(--primary-color);
          border-radius: 4px;
        }

        .review-title {
          font-weight: bold;
          margin-bottom: 8px;
          color: var(--text-primary);
        }

        .review-meta {
          display: flex;
          gap: 15px;
          font-size: 12px;
          margin-bottom: 8px;
        }

        .status {
          padding: 2px 8px;
          border-radius: 3px;
          font-weight: bold;
        }

        .status.approved {
          background: #4CAF50;
          color: white;
        }

        .status.changes_requested {
          background: #FF9800;
          color: white;
        }

        .status.pending {
          background: #999;
          color: white;
        }

        .rating {
          color: #FFB300;
        }

        .review-date {
          font-size: 11px;
          color: var(--text-secondary);
        }

        .empty-state {
          text-align: center;
          padding: 40px 20px;
          color: var(--text-secondary);
        }
      `}</style>
    </div>
  );
};

const ReviewEditor = ({ review, onAddComment, onSubmit, onBack }) => {
  const [rating, setRating] = useState(0);
  const [summary, setSummary] = useState('');
  const [status, setStatus] = useState('approved');

  return (
    <div className="review-editor">
      <button className="btn-back" onClick={onBack}>← Back</button>

      <div className="editor-header">
        <h3>Reviewing: {review.reviewer}</h3>
      </div>

      <div className="comments-section">
        <h4>Comments ({review.comments.length})</h4>
        <div className="comments-list">
          {review.comments.map(comment => (
            <div key={comment.id} className="comment-item">
              <div className="comment-header">
                <span className="comment-author">{comment.author}</span>
                <span className="comment-line">Line {comment.line_number}</span>
              </div>
              {comment.code_snippet && (
                <div className="code-snippet">{comment.code_snippet}</div>
              )}
              <div className="comment-text">{comment.comment}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="review-form">
        <div className="form-group">
          <label>Rating</label>
          <div className="rating-input">
            {[1, 2, 3, 4, 5].map(r => (
              <button
                key={r}
                className={`star ${rating >= r ? 'active' : ''}`}
                onClick={() => setRating(r)}
              >
                ⭐
              </button>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label>Status</label>
          <select value={status} onChange={e => setStatus(e.target.value)}>
            <option value="approved">Approved</option>
            <option value="changes_requested">Changes Requested</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>

        <div className="form-group">
          <label>Summary</label>
          <textarea
            value={summary}
            onChange={e => setSummary(e.target.value)}
            placeholder="Overall feedback..."
            rows="4"
          />
        </div>

        <button
          className="btn-submit"
          onClick={() => onSubmit(status, rating, summary)}
        >
          Submit Review
        </button>
      </div>

      <style jsx>{`
        .review-editor {
          padding: 20px;
          background: var(--bg-primary);
          border-radius: 8px;
        }

        .btn-back {
          background: none;
          border: none;
          color: var(--primary-color);
          cursor: pointer;
          font-weight: bold;
          margin-bottom: 15px;
        }

        .editor-header h3 {
          margin: 0 0 15px 0;
        }

        .comments-section {
          margin-bottom: 25px;
        }

        .comments-section h4 {
          margin-top: 0;
          margin-bottom: 12px;
        }

        .comments-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .comment-item {
          padding: 12px;
          background: var(--bg-secondary);
          border-left: 3px solid var(--primary-color);
          border-radius: 4px;
        }

        .comment-header {
          display: flex;
          justify-content: space-between;
          margin-bottom: 8px;
          font-size: 12px;
        }

        .comment-author {
          font-weight: bold;
        }

        .comment-line {
          color: var(--text-secondary);
        }

        .code-snippet {
          background: #f5f5f5;
          padding: 8px;
          border-radius: 4px;
          font-family: monospace;
          font-size: 12px;
          margin-bottom: 8px;
          overflow-x: auto;
        }

        .comment-text {
          font-size: 14px;
        }

        .review-form {
          padding-top: 20px;
          border-top: 1px solid var(--border-color);
        }

        .form-group {
          margin-bottom: 15px;
        }

        .form-group label {
          display: block;
          margin-bottom: 8px;
          font-weight: bold;
        }

        .rating-input {
          display: flex;
          gap: 5px;
        }

        .star {
          background: none;
          border: none;
          font-size: 24px;
          cursor: pointer;
          opacity: 0.3;
          transition: opacity 0.2s;
        }

        .star.active {
          opacity: 1;
        }

        select,
        textarea {
          width: 100%;
          padding: 10px;
          border: 1px solid var(--border-color);
          border-radius: 4px;
          background: var(--bg-primary);
          color: var(--text-primary);
          font-family: inherit;
        }

        .btn-submit {
          width: 100%;
          padding: 12px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: bold;
          font-size: 16px;
        }

        .btn-submit:hover {
          opacity: 0.9;
        }
      `}</style>
    </div>
  );
};

export default PeerCodeReview;
