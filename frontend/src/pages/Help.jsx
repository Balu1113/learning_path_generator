import { HelpCircle, Brain, Zap, Layers, ArrowRight, Lightbulb, Key, Rocket, BookOpen, Users, Award, Gamepad2, BarChart3, Code, ShoppingCart, Video, Mic, Compass, Target, Calendar, Flame } from "lucide-react";

export default function Help() {
  return (
    <div className="page-container">
      <div className="page-header">
        <HelpCircle size={28} />
        <div>
          <h2>Help & Guide</h2>
          <p className="subtitle">Complete guide to using the AI Learning Path Generator.</p>
        </div>
      </div>

      <div className="help-content">
        <section className="help-section">
          <h3><Lightbulb size={18} /> What is LearnPath?</h3>
          <p>
            LearnPath is an AI-powered platform that generates personalized, structured learning
            roadmaps, tracks skill mastery, enables collaborative learning, and builds evidence-based
            portfolios. It uses Google Gemini LLM with LangChain/LangGraph for intelligent path generation.
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
                <pre>python manage.py runserver</pre>
              </div>
            </div>
          </div>
        </section>

        <section className="help-section">
          <h3><Brain size={18} /> Agent Mode</h3>
          <p>
            The Agent Mode uses a <strong>ReAct (Reason + Act)</strong> framework. The AI
            thinks step-by-step, searches memory for similar past roadmaps, generates your path,
            and saves it for future reference.
          </p>
          <div className="how-to-use">
            <h4>How to use:</h4>
            <ol>
              <li>Type your learning goal in the input field</li>
              <li>Be as specific as possible (include goal, timeline, prior knowledge)</li>
              <li>Click <strong>"Generate Roadmap"</strong></li>
              <li>Watch the agent reason and build your path</li>
              <li>Review and start learning from your generated roadmap</li>
            </ol>
          </div>
          <div className="example-box">
            <h4>Example Goals:</h4>
            <ul>
              <li>"Become a Full Stack Web Developer in 6 months"</li>
              <li>"Learn Machine Learning from scratch, I know basic Python"</li>
              <li>"Get into cybersecurity, I have 2 hours per day"</li>
              <li>"Switch from frontend to backend development"</li>
            </ul>
          </div>
        </section>

        <section className="help-section">
          <h3><Zap size={18} /> Quick Path Generator</h3>
          <p>
            Generate a roadmap faster with explicit parameters. Great for quick starts.
          </p>
          <div className="how-to-use">
            <h4>How to use:</h4>
            <ol>
              <li>Enter your learning goal</li>
              <li>Select current level (beginner / intermediate / advanced)</li>
              <li>Set hours per day</li>
              <li>Choose preferred format/resources</li>
              <li>Click <strong>"Generate Path"</strong></li>
            </ol>
          </div>
        </section>

        <section className="help-section">
          <h3><BookOpen size={18} /> Study Workspace</h3>
          <p>
            The Study page is your learning hub with progress tracking, tests, projects, and more.
          </p>
          <div className="how-to-use">
            <h4>Key features:</h4>
            <ul>
              <li><strong>Phases & Topics</strong> - Complete topics in order with checkboxes</li>
              <li><strong>Phase Tests</strong> - Take assessments to validate mastery</li>
              <li><strong>Milestone Projects</strong> - Build projects with AI review</li>
              <li><strong>Code Challenges</strong> - Solve live coding challenges per phase</li>
              <li><strong>Study Notes</strong> - AI-generated notes at multiple levels</li>
              <li><strong>Flashcards & Spaced Repetition</strong> - Review with SM-2 algorithm</li>
              <li><strong>Chat with AI Tutor</strong> - Get help on topics</li>
              <li><strong>Pomodoro Timer</strong> - Stay focused with time-boxing</li>
            </ul>
          </div>
        </section>

        <section className="help-section">
          <h3><Users size={18} /> Groups & Collaboration</h3>
          <p>
            Learn together with study groups, shared deadlines, check-ins, and track member progress.
          </p>
        </section>

        <section className="help-section">
          <h3><Award size={18} /> Portfolio & Skill Passport</h3>
          <p>
            Build an evidence-based portfolio with validated skills, projects, tests, and badges.
            Share publicly with a custom profile or export as JSON.
          </p>
        </section>

        <section className="help-section">
          <h3><Target size={18} /> Job Target Mode</h3>
          <p>
            Analyze job descriptions, find skill gaps, and get tailored learning recommendations
            to match job requirements.
          </p>
        </section>

        <section className="help-section">
          <h3><Gamepad2 size={18} /> Gamification</h3>
          <p>
            Earn XP, level up, complete daily quests, join seasonal challenges, and climb leaderboards.
          </p>
        </section>

        <section className="help-section">
          <h3><BarChart3 size={18} /> Analytics</h3>
          <p>
            Track learning velocity, daily metrics, cohort comparisons, and get insights on your progress.
          </p>
        </section>

        <section className="help-section">
          <h3><Code size={18} /> Peer Review</h3>
          <p>
            Submit projects for peer review, give feedback to others, and build reputation in the community.
          </p>
        </section>

        <section className="help-section">
          <h3><ShoppingCart size={18} /> Marketplace</h3>
          <p>
            Browse curated learning paths, purchase premium paths, or create and sell your own custom paths.
          </p>
        </section>

        <section className="help-section">
          <h3><Video size={18} /> Videos & <Mic size={18} /> Voice Tutor</h3>
          <p>
            Access video learning resources with notes and transcript search. Practice with AI voice tutor
            for interviews and scenarios.
          </p>
        </section>

        <section className="help-section">
          <h3><Layers size={18} /> Domains</h3>
          <p>
            Browse available learning domains. The LLM generates topics dynamically for up-to-date content.
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
              <p>Mention hours per day for realistic timelines and scheduling</p>
            </div>
            <div className="tip-card">
              <strong>Stay Consistent</strong>
              <p>Use the Pomodoro timer, complete daily quests, and maintain your streak</p>
            </div>
            <div className="tip-card">
              <strong>Validate Skills</strong>
              <p>Take phase tests and complete projects to build your verified skill portfolio</p>
            </div>
            <div className="tip-card">
              <strong>Engage with Community</strong>
              <p>Join groups, give peer reviews, and share your progress</p>
            </div>
          </div>
        </section>

        <section className="help-section">
          <h3>Troubleshooting</h3>
          <div className="faq-list">
            <div className="faq-item">
              <strong>429 Quota Error</strong>
              <p>You've exceeded the Gemini free tier limit. Wait and try again, or upgrade your plan.</p>
            </div>
            <div className="faq-item">
              <strong>API Key Error</strong>
              <p>Make sure your <code>GEMINI_API_KEY</code> is set correctly in <code>.env</code> and restart the server.</p>
            </div>
            <div className="faq-item">
              <strong>Port Already in Use</strong>
              <p>Kill existing process on port 8000 or use a different port.</p>
            </div>
            <div className="faq-item">
              <strong>Empty Roadmap</strong>
              <p>Try rephrasing with more specific details and context.</p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
