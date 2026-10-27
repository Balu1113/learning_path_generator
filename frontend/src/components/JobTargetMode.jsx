import React, { useState } from 'react';
import { getCsrfToken } from '../api/client';

const JobTargetMode = () => {
  const [activeTab, setActiveTab] = useState('analyze');
  const [jobTitle, setJobTitle] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [gaps, setGaps] = useState(null);
  const [paths, setPaths] = useState(null);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyzeJob = async () => {
    if (!jobDescription.trim()) return;

    setLoading(true);
    try {
      const token = await getCsrfToken();
      const res = await fetch('/api/job-target/analyze', {
        method: 'POST',
        headers: {
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          job_title: jobTitle,
          job_description: jobDescription,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setAnalysis(data);
        findGaps(data.skills);
        getInsights();
      }
    } catch (error) {
      console.error('Failed to analyze job:', error);
    } finally {
      setLoading(false);
    }
  };

  const findGaps = async (skills) => {
    try {
      const token = await getCsrfToken();
      const res = await fetch('/api/job-target/gaps', {
        method: 'POST',
        headers: {
          'X-CSRFToken': token,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          required_skills: [
            ...skills.technical_skills,
            ...skills.domain_skills,
            ...skills.soft_skills,
          ],
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setGaps(data);
      }
    } catch (error) {
      console.error('Failed to find gaps:', error);
    }
  };

  const getInsights = async () => {
    try {
      const res = await fetch(`/api/job-target/insights?job_title=${encodeURIComponent(jobTitle)}`);
      if (res.ok) {
        const data = await res.json();
        setInsights(data);
      }
    } catch (error) {
      console.error('Failed to get insights:', error);
    }
  };

  const generatePath = async () => {
    if (!gaps) return;

    setLoading(true);
    try {
      const res = await fetch(
        `/api/job-target/paths?job_title=${encodeURIComponent(jobTitle)}&gaps=${gaps.gaps.map(g => g.skill).join(',')}`
      );

      if (res.ok) {
        const data = await res.json();
        setPaths(data);
      }
    } catch (error) {
      console.error('Failed to generate path:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="job-target-container">
      <h1>🎯 Job Target Mode</h1>
      <p className="subtitle">Analyze job descriptions and create personalized learning paths</p>

      <div className="job-target-tabs">
        <button
          className={`tab ${activeTab === 'analyze' ? 'active' : ''}`}
          onClick={() => setActiveTab('analyze')}
        >
          Analyze Job
        </button>
        <button
          className={`tab ${activeTab === 'gaps' ? 'active' : ''}`}
          onClick={() => setActiveTab('gaps')}
          disabled={!analysis}
        >
          Skill Gaps
        </button>
        <button
          className={`tab ${activeTab === 'path' ? 'active' : ''}`}
          onClick={() => setActiveTab('path')}
          disabled={!gaps}
        >
          Learning Path
        </button>
        <button
          className={`tab ${activeTab === 'insights' ? 'active' : ''}`}
          onClick={() => setActiveTab('insights')}
          disabled={!insights}
        >
          Market Insights
        </button>
      </div>

      {activeTab === 'analyze' && (
        <div className="analyze-section">
          <div className="input-group">
            <label>Job Title</label>
            <input
              type="text"
              value={jobTitle}
              onChange={e => setJobTitle(e.target.value)}
              placeholder="e.g., Senior Full Stack Developer"
            />
          </div>

          <div className="input-group">
            <label>Job Description</label>
            <textarea
              value={jobDescription}
              onChange={e => setJobDescription(e.target.value)}
              placeholder="Paste the full job description here..."
              rows="10"
            />
          </div>

          <button
            className="btn-analyze"
            onClick={analyzeJob}
            disabled={!jobDescription.trim() || loading}
          >
            {loading ? 'Analyzing...' : 'Analyze Job Description'}
          </button>

          {analysis && (
            <div className="analysis-result">
              <h3>Analysis Complete</h3>
              <p>{analysis.skills.summary}</p>

              <div className="skills-breakdown">
                {analysis.skills.technical_skills && analysis.skills.technical_skills.length > 0 && (
                  <div className="skill-category">
                    <h4>Technical Skills</h4>
                    <div className="skills-list">
                      {analysis.skills.technical_skills.map((skill, idx) => (
                        <div key={idx} className="skill-tag">
                          {skill.name}
                          <span className="level">{skill.level}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {analysis.skills.domain_skills && analysis.skills.domain_skills.length > 0 && (
                  <div className="skill-category">
                    <h4>Domain Skills</h4>
                    <div className="skills-list">
                      {analysis.skills.domain_skills.map((skill, idx) => (
                        <div key={idx} className="skill-tag">
                          {skill.name}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {analysis.skills.soft_skills && analysis.skills.soft_skills.length > 0 && (
                  <div className="skill-category">
                    <h4>Soft Skills</h4>
                    <div className="skills-list">
                      {analysis.skills.soft_skills.map((skill, idx) => (
                        <div key={idx} className="skill-tag soft">
                          {skill.name}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'gaps' && gaps && (
        <div className="gaps-section">
          <div className="gap-score">
            <div className="score-circle">
              <div className="score-value">{gaps.gap_score}%</div>
              <div className="score-label">Gap Score</div>
            </div>
            <div className="gap-stats">
              <div className="stat">
                <span className="label">Total Skills Required:</span>
                <span className="value">{gaps.total_skills_required}</span>
              </div>
              <div className="stat">
                <span className="label">Skills Matched:</span>
                <span className="value">{gaps.skills_matched}</span>
              </div>
              <div className="stat">
                <span className="label">Skill Gaps:</span>
                <span className="value">{gaps.skill_gaps}</span>
              </div>
            </div>
          </div>

          <div className="recommendation-box">
            <h3>Recommendation</h3>
            <p>{gaps.recommendation}</p>
          </div>

          {gaps.gaps.length > 0 && (
            <div className="gaps-list">
              <h3>Skills to Develop</h3>
              {gaps.gaps.map((gap, idx) => (
                <div key={idx} className="gap-item">
                  <div className="gap-skill">{gap.skill}</div>
                  <div className="gap-level">Required: {gap.required_level}</div>
                  <div className={`gap-importance ${gap.importance}`}>
                    {gap.importance}
                  </div>
                </div>
              ))}
            </div>
          )}

          {gaps.matched_skills.length > 0 && (
            <div className="matched-list">
              <h3>Skills You Have</h3>
              {gaps.matched_skills.map((skill, idx) => (
                <div key={idx} className="matched-item">
                  <div className="matched-skill">✓ {skill.skill}</div>
                  <div className="matched-level">Your: {skill.user_level}</div>
                </div>
              ))}
            </div>
          )}

          <button className="btn-generate-path" onClick={generatePath}>
            Generate Learning Path
          </button>
        </div>
      )}

      {activeTab === 'path' && paths && (
        <div className="path-section">
          <h2>{paths.job_title} - Learning Path</h2>
          <p className="duration">Total Duration: {paths.total_duration_weeks} weeks</p>

          <div className="phases-list">
            {paths.phases.map((phase, idx) => (
              <div key={idx} className="phase-card">
                <div className="phase-header">
                  <h3>Phase {phase.phase}: {phase.title}</h3>
                  <span className="duration">{phase.duration_weeks} weeks</span>
                </div>

                <div className="phase-content">
                  <div className="section">
                    <h4>Topics</h4>
                    <ul>
                      {phase.topics.map((topic, i) => (
                        <li key={i}>{topic}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="section">
                    <h4>Resources</h4>
                    <div className="resources">
                      {phase.resources.map((resource, i) => (
                        <span key={i} className="resource-tag">{resource}</span>
                      ))}
                    </div>
                  </div>

                  {phase.projects && phase.projects.length > 0 && (
                    <div className="section">
                      <h4>Projects</h4>
                      <ul>
                        {phase.projects.map((project, i) => (
                          <li key={i}>{project}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="section">
                    <h4>Assessment</h4>
                    <p>{phase.assessment}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {paths.success_criteria && (
            <div className="success-criteria">
              <h3>Success Criteria</h3>
              <p>{paths.success_criteria}</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'insights' && insights && (
        <div className="insights-section">
          <h2>{insights.job_title} - Market Insights</h2>

          <div className="insights-grid">
            <div className="insight-card">
              <h3>💰 Salary Range</h3>
              <div className="salary">
                ${insights.salary_range.min.toLocaleString()} - ${insights.salary_range.max.toLocaleString()}
                <span className="currency">{insights.salary_range.currency}</span>
              </div>
            </div>

            <div className="insight-card">
              <h3>📈 Market Demand</h3>
              <div className={`demand ${insights.market_demand}`}>
                {insights.market_demand.toUpperCase()}
              </div>
            </div>
          </div>

          {insights.top_companies && (
            <div className="insight-section">
              <h3>🏢 Top Companies Hiring</h3>
              <div className="companies-list">
                {insights.top_companies.map((company, idx) => (
                  <div key={idx} className="company-tag">{company}</div>
                ))}
              </div>
            </div>
          )}

          {insights.key_skills && (
            <div className="insight-section">
              <h3>🔑 Key Skills in Demand</h3>
              <div className="skills-list">
                {insights.key_skills.map((skill, idx) => (
                  <div key={idx} className="skill-tag">{skill}</div>
                ))}
              </div>
            </div>
          )}

          {insights.common_questions && (
            <div className="insight-section">
              <h3>❓ Common Interview Questions</h3>
              <ol className="questions-list">
                {insights.common_questions.map((question, idx) => (
                  <li key={idx}>{question}</li>
                ))}
              </ol>
            </div>
          )}

          {insights.industry_trends && (
            <div className="insight-section">
              <h3>🌍 Industry Trends</h3>
              <p>{insights.industry_trends}</p>
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .job-target-container {
          padding: 20px;
          background: var(--bg-secondary);
          border-radius: 8px;
        }

        .job-target-container h1 {
          margin-top: 0;
          color: var(--text-primary);
        }

        .subtitle {
          color: var(--text-secondary);
          margin-bottom: 20px;
        }

        .job-target-tabs {
          display: flex;
          gap: 10px;
          margin-bottom: 20px;
          border-bottom: 2px solid var(--border-color);
          flex-wrap: wrap;
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

        .tab:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .analyze-section {
          background: var(--bg-primary);
          padding: 20px;
          border-radius: 8px;
        }

        .input-group {
          margin-bottom: 15px;
        }

        .input-group label {
          display: block;
          margin-bottom: 8px;
          font-weight: bold;
          color: var(--text-primary);
        }

        .input-group input,
        .input-group textarea {
          width: 100%;
          padding: 10px;
          border: 1px solid var(--border-color);
          border-radius: 4px;
          background: var(--bg-secondary);
          color: var(--text-primary);
          font-family: inherit;
        }

        .btn-analyze {
          padding: 12px 24px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: bold;
          font-size: 16px;
        }

        .btn-analyze:hover:not(:disabled) {
          opacity: 0.9;
        }

        .btn-analyze:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .analysis-result {
          margin-top: 20px;
          padding: 15px;
          background: var(--bg-secondary);
          border-radius: 8px;
        }

        .skills-breakdown {
          margin-top: 15px;
        }

        .skill-category {
          margin-bottom: 15px;
        }

        .skill-category h4 {
          margin: 0 0 10px 0;
          color: var(--text-primary);
        }

        .skills-list {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .skill-tag {
          padding: 6px 12px;
          background: var(--primary-color);
          color: white;
          border-radius: 20px;
          font-size: 12px;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .skill-tag.soft {
          background: #9C27B0;
        }

        .skill-tag .level {
          font-size: 10px;
          opacity: 0.8;
        }

        .gap-score {
          display: flex;
          gap: 30px;
          align-items: center;
          margin-bottom: 20px;
          padding: 20px;
          background: var(--bg-primary);
          border-radius: 8px;
        }

        .score-circle {
          width: 120px;
          height: 120px;
          border-radius: 50%;
          background: linear-gradient(135deg, var(--primary-color), #64B5F6);
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          color: white;
        }

        .score-value {
          font-size: 32px;
          font-weight: bold;
        }

        .score-label {
          font-size: 12px;
        }

        .gap-stats {
          flex: 1;
        }

        .stat {
          display: flex;
          justify-content: space-between;
          margin-bottom: 10px;
          padding: 8px 0;
          border-bottom: 1px solid var(--border-color);
        }

        .stat .label {
          color: var(--text-secondary);
        }

        .stat .value {
          font-weight: bold;
          color: var(--primary-color);
        }

        .recommendation-box {
          padding: 15px;
          background: #E8F5E9;
          border-left: 4px solid #4CAF50;
          border-radius: 4px;
          margin-bottom: 20px;
        }

        .recommendation-box h3 {
          margin-top: 0;
          color: #1B5E20;
        }

        .gaps-list,
        .matched-list {
          margin-bottom: 20px;
        }

        .gap-item,
        .matched-item {
          padding: 12px;
          background: var(--bg-primary);
          border: 1px solid var(--border-color);
          border-radius: 6px;
          margin-bottom: 8px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .gap-importance {
          padding: 2px 8px;
          border-radius: 3px;
          font-size: 11px;
          font-weight: bold;
        }

        .gap-importance.high {
          background: #F44336;
          color: white;
        }

        .gap-importance.medium {
          background: #FF9800;
          color: white;
        }

        .gap-importance.low {
          background: #4CAF50;
          color: white;
        }

        .btn-generate-path {
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

        .phases-list {
          display: flex;
          flex-direction: column;
          gap: 15px;
        }

        .phase-card {
          padding: 15px;
          background: var(--bg-primary);
          border: 1px solid var(--border-color);
          border-radius: 8px;
        }

        .phase-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 15px;
          padding-bottom: 10px;
          border-bottom: 2px solid var(--border-color);
        }

        .phase-header h3 {
          margin: 0;
        }

        .duration {
          background: var(--primary-color);
          color: white;
          padding: 4px 8px;
          border-radius: 3px;
          font-size: 12px;
        }

        .phase-content {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 15px;
        }

        .section h4 {
          margin-top: 0;
          margin-bottom: 8px;
        }

        .section ul {
          margin: 0;
          padding-left: 20px;
        }

        .section li {
          margin-bottom: 4px;
        }

        .resources {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }

        .resource-tag {
          padding: 4px 8px;
          background: var(--border-color);
          border-radius: 3px;
          font-size: 11px;
        }

        .success-criteria {
          padding: 15px;
          background: #E3F2FD;
          border-left: 4px solid var(--primary-color);
          border-radius: 4px;
          margin-top: 20px;
        }

        .insights-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 15px;
          margin-bottom: 20px;
        }

        .insight-card {
          padding: 15px;
          background: var(--bg-primary);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          text-align: center;
        }

        .insight-card h3 {
          margin-top: 0;
          margin-bottom: 10px;
        }

        .salary {
          font-size: 24px;
          font-weight: bold;
          color: var(--primary-color);
        }

        .currency {
          font-size: 12px;
          display: block;
          color: var(--text-secondary);
        }

        .demand {
          font-size: 18px;
          font-weight: bold;
          padding: 10px;
          border-radius: 4px;
        }

        .demand.high {
          background: #4CAF50;
          color: white;
        }

        .demand.medium {
          background: #FF9800;
          color: white;
        }

        .demand.low {
          background: #F44336;
          color: white;
        }

        .insight-section {
          margin-bottom: 20px;
          padding: 15px;
          background: var(--bg-primary);
          border-radius: 8px;
        }

        .companies-list,
        .skills-list {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .company-tag {
          padding: 6px 12px;
          background: var(--border-color);
          border-radius: 4px;
          font-size: 12px;
        }

        .questions-list {
          margin: 0;
          padding-left: 20px;
        }

        .questions-list li {
          margin-bottom: 8px;
        }

        @media (max-width: 768px) {
          .gap-score {
            flex-direction: column;
          }

          .phase-content {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
};

export default JobTargetMode;
