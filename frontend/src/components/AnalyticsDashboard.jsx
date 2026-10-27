import React, { useState, useEffect } from 'react';
import {
  getAnalyticsDashboard,
  getDailyMetrics,
  getLearningVelocity,
  getCohortComparison,
} from '../api/client';

const AnalyticsDashboard = ({ pathId }) => {
  const [analytics, setAnalytics] = useState(null);
  const [dailyMetrics, setDailyMetrics] = useState([]);
  const [velocity, setVelocity] = useState(null);
  const [cohort, setCohort] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadAnalytics();
  }, [pathId]);

  const loadAnalytics = async () => {
    if (!pathId) return;
    setLoading(true);
    setError('');
    try {
      const [analyticsRes, dailyRes, velocityRes, cohortRes] = await Promise.all([
        getAnalyticsDashboard(pathId),
        getDailyMetrics(pathId),
        getLearningVelocity(pathId),
        getCohortComparison(pathId),
      ]);

      const failed = [analyticsRes, dailyRes, velocityRes, cohortRes]
        .find((r) => r && r.error);
      if (failed) {
        setError(failed.error);
        setAnalytics(null);
        return;
      }

      setAnalytics(analyticsRes);
      setDailyMetrics(dailyRes.metrics || []);
      setVelocity(velocityRes);
      setCohort(cohortRes);
    } catch (err) {
      console.error('Failed to load analytics:', err);
      setError('Failed to load analytics. Please try again.');
      setAnalytics(null);
    } finally {
      setLoading(false);
    }
  };

  if (!pathId) {
    return <div className="analytics-loading">Select a learning path to see analytics.</div>;
  }

  if (loading) {
    return <div className="analytics-loading">Loading analytics...</div>;
  }

  if (error) {
    return (
      <div className="analytics-loading">
        <p>{error}</p>
        <button className="analytics-retry" onClick={loadAnalytics}>Retry</button>
      </div>
    );
  }

  if (!analytics) {
    return <div className="analytics-loading">No analytics data yet.</div>;
  }

  const getCompletionColor = (rate) => {
    if (rate >= 80) return '#4CAF50';
    if (rate >= 60) return '#FF9800';
    return '#F44336';
  };

  const hasActivity = dailyMetrics.some(
    (m) => m.time_minutes > 0 || m.topics_completed > 0 || m.tests_taken > 0
  );

  return (
    <div className="analytics-dashboard">
      <div className="analytics-grid">
        {/* Overview Cards */}
        <div className="analytics-card">
          <div className="card-label">Completion Rate</div>
          <div className="card-value" style={{ color: getCompletionColor(analytics.completion_rate) }}>
            {analytics.completion_rate}%
          </div>
          <div className="card-detail">
            {analytics.topics_completed} / {analytics.topics_total} topics
          </div>
        </div>

        <div className="analytics-card">
          <div className="card-label">Time Invested</div>
          <div className="card-value">{analytics.total_time_minutes}</div>
          <div className="card-detail">minutes</div>
        </div>

        <div className="analytics-card">
          <div className="card-label">Average Test Score</div>
          <div className="card-value">{analytics.average_test_score}%</div>
          <div className="card-detail">across all tests</div>
        </div>

        <div className="analytics-card">
          <div className="card-label">Days Active</div>
          <div className="card-value">{analytics.days_active}</div>
          <div className="card-detail">learning days</div>
        </div>
      </div>

      {/* Predictions */}
      {(analytics.predicted_completion_days || velocity) && (
        <div className="analytics-section">
          <h3>Predictions</h3>
          <div className="prediction-cards">
            {analytics.predicted_completion_days && (
              <div className="prediction-card">
                <div className="prediction-label">Estimated Completion</div>
                <div className="prediction-value">{analytics.predicted_completion_days} days</div>
                <div className="prediction-detail">at current pace</div>
              </div>
            )}
            {velocity && (
              <div className="prediction-card">
                <div className="prediction-label">Learning Velocity</div>
                <div className="prediction-value">{Number(velocity.topics_per_week || 0).toFixed(1)}</div>
                <div className="prediction-detail">topics per week</div>
              </div>
            )}
            {velocity && velocity.estimated_completion_weeks != null && (
              <div className="prediction-card">
                <div className="prediction-label">Weeks to Finish</div>
                <div className="prediction-value">{velocity.estimated_completion_weeks}</div>
                <div className="prediction-detail">at last week's pace</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Weak Areas */}
      {analytics.weak_areas && analytics.weak_areas.length > 0 && (
        <div className="analytics-section">
          <h3>Areas Needing Review</h3>
          <div className="weak-areas-list">
            {analytics.weak_areas.map((area, idx) => (
              <div key={idx} className="weak-area-item">
                <div className="area-name">{area.phase}</div>
                <div className="area-score">
                  <div className="score-bar">
                    <div
                      className="score-fill"
                      style={{ width: `${area.avg_score}%`, background: '#F44336' }}
                    />
                  </div>
                  <span>{area.avg_score}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cohort Comparison */}
      {cohort && (
        <div className="analytics-section">
          <h3>Cohort Comparison{cohort.cohort_size ? ` (${cohort.cohort_size} learners on this path)` : ''}</h3>
          <div className="cohort-comparison">
            <div className="comparison-item">
              <div className="comparison-label">Your Time</div>
              <div className="comparison-value">{cohort.user_time_minutes} min</div>
              <div className="comparison-avg">Cohort avg: {cohort.cohort_avg_time_minutes} min</div>
            </div>
            <div className="comparison-item">
              <div className="comparison-label">Your Progress</div>
              <div className="comparison-value">{cohort.user_topics_completed} topics</div>
              <div className="comparison-avg">Cohort avg: {cohort.cohort_avg_topics} topics</div>
            </div>
            <div className="comparison-item">
              <div className="comparison-label">Your Percentile</div>
              <div className="comparison-value">{cohort.percentile}%</div>
              <div className="comparison-avg">Better than {cohort.percentile}% of cohort</div>
            </div>
          </div>
        </div>
      )}

      {/* Daily Activity Chart */}
      <div className="analytics-section">
        <h3>Daily Activity (Last 30 Days)</h3>
        {hasActivity ? (
          <div className="daily-chart">
            {dailyMetrics.map((metric, idx) => (
              <div key={idx} className="chart-bar">
                <div
                  className="bar-fill"
                  style={{
                    height: metric.time_minutes > 0
                      ? `${Math.max(4, Math.min(100, (metric.time_minutes / 60) * 100))}%`
                      : '0%',
                  }}
                  title={`${metric.date}: ${metric.time_minutes} min · ${metric.topics_completed} topics · ${metric.tests_taken} tests`}
                />
              </div>
            ))}
          </div>
        ) : (
          <div className="chart-empty">No focus time logged in the last 30 days.</div>
        )}
      </div>

      <style jsx>{`
        .analytics-dashboard {
          padding: 20px;
          background: var(--bg-secondary);
          border-radius: 8px;
        }

        .analytics-dashboard h2 {
          margin-top: 0;
          color: var(--text-primary);
        }

        .analytics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 15px;
          margin-bottom: 30px;
        }

        .analytics-card {
          background: var(--bg-primary);
          padding: 20px;
          border-radius: 8px;
          border: 1px solid var(--border-color);
          text-align: center;
        }

        .card-label {
          font-size: 12px;
          color: var(--text-secondary);
          text-transform: uppercase;
          margin-bottom: 10px;
        }

        .card-value {
          font-size: 32px;
          font-weight: bold;
          margin-bottom: 5px;
        }

        .card-detail {
          font-size: 12px;
          color: var(--text-secondary);
        }

        .analytics-section {
          margin-bottom: 30px;
        }

        .analytics-section h3 {
          margin-top: 0;
          margin-bottom: 15px;
          color: var(--text-primary);
        }

        .prediction-cards {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 15px;
        }

        .prediction-card {
          background: var(--bg-primary);
          padding: 15px;
          border-radius: 8px;
          border-left: 4px solid var(--primary-color);
        }

        .prediction-label {
          font-size: 12px;
          color: var(--text-secondary);
          margin-bottom: 8px;
        }

        .prediction-value {
          font-size: 24px;
          font-weight: bold;
          color: var(--primary-color);
          margin-bottom: 5px;
        }

        .prediction-detail {
          font-size: 12px;
          color: var(--text-secondary);
        }

        .weak-areas-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .weak-area-item {
          display: flex;
          align-items: center;
          gap: 15px;
          padding: 12px;
          background: var(--bg-primary);
          border-radius: 6px;
        }

        .area-name {
          min-width: 150px;
          font-weight: 500;
        }

        .area-score {
          flex: 1;
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .score-bar {
          flex: 1;
          height: 8px;
          background: var(--border-color);
          border-radius: 4px;
          overflow: hidden;
        }

        .score-fill {
          height: 100%;
          transition: width 0.3s;
        }

        .cohort-comparison {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 15px;
        }

        .comparison-item {
          background: var(--bg-primary);
          padding: 15px;
          border-radius: 8px;
          border: 1px solid var(--border-color);
        }

        .comparison-label {
          font-size: 12px;
          color: var(--text-secondary);
          margin-bottom: 8px;
        }

        .comparison-value {
          font-size: 24px;
          font-weight: bold;
          color: var(--primary-color);
          margin-bottom: 5px;
        }

        .comparison-avg {
          font-size: 12px;
          color: var(--text-secondary);
        }

        .daily-chart {
          display: flex;
          align-items: flex-end;
          gap: 4px;
          height: 150px;
          background: var(--bg-primary);
          padding: 15px;
          border-radius: 8px;
          border: 1px solid var(--border-color);
        }

        .chart-bar {
          flex: 1;
          height: 100%;
          background: var(--border-color);
          border-radius: 4px 4px 0 0;
          overflow: hidden;
          cursor: pointer;
          transition: opacity 0.2s;
        }

        .bar-fill {
          width: 100%;
          background: linear-gradient(180deg, #4CAF50, #8BC34A);
          transition: all 0.3s;
        }

        .chart-bar:hover {
          opacity: 0.8;
        }

        .analytics-loading {
          padding: 40px;
          text-align: center;
          color: var(--text-secondary);
        }

        .analytics-retry {
          margin-top: 12px;
          padding: 8px 16px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 600;
        }

        .chart-empty {
          padding: 40px;
          text-align: center;
          color: var(--text-secondary);
          background: var(--bg-primary);
          border-radius: 8px;
          border: 1px solid var(--border-color);
        }

        @media (max-width: 768px) {
          .analytics-grid {
            grid-template-columns: repeat(2, 1fr);
          }

          .daily-chart {
            gap: 2px;
          }
        }
      `}</style>
    </div>
  );
};

export default AnalyticsDashboard;
