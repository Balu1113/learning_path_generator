import React, { useState, useEffect } from 'react';
import { getCsrfToken } from '../api/client';

const VoiceTutor = ({ pathId, phaseIdx }) => {
  const [scenarios, setScenarios] = useState([]);
  const [activeTab, setActiveTab] = useState('scenarios');
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [session, setSession] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadScenarios();
    loadConversations();
  }, [pathId, phaseIdx]);

  const loadScenarios = async () => {
    try {
      const res = await fetch(`/api/voice/scenarios/${pathId}/${phaseIdx}`);
      const data = await res.json();
      setScenarios(data.scenarios || []);
    } catch (error) {
      console.error('Failed to load scenarios:', error);
    }
  };

  const loadConversations = async () => {
    try {
      const res = await fetch('/api/voice/conversations');
      const data = await res.json();
      setConversations(data.conversations || []);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const startSession = async (scenario) => {
    setLoading(true);
    try {
      const token = await getCsrfToken();
      const res = await fetch(`/api/voice/session/start/${pathId}/${phaseIdx}`, {
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
      console.error('Failed to start session:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="voice-tutor-container">
      <h2>AI Voice Tutor</h2>

      <div className="tutor-tabs">
        <button
          className={`tab ${activeTab === 'scenarios' ? 'active' : ''}`}
          onClick={() => setActiveTab('scenarios')}
        >
          Practice Scenarios
        </button>
        <button
          className={`tab ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          Chat with Tutor
        </button>
        <button
          className={`tab ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          History
        </button>
      </div>

      {activeTab === 'scenarios' && (
        <div className="scenarios-section">
          {session ? (
            <PracticeSession
              session={session}
              onBack={() => {
                setSession(null);
                loadScenarios();
              }}
            />
          ) : (
            <div className="scenarios-grid">
              {scenarios.map(scenario => (
                <div key={scenario.id} className="scenario-card">
                  <h3>{scenario.title}</h3>
                  <p>{scenario.description}</p>
                  <div className="scenario-meta">
                    <span className={`difficulty ${scenario.difficulty}`}>
                      {scenario.difficulty}
                    </span>
                  </div>
                  <button
                    className="btn-start"
                    onClick={() => startSession(scenario)}
                    disabled={loading}
                  >
                    Start Practice
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'chat' && (
        <TutorChat />
      )}

      {activeTab === 'history' && (
        <div className="history-section">
          <div className="conversations-list">
            {conversations.length === 0 ? (
              <div className="empty-state">No conversations yet</div>
            ) : (
              conversations.map(conv => (
                <div key={conv.id} className="conversation-item">
                  <div className="conv-topic">{conv.topic}</div>
                  <div className="conv-meta">
                    <span>{conv.message_count} messages</span>
                    <span>{new Date(conv.updated_at).toLocaleDateString()}</span>
                  </div>
                  <div className="conv-preview">{conv.last_message}</div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      <style jsx>{`
        .voice-tutor-container {
          padding: 20px;
          background: var(--bg-secondary);
          border-radius: 8px;
        }

        .voice-tutor-container h2 {
          margin-top: 0;
          color: var(--text-primary);
        }

        .tutor-tabs {
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

        .scenarios-section {
          min-height: 300px;
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
        }

        .scenario-card h3 {
          margin: 0 0 10px 0;
          color: var(--text-primary);
        }

        .scenario-card p {
          margin: 0 0 15px 0;
          color: var(--text-secondary);
          font-size: 14px;
          flex: 1;
        }

        .scenario-meta {
          margin-bottom: 15px;
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

        .history-section {
          min-height: 300px;
        }

        .conversations-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .conversation-item {
          padding: 15px;
          background: var(--bg-primary);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.3s;
        }

        .conversation-item:hover {
          border-color: var(--primary-color);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .conv-topic {
          font-weight: bold;
          margin-bottom: 8px;
          color: var(--text-primary);
        }

        .conv-meta {
          display: flex;
          gap: 15px;
          font-size: 12px;
          color: var(--text-secondary);
          margin-bottom: 8px;
        }

        .conv-preview {
          font-size: 12px;
          color: var(--text-secondary);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
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

const PracticeSession = ({ session, onBack }) => {
  const [transcript, setTranscript] = useState('');
  const [feedback, setFeedback] = useState(null);
  const [score, setScore] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [loading, setLoading] = useState(false);

  const submitResponse = async () => {
    if (!transcript.trim()) return;

    setLoading(true);
    try {
      const token = await getCsrfToken();
      const res = await fetch(`/api/voice/session/${session.session_id}/submit`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ transcript }),
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
        <h3>{session.topic}</h3>
        <span className="scenario-type">{session.scenario_type}</span>
      </div>

      <div className="session-prompt">
        <p>{session.initial_prompt}</p>
      </div>

      {!feedback ? (
        <div className="response-section">
          <div className="recording-controls">
            <button
              className={`btn-record ${isRecording ? 'recording' : ''}`}
              onClick={() => setIsRecording(!isRecording)}
            >
              {isRecording ? '🔴 Recording...' : '🎤 Start Recording'}
            </button>
          </div>

          <textarea
            value={transcript}
            onChange={e => setTranscript(e.target.value)}
            placeholder="Or type your response here..."
            rows="6"
            className="response-input"
          />

          <button
            className="btn-submit"
            onClick={submitResponse}
            disabled={!transcript.trim() || loading}
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
            <h4>Feedback</h4>
            <p>{feedback}</p>
          </div>

          <button className="btn-try-again" onClick={() => {
            setTranscript('');
            setFeedback(null);
            setScore(null);
          }}>
            Try Another Response
          </button>
        </div>
      )}

      <style jsx>{`
        .practice-session {
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

        .session-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }

        .session-header h3 {
          margin: 0;
          color: var(--text-primary);
        }

        .scenario-type {
          padding: 4px 8px;
          background: var(--primary-color);
          color: white;
          border-radius: 4px;
          font-size: 12px;
          font-weight: bold;
        }

        .session-prompt {
          padding: 15px;
          background: var(--bg-secondary);
          border-left: 4px solid var(--primary-color);
          border-radius: 4px;
          margin-bottom: 20px;
        }

        .session-prompt p {
          margin: 0;
          color: var(--text-primary);
        }

        .response-section {
          display: flex;
          flex-direction: column;
          gap: 15px;
        }

        .recording-controls {
          display: flex;
          gap: 10px;
        }

        .btn-record {
          padding: 12px 20px;
          background: #F44336;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: bold;
          font-size: 14px;
        }

        .btn-record.recording {
          animation: pulse 1s infinite;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
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

        .feedback-content h4 {
          margin-top: 0;
          margin-bottom: 10px;
        }

        .feedback-content p {
          margin: 0;
          line-height: 1.6;
          color: var(--text-primary);
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

const TutorChat = () => {
  const [conversations, setConversations] = useState([]);
  const [selectedConv, setSelectedConv] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const res = await fetch('/api/voice/conversations');
      const data = await res.json();
      setConversations(data.conversations || []);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const startConversation = async (topic) => {
    try {
      const res = await fetch(`/api/voice/chat?topic=${encodeURIComponent(topic)}`);
      const data = await res.json();
      setSelectedConv(data.conversation_id);
      setMessages(data.messages || []);
    } catch (error) {
      console.error('Failed to start conversation:', error);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || !selectedConv) return;

    const userMessage = input;
    setInput('');
    setMessages([...messages, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const token = await getCsrfToken();
      const res = await fetch(`/api/voice/chat/${selectedConv}/message`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ message: userMessage }),
      });

      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="tutor-chat">
      {!selectedConv ? (
        <div className="chat-start">
          <h3>Start a Conversation</h3>
          <div className="topic-buttons">
            {['Python Basics', 'Web Development', 'Data Science', 'General Questions'].map(topic => (
              <button
                key={topic}
                className="btn-topic"
                onClick={() => startConversation(topic)}
              >
                {topic}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="chat-window">
          <div className="messages">
            {messages.map((msg, idx) => (
              <div key={idx} className={`message ${msg.role}`}>
                <div className="message-content">{msg.content}</div>
              </div>
            ))}
            {loading && <div className="message assistant"><div className="typing">Tutor is typing...</div></div>}
          </div>

          <div className="chat-input">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyPress={e => e.key === 'Enter' && sendMessage()}
              placeholder="Ask a question..."
              disabled={loading}
            />
            <button onClick={sendMessage} disabled={!input.trim() || loading}>
              Send
            </button>
          </div>
        </div>
      )}

      <style jsx>{`
        .tutor-chat {
          min-height: 400px;
          background: var(--bg-primary);
          border-radius: 8px;
          padding: 20px;
        }

        .chat-start {
          text-align: center;
        }

        .chat-start h3 {
          margin-top: 0;
        }

        .topic-buttons {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 10px;
          margin-top: 20px;
        }

        .btn-topic {
          padding: 12px 15px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: bold;
        }

        .btn-topic:hover {
          opacity: 0.9;
        }

        .chat-window {
          display: flex;
          flex-direction: column;
          height: 500px;
        }

        .messages {
          flex: 1;
          overflow-y: auto;
          margin-bottom: 15px;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .message {
          display: flex;
          margin-bottom: 10px;
        }

        .message.user {
          justify-content: flex-end;
        }

        .message.assistant {
          justify-content: flex-start;
        }

        .message-content {
          max-width: 70%;
          padding: 12px 15px;
          border-radius: 8px;
          line-height: 1.5;
        }

        .message.user .message-content {
          background: var(--primary-color);
          color: white;
        }

        .message.assistant .message-content {
          background: var(--bg-secondary);
          color: var(--text-primary);
        }

        .typing {
          font-style: italic;
          color: var(--text-secondary);
        }

        .chat-input {
          display: flex;
          gap: 10px;
        }

        .chat-input input {
          flex: 1;
          padding: 10px 12px;
          border: 1px solid var(--border-color);
          border-radius: 4px;
          background: var(--bg-secondary);
          color: var(--text-primary);
        }

        .chat-input button {
          padding: 10px 20px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: bold;
        }

        .chat-input button:hover:not(:disabled) {
          opacity: 0.9;
        }

        .chat-input button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
};

export default VoiceTutor;
