import React, { useState, useEffect } from 'react';
import { getCsrfToken } from '../api/client';

const Marketplace = () => {
  const [paths, setPaths] = useState([]);
  const [featured, setFeatured] = useState([]);
  const [myPurchases, setMyPurchases] = useState([]);
  const [myPaths, setMyPaths] = useState([]);
  const [selectedPath, setSelectedPath] = useState(null);
  const [activeTab, setActiveTab] = useState('browse');
  const [loading, setLoading] = useState(false);
  const [sort, setSort] = useState('-featured');
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (activeTab === 'browse') {
      loadPaths();
    } else if (activeTab === 'featured') {
      loadFeatured();
    } else if (activeTab === 'purchases') {
      loadMyPurchases();
    } else if (activeTab === 'created') {
      loadMyPaths();
    }
  }, [activeTab, sort, page]);

  const loadPaths = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/marketplace/browse?sort=${sort}&page=${page}`);
      const data = await res.json();
      setPaths(data.paths || []);
    } catch (error) {
      console.error('Failed to load paths:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadFeatured = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/marketplace/featured');
      const data = await res.json();
      setFeatured(data.paths || []);
    } catch (error) {
      console.error('Failed to load featured:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMyPurchases = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/marketplace/my-purchases');
      const data = await res.json();
      setMyPurchases(data.purchases || []);
    } catch (error) {
      console.error('Failed to load purchases:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMyPaths = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/marketplace/my-paths');
      const data = await res.json();
      setMyPaths(data.paths || []);
    } catch (error) {
      console.error('Failed to load paths:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadPathDetail = async (pathId) => {
    try {
      const res = await fetch(`/api/marketplace/paths/${pathId}`);
      const data = await res.json();
      setSelectedPath(data);
    } catch (error) {
      console.error('Failed to load path detail:', error);
    }
  };

  const purchasePath = async (pathId) => {
    try {
      const token = await getCsrfToken();
      const res = await fetch(`/api/marketplace/paths/${pathId}/purchase`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (res.ok) {
        loadPathDetail(pathId);
        loadMyPurchases();
      }
    } catch (error) {
      console.error('Failed to purchase:', error);
    }
  };

  const submitReview = async (pathId, rating, comment) => {
    try {
      const token = await getCsrfToken();
      const res = await fetch(`/api/marketplace/paths/${pathId}/review`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ rating, comment }),
      });

      if (res.ok) {
        loadPathDetail(pathId);
      }
    } catch (error) {
      console.error('Failed to submit review:', error);
    }
  };

  return (
    <div className="marketplace-container">
      <h1>Learning Path Marketplace</h1>

      <div className="marketplace-tabs">
        <button
          className={`tab ${activeTab === 'browse' ? 'active' : ''}`}
          onClick={() => setActiveTab('browse')}
        >
          Browse Paths
        </button>
        <button
          className={`tab ${activeTab === 'featured' ? 'active' : ''}`}
          onClick={() => setActiveTab('featured')}
        >
          Featured
        </button>
        <button
          className={`tab ${activeTab === 'purchases' ? 'active' : ''}`}
          onClick={() => setActiveTab('purchases')}
        >
          My Purchases
        </button>
        <button
          className={`tab ${activeTab === 'created' ? 'active' : ''}`}
          onClick={() => setActiveTab('created')}
        >
          My Paths
        </button>
      </div>

      {selectedPath ? (
        <PathDetail
          path={selectedPath}
          onBack={() => setSelectedPath(null)}
          onPurchase={purchasePath}
          onReview={submitReview}
        />
      ) : (
        <>
          {activeTab === 'browse' && (
            <div className="browse-section">
              <div className="sort-controls">
                <select value={sort} onChange={e => setSort(e.target.value)}>
                  <option value="-featured">Featured First</option>
                  <option value="-rating">Highest Rated</option>
                  <option value="-purchase_count">Most Popular</option>
                  <option value="price">Price: Low to High</option>
                  <option value="-price">Price: High to Low</option>
                </select>
              </div>

              <div className="paths-grid">
                {paths.length === 0 ? (
                  <div className="empty-state">No paths found</div>
                ) : (
                  paths.map(path => (
                    <PathCard
                      key={path.id}
                      path={path}
                      onClick={() => {
                        loadPathDetail(path.id);
                      }}
                    />
                  ))
                )}
              </div>
            </div>
          )}

          {activeTab === 'featured' && (
            <div className="featured-section">
              <div className="paths-grid">
                {featured.length === 0 ? (
                  <div className="empty-state">No featured paths</div>
                ) : (
                  featured.map(path => (
                    <PathCard
                      key={path.id}
                      path={path}
                      featured
                      onClick={() => loadPathDetail(path.id)}
                    />
                  ))
                )}
              </div>
            </div>
          )}

          {activeTab === 'purchases' && (
            <div className="purchases-section">
              <div className="purchases-list">
                {myPurchases.length === 0 ? (
                  <div className="empty-state">No purchases yet</div>
                ) : (
                  myPurchases.map(purchase => (
                    <div key={purchase.id} className="purchase-item">
                      <div className="purchase-title">{purchase.title}</div>
                      <div className="purchase-meta">
                        <span className="creator">by {purchase.creator}</span>
                        <span className="price">${purchase.price}</span>
                      </div>
                      <div className="purchase-date">
                        Purchased: {new Date(purchase.purchased_at).toLocaleDateString()}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {activeTab === 'created' && (
            <div className="created-section">
              <button className="btn-create">+ Create New Path</button>
              <div className="paths-list">
                {myPaths.length === 0 ? (
                  <div className="empty-state">No paths created yet</div>
                ) : (
                  myPaths.map(path => (
                    <div key={path.id} className="path-item">
                      <div className="path-title">{path.title}</div>
                      <div className="path-meta">
                        <span className={`status ${path.status}`}>{path.status}</span>
                        <span className="price">${path.price}</span>
                        <span className="rating">⭐ {path.rating}</span>
                      </div>
                      <div className="path-stats">
                        <span>{path.purchase_count} purchases</span>
                        {path.featured && <span className="featured-badge">Featured</span>}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </>
      )}

      <style jsx>{`
        .marketplace-container {
          padding: 20px;
          background: var(--bg-secondary);
          border-radius: 8px;
        }

        .marketplace-container h1 {
          margin-top: 0;
          color: var(--text-primary);
        }

        .marketplace-tabs {
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

        .sort-controls {
          margin-bottom: 20px;
        }

        .sort-controls select {
          padding: 8px 12px;
          border: 1px solid var(--border-color);
          border-radius: 4px;
          background: var(--bg-primary);
          color: var(--text-primary);
          cursor: pointer;
        }

        .paths-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 20px;
        }

        .paths-list {
          display: flex;
          flex-direction: column;
          gap: 15px;
        }

        .purchases-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .purchase-item {
          padding: 15px;
          background: var(--bg-primary);
          border: 1px solid var(--border-color);
          border-radius: 8px;
        }

        .purchase-title {
          font-weight: bold;
          margin-bottom: 8px;
          color: var(--text-primary);
        }

        .purchase-meta {
          display: flex;
          justify-content: space-between;
          font-size: 12px;
          margin-bottom: 8px;
        }

        .creator {
          color: var(--text-secondary);
        }

        .price {
          font-weight: bold;
          color: var(--primary-color);
        }

        .purchase-date {
          font-size: 11px;
          color: var(--text-secondary);
        }

        .path-item {
          padding: 15px;
          background: var(--bg-primary);
          border: 1px solid var(--border-color);
          border-radius: 8px;
        }

        .path-title {
          font-weight: bold;
          margin-bottom: 10px;
          color: var(--text-primary);
        }

        .path-meta {
          display: flex;
          gap: 15px;
          font-size: 12px;
          margin-bottom: 10px;
        }

        .status {
          padding: 2px 8px;
          border-radius: 3px;
          font-weight: bold;
        }

        .status.draft {
          background: #999;
          color: white;
        }

        .status.published {
          background: #4CAF50;
          color: white;
        }

        .rating {
          color: #FFB300;
        }

        .path-stats {
          display: flex;
          gap: 10px;
          font-size: 11px;
          color: var(--text-secondary);
        }

        .featured-badge {
          background: #FF9800;
          color: white;
          padding: 2px 6px;
          border-radius: 3px;
        }

        .btn-create {
          padding: 12px 20px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: bold;
          margin-bottom: 20px;
        }

        .btn-create:hover {
          opacity: 0.9;
        }

        .empty-state {
          text-align: center;
          padding: 40px 20px;
          color: var(--text-secondary);
        }

        @media (max-width: 768px) {
          .paths-grid {
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
          }
        }
      `}</style>
    </div>
  );
};

const PathCard = ({ path, featured, onClick }) => {
  return (
    <div className="path-card" onClick={onClick}>
      {path.thumbnail_url && (
        <div className="path-thumbnail">
          <img src={path.thumbnail_url} alt={path.title} />
        </div>
      )}
      {featured && <div className="featured-ribbon">Featured</div>}
      <div className="path-content">
        <h3>{path.title}</h3>
        <p className="description">{path.description}</p>
        <div className="path-footer">
          <div className="rating">
            ⭐ {path.rating} ({path.rating_count})
          </div>
          <div className="price">${path.price}</div>
        </div>
        <div className="creator">by {path.creator}</div>
      </div>

      <style jsx>{`
        .path-card {
          background: var(--bg-primary);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          overflow: hidden;
          cursor: pointer;
          transition: all 0.3s;
          display: flex;
          flex-direction: column;
        }

        .path-card:hover {
          transform: translateY(-4px);
          box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
          border-color: var(--primary-color);
        }

        .path-thumbnail {
          width: 100%;
          height: 150px;
          background: var(--border-color);
          overflow: hidden;
        }

        .path-thumbnail img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .featured-ribbon {
          position: absolute;
          top: 10px;
          right: 10px;
          background: #FF9800;
          color: white;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: bold;
        }

        .path-content {
          padding: 15px;
          flex: 1;
          display: flex;
          flex-direction: column;
        }

        .path-content h3 {
          margin: 0 0 8px 0;
          font-size: 16px;
          color: var(--text-primary);
        }

        .description {
          margin: 0 0 12px 0;
          font-size: 12px;
          color: var(--text-secondary);
          flex: 1;
        }

        .path-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
          font-size: 14px;
        }

        .rating {
          color: #FFB300;
          font-weight: bold;
        }

        .price {
          font-weight: bold;
          color: var(--primary-color);
        }

        .creator {
          font-size: 11px;
          color: var(--text-secondary);
        }
      `}</style>
    </div>
  );
};

const PathDetail = ({ path, onBack, onPurchase, onReview }) => {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');

  return (
    <div className="path-detail">
      <button className="btn-back" onClick={onBack}>← Back</button>

      <div className="detail-header">
        <h2>{path.title}</h2>
        <div className="detail-meta">
          <span className="creator">by {path.creator}</span>
          <span className="price">${path.price}</span>
        </div>
      </div>

      <div className="detail-content">
        <div className="description">{path.description}</div>

        {!path.purchased && (
          <button
            className="btn-purchase"
            onClick={() => onPurchase(path.id)}
          >
            Purchase Path
          </button>
        )}

        {path.purchased && (
          <div className="review-section">
            <h3>Leave a Review</h3>
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
            <textarea
              value={comment}
              onChange={e => setComment(e.target.value)}
              placeholder="Share your thoughts..."
              rows="3"
            />
            <button
              className="btn-submit"
              onClick={() => onReview(path.id, rating, comment)}
            >
              Submit Review
            </button>
          </div>
        )}

        {path.reviews && path.reviews.length > 0 && (
          <div className="reviews-section">
            <h3>Reviews</h3>
            {path.reviews.map((review, idx) => (
              <div key={idx} className="review-item">
                <div className="review-header">
                  <span className="author">{review.author}</span>
                  <span className="rating">⭐ {review.rating}/5</span>
                </div>
                <p>{review.comment}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <style jsx>{`
        .path-detail {
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

        .detail-header h2 {
          margin: 0 0 10px 0;
        }

        .detail-meta {
          display: flex;
          gap: 15px;
          font-size: 14px;
        }

        .creator {
          color: var(--text-secondary);
        }

        .price {
          font-weight: bold;
          color: var(--primary-color);
        }

        .detail-content {
          margin-top: 20px;
        }

        .description {
          margin-bottom: 20px;
          line-height: 1.6;
        }

        .btn-purchase {
          padding: 12px 24px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: bold;
          font-size: 16px;
        }

        .btn-purchase:hover {
          opacity: 0.9;
        }

        .review-section {
          margin-top: 20px;
          padding: 15px;
          background: var(--bg-secondary);
          border-radius: 8px;
        }

        .review-section h3 {
          margin-top: 0;
        }

        .rating-input {
          display: flex;
          gap: 5px;
          margin-bottom: 10px;
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

        textarea {
          width: 100%;
          padding: 10px;
          border: 1px solid var(--border-color);
          border-radius: 4px;
          background: var(--bg-primary);
          color: var(--text-primary);
          font-family: inherit;
          margin-bottom: 10px;
        }

        .btn-submit {
          padding: 8px 16px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: bold;
        }

        .reviews-section {
          margin-top: 20px;
        }

        .reviews-section h3 {
          margin-top: 0;
        }

        .review-item {
          padding: 12px;
          background: var(--bg-secondary);
          border-radius: 6px;
          margin-bottom: 10px;
        }

        .review-header {
          display: flex;
          justify-content: space-between;
          margin-bottom: 8px;
          font-size: 12px;
        }

        .author {
          font-weight: bold;
        }

        .rating {
          color: #FFB300;
        }

        .review-item p {
          margin: 0;
          font-size: 14px;
        }
      `}</style>
    </div>
  );
};

export default Marketplace;
