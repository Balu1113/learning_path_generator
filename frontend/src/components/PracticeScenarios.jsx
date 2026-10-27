import React, { useState, useEffect } from 'react';
import { getCsrfToken } from '../api/client';

const PracticeScenarios = ({ pathId, phaseIdx }) => {
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [session, setSession] = useState(null);
  const [tips, setTips] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadScenarios();
    loadTips();
  }, [pathId, phaseIdx]);

  const loadScenarios = async () => {
    try {
      const res = await fetch(`/api/practice/scenarios/${pathId}/${phaseIdx}`);
      const data = await res.json();
      setScenarios(data.scenarios || []);
    } catch (error) {
      console.error('Failed to load scenarios:', error);
    }
  };

  const loadTips = async () => {
    try {
      const res = await fetch('/api/practice/tips');
      const data = await res.json();
      setTips(data.tips || {});
    } catch (error) {
      console.error('Failed to load tips:', error);
    }
  };

  const startScenario = async (scenario) => {
    setLoading(true);
    try {
      const token = await getCsrfToken();
      const res = await fetch(`/api/practice/start/${pathId}/${phaseIdx}`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          scenario_type: scenario.id,
          topic: scenario.title,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setSession(data);
        setSelectedScenario(scenario);
      }
    } catch (error) {
      console.error('Failed to start scenario:', error);
    } finally {
      setLoading(false);
    }
  };

  if (selectedScenario && session) {
    return (
      <PracticeSession
        session={session}
        scenario={selectedScenario}
        tips={tips?.[selectedScenario.id] || []}
        onBack={() => {
          setSession(null);
          setSelectedScenario(null);
        }}
      />
    );
  }

  return (
    <div className="practice-scenarios-container">
      <h2>🎯 Practice Scenarios</h2>
      <p className="subtitle">Improve your skills with AI-powered practice</p>

      <div className="scenarios-grid">
        {scenarios.map(scenario => (
          <div key={scenario.id} className="scenario-card">
            <div className="scenario-icon">{scenario.icon}</div>
            <h3>{scenario.title}</h3>
            <p className="description">{scenario.description}</p>
            <div className="scenario-meta">
              <span className={`difficulty ${scenario.difficulty}`}>
                {scenario.difficulty}
              </span>
              <span className="duration">⏱️ {scenario.duration_minutes}m</span>
            </div>
            <button
              className="btn-start"
              onClick={() => startScenario(scenario)}
              disabled={loading}
            >
              Start Practice
            </button>
          </div>
        ))}
      </div>

      <style jsx>{`
        .practice-scenarios-container {
          padding: 20px;
          background: var(--bg-secondary);
          border-radius: 8px;
        }

        .practice-scenarios-container h2 {
          margin-top: 0;
          color: var(--text-primary);
        }

        .subtitle {
          color: var(--text-secondary);
          margin-bottom: 20px;
        }

        .scenarios-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 15px;
        }

        .scenario-card {
          padding: 20px;
          background: var(--bg-primary);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          display: flex;
          flex-direction: column;
          transition: all 0.3s;
        }

        .scenario-card:hover {
          transform: translateY(-4px);
          box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
          border-color: var(--primary-color);
        }

        .scenario-icon {
          font-size: 40px;
          margin-bottom: 10px;
        }

        .scenario-card h3 {
          margin: 0 0 8px 0;
          color: var(--text-primary);
        }

        .description {
          margin: 0 0 12px 0;
          color: var(--text-secondary);
          font-size: 14px;
          flex: 1;
        }

        .scenario-meta {
          display: flex;
          gap: 10px;
          margin-bottom: 12px;
          font-size: 12px;
        }

        .difficulty {
          padding: 4px 8px;
          border-radius: 4px;
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

        .duration {
          color: var(--text-secondary);
        }

        .btn-start {
          padding: 10px 15px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: bold;
        }

        .btn-start:hover:not(:disabled) {
          opacity: 0.9;
        }

        .btn-start:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
};

const PracticeSession = ({ session, scenario, tips, onBack }) => {
  const [response, setResponse] = useState('');
  const [feedback, setFeedback] = useState(null);
  const [score, setScore] = useState(null);
  const [loading, setLoading] = useState(false);

  const submitResponse = async () => {
    if (!response.trim()) return;

    setLoading(true);
    try {
      const token = await getCsrfToken();
      const res = await fetch(`/api/practice/${session.conversation_id}/submit`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ response }),
      });

      if (res.ok) {
        const data = await res.json();
        setFeedback(data.feedback);
        setScore(data.score);
      }
    } catch (error) {
      console.error('Failed to submit response:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="practice-session">
      <button className="btn-back" onClick={onBack}>← Back</button>

      <div className="session-header">
        <h2>{scenario.title}</h2>
        <span className="topic">{session.topic}</span>
      </div>

      <div className="session-content">
        <div className="prompt-section">
          <h3>Prompt</h3>
          <p className="prompt">{session.initial_prompt}</p>
        </div>

        {tips.length > 0 && (
          <div className="tips-section">
            <h3>💡 Tips</h3>
            <ul className="tips-list">
              {tips.map((tip, idx) => (
                <li key={idx}>{tip}</li>
              ))}
            </ul>
          </div>
        )}

        {!feedback ? (
          <div className="response-section">
            <textarea
              value={response}
              onChange={e => setResponse(e.target.value)}
              placeholder="Type your response here..."
              rows="8"
              className="response-input"
            />

            <button
              className="btn-submit"
              onClick={submitResponse}
              disabled={!response.trim() || loading}
            >
              {loading ? 'Analyzing...' : 'Submit Response'}
            </button>
          </div>
        ) : (
          <div className="feedback-section">
            <div className="score-display">
              <div className="score-value">{score}/100</div>
              <div className="score-label">Your Score</div>
            </div>

            <div className="feedback-content">
              <h3>Feedback</h3>
              <p>{feedback}</p>
            </div>

            <button
              className="btn-try-again"
              onClick={() => {
                setResponse('');
                setFeedback(null);
                setScore(null);
              }}
            >
              Try Another Response
            </button>
          </div>
        )}
      </div>

      <style jsx>{`
        .practice-session {
          padding: 20px;
          background: var(--bg-secondary);
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

        .session-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
          padding-bottom: 15px;
          border-bottom: 2px solid var(--border-color);
        }

        .session-header h2 {
          margin: 0;
          color: var(--text-primary);
        }

        .topic {
          padding: 4px 8px;
          background: var(--primary-color);
          color: white;
          border-radius: 4px;
          font-size: 12px;
          font-weight: bold;
        }

        .session-content {
          background: var(--bg-primary);
          padding: 20px;
          border-radius: 8px;
        }

        .prompt-section {
          margin-bottom: 20px;
        }

        .prompt-section h3 {
          margin-top: 0;
          margin-bottom: 10px;
        }

        .prompt {
          padding: 15px;
          background: var(--bg-secondary);
          border-left: 4px solid var(--primary-color);
          border-radius: 4px;
          margin: 0;
        }

        .tips-section {
          margin-bottom: 20px;
          padding: 15px;
          background: #E8F5E9;
          border-radius: 4px;
        }

        .tips-section h3 {
          margin-top: 0;
          margin-bottom: 10px;
          color: #1B5E20;
        }

        .tips-list {
          margin: 0;
          padding-left: 20px;
        }

        .tips-list li {
          margin-bottom: 6px;
          color: #2E7D32;
        }

        .response-section {
          display: flex;
          flex-direction: column;
          gap: 15px;
        }

        .response-input {
          padding: 12px;
          border: 1px solid var(--border-color);
          border-radius: 4px;
          background: var(--bg-secondary);
          color: var(--text-primary);
          font-family: inherit;
          resize: vertical;
        }

        .btn-submit {
          padding: 12px 20px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: bold;
          font-size: 16px;
        }

        .btn-submit:hover:not(:disabled) {
          opacity: 0.9;
        }

        .btn-submit:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .feedback-section {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .score-display {
          text-align: center;
          padding: 30px;
          background: var(--bg-secondary);
          border-radius: 8px;
        }

        .score-value {
          font-size: 48px;
          font-weight: bold;
          color: var(--primary-color);
        }

        .score-label {
          font-size: 14px;
          color: var(--text-secondary);
          margin-top: 10px;
        }

        .feedback-content {
          padding: 15px;
          background: var(--bg-secondary);
          border-radius: 8px;
        }

        .feedback-content h3 {
          margin-top: 0;
          margin-bottom: 10px;
        }

        .feedback-content p {
          margin: 0;
          line-height: 1.6;
        }

        .btn-try-again {
          padding: 12px 20px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: bold;
        }

        .btn-try-again:hover {
          opacity: 0.9;
        }
      `}</style>
    </div>
  );
};

export default PracticeScenarios;
