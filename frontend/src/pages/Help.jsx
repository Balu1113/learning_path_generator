import { HelpCircle, Brain, Zap, Layers, ArrowRight, Lightbulb, Key, Rocket } from "lucide-react";

export default function Help() {
  return (
    <div className="page-container">
      <div className="page-header">
        <HelpCircle size={28} />
        <div>
          <h2>Help & Guide</h2>
          <p className="subtitle">Learn how to use the AI Learning Path Generator.</p>
        </div>
      </div>

      <div className="help-content">
        <section className="help-section">
          <h3><Lightbulb size={18} /> What is LearnPath?</h3>
          <p>
            LearnPath is an AI-powered tool that generates personalized, structured learning
            roadmaps for any skill or career goal. It uses Google Gemini LLM to create
            detailed roadmaps with real resources, time estimates, and project suggestions.
          </p>
        </section>

        <section className="help-section">
          <h3><Key size={18} /> Getting Started</h3>
          <div className="steps-grid">
            <div className="help-step">
              <span className="step-num">1</span>
              <div>
                <strong>Get a Gemini API Key</strong>
                <p>Visit <code>https://aistudio.google.com/apikey</code> and generate a free API key.</p>
              </div>
            </div>
            <div className="help-step">
              <span className="step-num">2</span>
              <div>
                <strong>Configure .env</strong>
                <p>Add your API key to the <code>.env</code> file in the project root:</p>
                <pre>GEMINI_API_KEY=your-key-here</pre>
              </div>
            </div>
            <div className="help-step">
              <span className="step-num">3</span>
              <div>
                <strong>Start the Server</strong>
                <p>Run the Django backend and React frontend.</p>
                <pre>python backend\manage.py runserver 0.0.0.0:8000</pre>
              </div>
            </div>
          </div>
        </section>

        <section className="help-section">
          <h3><Brain size={18} /> Agent Mode</h3>
          <p>
            The Agent Mode uses a <strong>ReAct (Reason + Act)</strong> framework. The AI
            thinks step-by-step, searches its memory for similar past roadmaps, generates
            your path, and saves it for future reference.
          </p>
          <div className="how-to-use">
            <h4>How to use:</h4>
            <ol>
              <li>Type your learning goal in the input field</li>
              <li>Be as specific as possible for better results</li>
              <li>Click <strong>"Generate Roadmap"</strong></li>
              <li>Watch the agent think through each step</li>
              <li>Get your personalized roadmap</li>
            </ol>
          </div>
          <div className="example-box">
            <h4>Example Goals:</h4>
            <ul>
              <li>"Become a Full Stack Web Developer in 6 months"</li>
              <li>"Learn Machine Learning from scratch, I know basic Python"</li>
              <li>"Get into cybersecurity, I have 2 hours per day"</li>
              <li>"Build a mobile app with React Native"</li>
              <li>"Switch from frontend to backend development"</li>
            </ul>
          </div>
        </section>

        <section className="help-section">
          <h3><Zap size={18} /> Quick Path Generator</h3>
          <p>
            A faster option that generates a roadmap directly without the agent workflow.
            Best for straightforward goals.
          </p>
          <div className="how-to-use">
            <h4>How to use:</h4>
            <ol>
              <li>Enter your learning goal</li>
              <li>Select your <strong>current level</strong> (beginner / intermediate / advanced)</li>
              <li>Adjust the <strong>hours per day</strong> slider</li>
              <li>Choose your <strong>preferred format</strong> (courses, books, videos, etc.)</li>
              <li>Click <strong>"Generate Path"</strong></li>
            </ol>
          </div>
        </section>

        <section className="help-section">
          <h3><Layers size={18} /> Domains</h3>
          <p>
            Browse the available learning domains. The LLM generates topics dynamically,
            so every roadmap is unique and up-to-date.
          </p>
          <div className="domains-list">
            <span className="domain-tag">Web Development</span>
            <span className="domain-tag">Data Science</span>
            <span className="domain-tag">Cloud & DevOps</span>
            <span className="domain-tag">Mobile Development</span>
            <span className="domain-tag">Cybersecurity</span>
            <span className="domain-tag">AI/ML Engineering</span>
            <span className="domain-tag">Blockchain</span>
          </div>
        </section>

        <section className="help-section">
          <h3><Rocket size={18} /> Tips for Best Results</h3>
          <div className="tips-grid">
            <div className="tip-card">
              <strong>Be Specific</strong>
              <p>Instead of "Learn programming", try "Learn Python for data analysis and automation"</p>
            </div>
            <div className="tip-card">
              <strong>Mention Your Level</strong>
              <p>Tell the AI what you already know so it can tailor the roadmap</p>
            </div>
            <div className="tip-card">
              <strong>Set Time Constraints</strong>
              <p>Mention how many hours per day you can dedicate for realistic timelines</p>
            </div>
            <div className="tip-card">
              <strong>Save Roadmaps</strong>
              <p>The agent mode automatically saves generated paths to memory for future reference</p>
            </div>
          </div>
        </section>

        <section className="help-section">
          <h3>Troubleshooting</h3>
          <div className="faq-list">
            <div className="faq-item">
              <strong>429 Quota Error</strong>
              <p>You've exceeded the Gemini free tier limit. Wait a minute and try again, or upgrade your plan.</p>
            </div>
            <div className="faq-item">
              <strong>API Key Error</strong>
              <p>Make sure your <code>GEMINI_API_KEY</code> is set correctly in the <code>.env</code> file and the server is restarted.</p>
            </div>
            <div className="faq-item">
              <strong>Port Already in Use</strong>
              <p>Kill the existing process: <code>netstat -ano | findstr :8000</code> then <code>taskkill /PID &lt;id&gt; /F</code></p>
            </div>
            <div className="faq-item">
              <strong>Empty Roadmap</strong>
              <p>The LLM might be rate-limited. Try again after a short wait.</p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
