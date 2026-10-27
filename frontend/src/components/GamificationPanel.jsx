import React, { useState, useEffect } from 'react';
import { getCsrfToken } from '../api/client';

const GamificationPanel = () => {
  const [level, setLevel] = useState(null);
  const [quests, setQuests] = useState([]);
  const [streak, setStreak] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [activeTab, setActiveTab] = useState('level');
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [answers, setAnswers] = useState({});
  const [feedback, setFeedback] = useState({});
  const [submitting, setSubmitting] = useState(null);

  useEffect(() => {
    loadGamificationData();
  }, []);

  const loadGamificationData = async () => {
    setLoading(true);
    try {
      const [levelRes, questsRes, streakRes, leaderboardRes] = await Promise.all([
        fetch('/api/gamification/level', { credentials: 'include' }).then(r => r.json()),
        fetch('/api/gamification/quests', { credentials: 'include' }).then(r => r.json()),
        fetch('/api/gamification/streak', { credentials: 'include' }).then(r => r.json()),
        fetch('/api/gamification/leaderboard', { credentials: 'include' }).then(r => r.json()),
      ]);

      if (levelRes.error || questsRes.error || streakRes.error || leaderboardRes.error) {
        // User might not be logged in
        setLevel(null);
        setQuests([]);
        setStreak(null);
        setLeaderboard([]);
        return;
      }

      setLevel(levelRes);
      setQuests(questsRes.quests || []);
      setStreak(streakRes);
      setLeaderboard(leaderboardRes.leaderboard || []);
    } catch (error) {
      console.error('Failed to load gamification data:', error);
    } finally {
      setLoading(false);
    }
  };

  const submitQuest = async (quest, answer = '') => {
    setSubmitting(quest.id);
    try {
      const token = await getCsrfToken();
      const res = await fetch(`/api/gamification/quests/${quest.id}/complete`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ answer }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setFeedback(f => ({
          ...f,
          [quest.id]: { correct: false, message: data.error || 'Something went wrong' },
        }));
        return;
      }
      if (data.correct === false) {
        setFeedback(f => ({
          ...f,
          [quest.id]: { correct: false, message: 'Not quite — try again!' },
        }));
        return;
      }
      setFeedback(f => ({
        ...f,
        [quest.id]: data.completed
          ? { correct: true, message: `Correct! Quest complete +${data.xp_earned} XP` }
          : { correct: true, message: 'Correct! Next question unlocked.' },
      }));
      setAnswers(a => ({ ...a, [quest.id]: '' }));
      loadGamificationData();
    } catch (error) {
      console.error('Failed to submit quest answer:', error);
    } finally {
      setSubmitting(null);
    }
  };

  const generateQuests = async () => {
    setGenerating(true);
    try {
      const token = await getCsrfToken();
      const res = await fetch('/api/gamification/quests/generate', {
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
        setQuests(data.quests || []);
        setFeedback({});
        setAnswers({});
      }
    } catch (error) {
      console.error('Failed to generate quests:', error);
    } finally {
      setGenerating(false);
    }
  };

  const getLevelColor = (level) => {
    const colors = {
      novice: '#888',
      beginner: '#4CAF50',
      intermediate: '#2196F3',
      advanced: '#FF9800',
      expert: '#9C27B0',
    };
    return colors[level] || '#888';
  };

  const getXPProgress = () => {
    if (!level) return 0;
    return (level.xp_progress / level.xp_to_next_level) * 100;
  };

  return (
    <div className="gamification-panel">
      <div className="gamification-tabs">
        <button
          className={`tab ${activeTab === 'level' ? 'active' : ''}`}
          onClick={() => setActiveTab('level')}
        >
          Level & XP
        </button>
        <button
          className={`tab ${activeTab === 'quests' ? 'active' : ''}`}
          onClick={() => setActiveTab('quests')}
        >
          Daily Quests
        </button>
        <button
          className={`tab ${activeTab === 'leaderboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('leaderboard')}
        >
          Leaderboard
        </button>
      </div>

      {activeTab === 'level' && level && (
        <div className="gamification-content">
          <div className="level-card">
            <div className="level-badge" style={{ borderColor: getLevelColor(level.level) }}>
              <div className="level-text">{level.level.toUpperCase()}</div>
            </div>
            <div className="xp-info">
              <div className="xp-total">Total XP: {level.xp_total}</div>
              <div className="xp-progress-bar">
                <div
                  className="xp-progress-fill"
                  style={{ width: `${getXPProgress()}%` }}
                />
              </div>
              <div className="xp-next">{level.xp_progress} / {level.xp_to_next_level} XP</div>
            </div>
          </div>

          {streak && (
            <div className="streak-card">
              <div className="streak-icon">🔥</div>
              <div className="streak-info">
                <div className="streak-current">{streak.current_streak_days} day streak</div>
                <div className="streak-best">Best: {streak.longest_streak_days} days</div>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'quests' && (
        <div className="gamification-content">
          <div className="quests-toolbar">
            <button
              className="btn-generate"
              onClick={generateQuests}
              disabled={generating}
            >
              {generating ? 'Generating…' : '✨ Generate Today\'s Quests'}
            </button>
          </div>
          <div className="quests-list">
            {quests.length === 0 ? (
              <div className="empty-state">
                {generating
                  ? 'Creating personalized quiz quests with AI…'
                  : 'No quests available today — hit "Generate" to create AI quiz quests from your learning path topics.'}
              </div>
            ) : (
              quests.map(quest => {
                const currentQuestion = quest.is_quiz && !quest.completed
                  ? (quest.questions || []).find(q => q.index === quest.progress_count) || (quest.questions || [])[0]
                  : null;
                const fb = feedback[quest.id];
                return (
                  <div key={quest.id} className={`quest-card ${quest.completed ? 'completed' : ''}`}>
                    <div className="quest-header">
                      <h4>{quest.title}</h4>
                      <span className={`difficulty ${quest.difficulty}`}>{quest.difficulty}</span>
                    </div>
                    <p className="quest-description">{quest.description}</p>

                    {currentQuestion && (
                      <div className="quest-question">
                        <div className="question-text">
                          Q{quest.progress_count + 1} of {quest.target_count}: {currentQuestion.question}
                        </div>
                        <div className="question-row">
                          <input
                            type="text"
                            className="answer-input"
                            placeholder="Type your answer…"
                            value={answers[quest.id] || ''}
                            onChange={e => setAnswers(a => ({ ...a, [quest.id]: e.target.value }))}
                            onKeyDown={e => {
                              if (e.key === 'Enter' && (answers[quest.id] || '').trim()) {
                                submitQuest(quest, answers[quest.id]);
                              }
                            }}
                            disabled={submitting === quest.id}
                          />
                          <button
                            className="btn-complete"
                            onClick={() => submitQuest(quest, answers[quest.id] || '')}
                            disabled={submitting === quest.id || !(answers[quest.id] || '').trim()}
                          >
                            {submitting === quest.id ? 'Checking…' : 'Submit Answer'}
                          </button>
                        </div>
                        {fb && (
                          <div className={`answer-feedback ${fb.correct ? 'correct' : 'wrong'}`}>
                            {fb.message}
                          </div>
                        )}
                      </div>
                    )}

                    {!quest.is_quiz && (
                      <div className="quest-footer">
                        <span className="xp-reward">+{quest.xp_reward} XP</span>
                        {quest.target_count > 1 && !quest.completed && (
                          <span className="quest-progress">{quest.progress_count} / {quest.target_count}</span>
                        )}
                        {!quest.completed && (
                          <button
                            className="btn-complete"
                            onClick={() => submitQuest(quest)}
                            disabled={submitting === quest.id}
                          >
                            {quest.target_count > 1 ? 'Do Quest' : 'Complete'}
                          </button>
                        )}
                      </div>
                    )}

                    {quest.is_quiz && quest.completed && (
                      <div className="quest-footer">
                        <span className="xp-reward">+{quest.xp_reward} XP</span>
                        <span className="completed-badge">✓ Completed</span>
                      </div>
                    )}
                    {quest.is_quiz && !quest.completed && !currentQuestion && (
                      <div className="quest-footer">
                        <span className="xp-reward">+{quest.xp_reward} XP</span>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {activeTab === 'leaderboard' && (
        <div className="gamification-content">
          <div className="leaderboard-list">
            {leaderboard.length === 0 ? (
              <div className="empty-state">No leaderboard data</div>
            ) : (
              leaderboard.map((entry, idx) => (
                <div key={idx} className="leaderboard-entry">
                  <div className="rank">#{entry.rank}</div>
                  <div className="username">{entry.username}</div>
                  <div className="score">{entry.score} pts</div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      <style jsx>{`
        .gamification-panel {
          background: var(--bg-secondary);
          border-radius: 8px;
          padding: 20px;
          margin: 20px 0;
        }

        .gamification-tabs {
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

        .gamification-content {
          display: flex;
          flex-direction: column;
          gap: 15px;
        }

        .level-card {
          display: flex;
          align-items: center;
          gap: 20px;
          padding: 20px;
          background: var(--bg-primary);
          border-radius: 8px;
          border: 2px solid var(--border-color);
        }

        .level-badge {
          width: 100px;
          height: 100px;
          border-radius: 50%;
          border: 4px solid;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 24px;
          font-weight: bold;
          color: var(--primary-color);
        }

        .xp-info {
          flex: 1;
        }

        .xp-total {
          font-size: 18px;
          font-weight: bold;
          margin-bottom: 10px;
        }

        .xp-progress-bar {
          width: 100%;
          height: 8px;
          background: var(--border-color);
          border-radius: 4px;
          overflow: hidden;
          margin-bottom: 5px;
        }

        .xp-progress-fill {
          height: 100%;
          background: linear-gradient(90deg, #4CAF50, #8BC34A);
          transition: width 0.3s;
        }

        .xp-next {
          font-size: 12px;
          color: var(--text-secondary);
        }

        .streak-card {
          display: flex;
          align-items: center;
          gap: 15px;
          padding: 15px;
          background: var(--bg-primary);
          border-radius: 8px;
          border-left: 4px solid #FF9800;
        }

        .streak-icon {
          font-size: 32px;
        }

        .streak-info {
          flex: 1;
        }

        .streak-current {
          font-size: 16px;
          font-weight: bold;
        }

        .streak-best {
          font-size: 12px;
          color: var(--text-secondary);
        }

        .quests-toolbar {
          display: flex;
          justify-content: flex-end;
        }

        .btn-generate {
          padding: 8px 16px;
          background: linear-gradient(135deg, #4CAF50, #2196F3);
          color: white;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          font-size: 13px;
          font-weight: bold;
          transition: opacity 0.3s;
        }

        .btn-generate:hover:not(:disabled) {
          opacity: 0.9;
        }

        .btn-generate:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .quests-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .quest-card {
          padding: 15px;
          background: var(--bg-primary);
          border-radius: 8px;
          border: 1px solid var(--border-color);
          transition: all 0.3s;
        }

        .quest-card.completed {
          opacity: 0.6;
          background: var(--bg-secondary);
        }

        .quest-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }

        .quest-header h4 {
          margin: 0;
          font-size: 16px;
        }

        .difficulty {
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: bold;
        }

        .difficulty.easy {
          background: #4CAF50;
          color: white;
        }

        .difficulty.medium {
          background: #FF9800;
          color: white;
        }

        .difficulty.hard {
          background: #F44336;
          color: white;
        }

        .quest-description {
          margin: 8px 0;
          font-size: 14px;
          color: var(--text-secondary);
        }

        .quest-question {
          margin: 10px 0;
          padding: 12px;
          background: var(--bg-secondary);
          border-radius: 6px;
          border: 1px solid var(--border-color);
        }

        .question-text {
          font-size: 14px;
          font-weight: 600;
          margin-bottom: 10px;
        }

        .question-row {
          display: flex;
          gap: 8px;
        }

        .answer-input {
          flex: 1;
          padding: 8px 10px;
          border: 1px solid var(--border-color);
          border-radius: 4px;
          background: var(--bg-primary);
          color: var(--text-primary, inherit);
          font-size: 14px;
        }

        .answer-input:focus {
          outline: none;
          border-color: var(--primary-color);
        }

        .answer-feedback {
          margin-top: 8px;
          font-size: 13px;
          font-weight: 600;
        }

        .answer-feedback.correct {
          color: #4CAF50;
        }

        .answer-feedback.wrong {
          color: #F44336;
        }

        .quest-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 10px;
        }

        .quest-progress {
          font-size: 12px;
          color: var(--text-secondary);
          font-weight: bold;
        }

        .xp-reward {
          font-weight: bold;
          color: #4CAF50;
        }

        .btn-complete {
          padding: 6px 12px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 12px;
          font-weight: bold;
        }

        .btn-complete:hover:not(:disabled) {
          opacity: 0.9;
        }

        .btn-complete:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .completed-badge {
          color: #4CAF50;
          font-weight: bold;
        }

        .leaderboard-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .leaderboard-entry {
          display: flex;
          align-items: center;
          gap: 15px;
          padding: 12px;
          background: var(--bg-primary);
          border-radius: 6px;
          border-left: 4px solid var(--primary-color);
        }

        .rank {
          font-weight: bold;
          font-size: 16px;
          min-width: 40px;
        }

        .username {
          flex: 1;
          font-weight: 500;
        }

        .score {
          font-weight: bold;
          color: var(--primary-color);
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

export default GamificationPanel;
