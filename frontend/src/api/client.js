const API_BASE = "/api";
let csrfToken = null;

export async function getCsrfToken() {
  const res = await fetch(`${API_BASE}/auth/csrf`);
  const data = await res.json();
  csrfToken = data.csrfToken;
  return csrfToken;
}

async function jsonFetch(url, options = {}) {
  if (options.method && options.method !== "GET") {
    const token = await getCsrfToken();
    options.headers = options.headers || {};
    options.headers["X-CSRFToken"] = token;
    options.credentials = "include";
  }
  const res = await fetch(url, options);
  return res.json();
}

export async function agentGenerate(goal) {
  return jsonFetch(`${API_BASE}/agent/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ goal }),
  });
}

export async function pathGenerate(body) {
  return jsonFetch(`${API_BASE}/path/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function pathStructured(body) {
  return jsonFetch(`${API_BASE}/path/structured`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function pathStream(body, onChunk) {
  const res = await fetch(`${API_BASE}/path/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) {
    throw new Error("Stream failed");
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let full = "";
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop();
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data: ")) continue;
      const evt = JSON.parse(line.slice(6));
      if (evt.error) throw new Error(evt.error);
      if (typeof evt.chunk === "string" && evt.chunk) {
        full += evt.chunk;
        onChunk(full);
      }
    }
  }
  return full;
}

export async function pathStreamSave(body) {
  return jsonFetch(`${API_BASE}/path/stream/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function getDomains() {
  return jsonFetch(`${API_BASE}/domains`);
}

export async function getDomainTopics(domain) {
  return jsonFetch(`${API_BASE}/domains/${domain}`);
}

export async function searchResources({ query = "", domain = "", difficulty = "any" } = {}) {
  const params = new URLSearchParams({ query, domain, difficulty });
  return jsonFetch(`${API_BASE}/resources/search?${params.toString()}`);
}

export async function getPathHistory() {
  return jsonFetch(`${API_BASE}/paths/history`);
}

export async function deletePath(id) {
  return jsonFetch(`${API_BASE}/paths/${id}/delete`, { method: "DELETE" });
}

export async function chatWithPath(id, message, history) {
  return jsonFetch(`${API_BASE}/paths/${id}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
}

export async function getProgress(id) {
  return jsonFetch(`${API_BASE}/paths/${id}/progress`);
}

export async function saveProgress(id, item_key, done) {
  return jsonFetch(`${API_BASE}/paths/${id}/progress/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item_key, done }),
  });
}

export async function getPhases(id) {
  return jsonFetch(`${API_BASE}/paths/${id}/phases`);
}

export async function getPathWorkspace(id) {
  return jsonFetch(`${API_BASE}/paths/${id}/workspace`);
}

export async function sendFeedback(id, value) {
  return jsonFetch(`${API_BASE}/paths/${id}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ value }),
  });
}

export async function placementAdaptiveStart(goal) {
  return jsonFetch(`${API_BASE}/placement/adaptive/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ goal }),
  });
}

export async function placementAdaptiveAnswer(session_id, question_id, answer_index) {
  return jsonFetch(`${API_BASE}/placement/adaptive/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id, question_id, answer_index }),
  });
}

export async function placementStart(goal) {
  return jsonFetch(`${API_BASE}/placement/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ goal }),
  });
}

export async function placementSubmit(quiz_id, answers) {
  return jsonFetch(`${API_BASE}/placement/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ quiz_id, answers }),
  });
}

export async function phaseTestStart(pathId, phaseIdx, body) {
  return jsonFetch(`${API_BASE}/paths/${pathId}/phases/${phaseIdx}/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function phaseTestSubmit(quiz_id, answers) {
  return jsonFetch(`${API_BASE}/tests/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ quiz_id, answers }),
  });
}

export async function getStats() {
  return jsonFetch(`${API_BASE}/stats`);
}

export async function registerUser(username, password) {
  csrfToken = null;
  return jsonFetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

export async function loginUser(username, password) {
  csrfToken = null;
  return jsonFetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

export async function logoutUser() {
  csrfToken = null;
  return jsonFetch(`${API_BASE}/auth/logout`, { method: "POST" });
}

export async function fetchMe() {
  return jsonFetch(`${API_BASE}/auth/me`);
}

export function icsUrl(id) {
  return `${API_BASE}/paths/${id}/ics`;
}

export function scheduleUrl(id, params = {}) {
  const qs = new URLSearchParams(params).toString();
  return `${API_BASE}/paths/${id}/schedule.ics${qs ? `?${qs}` : ""}`;
}

export function getSchedule(id, params = {}) {
  const qs = new URLSearchParams(params).toString();
  return jsonFetch(`${API_BASE}/paths/${id}/schedule${qs ? `?${qs}` : ""}`);
}

export function getFlashcards(id) {
  return jsonFetch(`${API_BASE}/paths/${id}/flashcards`);
}

export function generateFlashcards(id, body) {
  return jsonFetch(`${API_BASE}/paths/${id}/flashcards/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getDueFlashcards(limit = 50) {
  return jsonFetch(`${API_BASE}/flashcards/due?limit=${limit}`);
}

export function reviewFlashcard(cardId, rating) {
  return jsonFetch(`${API_BASE}/flashcards/${cardId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rating }),
  });
}

export function deleteFlashcard(cardId) {
  return jsonFetch(`${API_BASE}/flashcards/${cardId}/delete`, { method: "DELETE" });
}

export function generateStudyNotes(id, body) {
  return jsonFetch(`${API_BASE}/paths/${id}/study-notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getStreak(days = 182) {
  return jsonFetch(`${API_BASE}/streak?days=${days}`);
}

export function getBadges() {
  return jsonFetch(`${API_BASE}/badges`);
}

export function socraticChat(id, message, history) {
  return jsonFetch(`${API_BASE}/paths/${id}/socratic`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
}

export function regeneratePath(id) {
  return jsonFetch(`${API_BASE}/paths/${id}/regenerate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
}

export function ankiUrl(id) {
  return `${API_BASE}/paths/${id}/export/anki`;
}

export function notionUrl(id) {
  return `${API_BASE}/paths/${id}/export/notion`;
}

export function logFocus(body) {
  return jsonFetch(`${API_BASE}/focus/log`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getFocusSummary(pathId) {
  const qs = pathId ? `?path_id=${encodeURIComponent(pathId)}` : "";
  return jsonFetch(`${API_BASE}/focus/summary${qs}`);
}

export function getDeadlineAlerts() {
  return jsonFetch(`${API_BASE}/deadlines/alerts`);
}

export function getPathDifficulty(id) {
  return jsonFetch(`${API_BASE}/paths/${id}/difficulty`);
}

export function getPathRecommendation(id) {
  return jsonFetch(`${API_BASE}/paths/${id}/recommendation`);
}

export function retunePhase(id, body) {
  return jsonFetch(`${API_BASE}/paths/${id}/retune`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getShare(id) {
  return jsonFetch(`${API_BASE}/paths/${id}/share`);
}

export function createShare(id) {
  return jsonFetch(`${API_BASE}/paths/${id}/share`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
}

export function revokeShare(id) {
  return jsonFetch(`${API_BASE}/paths/${id}/share`, { method: "DELETE" });
}

export function getSharedPath(slug) {
  return jsonFetch(`${API_BASE}/share/${encodeURIComponent(slug)}`);
}

export function getGallery() {
  return jsonFetch(`${API_BASE}/gallery`);
}

export function getGroups() {
  return jsonFetch(`${API_BASE}/groups`);
}

export function createGroup(name) {
  return jsonFetch(`${API_BASE}/groups/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export function joinGroup(code) {
  return jsonFetch(`${API_BASE}/groups/join`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
}

export function getGroup(id) {
  return jsonFetch(`${API_BASE}/groups/${id}`);
}

export function setGroupPath(id, pathId) {
  return jsonFetch(`${API_BASE}/groups/${id}/path`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path_id: pathId }),
  });
}

export function leaveGroup(id) {
  return jsonFetch(`${API_BASE}/groups/${id}/leave`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
}

export function getProjects(id) {
  return jsonFetch(`${API_BASE}/paths/${id}/projects`);
}

export function generateProject(id, body) {
  return jsonFetch(`${API_BASE}/paths/${id}/projects/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getProject(id, phaseIdx) {
  return jsonFetch(`${API_BASE}/paths/${id}/projects/${phaseIdx}`);
}

export function submitProject(id, phaseIdx, body) {
  return jsonFetch(`${API_BASE}/paths/${id}/projects/${phaseIdx}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function reviewProject(id, phaseIdx) {
  return jsonFetch(`${API_BASE}/paths/${id}/projects/${phaseIdx}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
}

export function extractSkills(id) {
  return jsonFetch(`${API_BASE}/paths/${id}/skills/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
}

export function getSkillMatrix(id) {
  return jsonFetch(`${API_BASE}/paths/${id}/skills/matrix`);
}

export function getPortfolio() {
  return jsonFetch(`${API_BASE}/portfolio`);
}

export function getPublicPortfolio(username) {
  return jsonFetch(`${API_BASE}/portfolio/${encodeURIComponent(username)}`);
}

export function exportPortfolio() {
  return fetch(`${API_BASE}/portfolio/export`).then((r) => r.blob());
}

export function updatePortfolioPrivacy(settings) {
  return jsonFetch(`${API_BASE}/portfolio/privacy`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
}

export function analyzeJobTarget(jobDescription) {
  return jsonFetch(`${API_BASE}/job-target`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_description: jobDescription }),
  });
}

export function practiceTurn(pathId, scenario, message, history = []) {
  return jsonFetch(`${API_BASE}/paths/${pathId}/practice`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario, message, history }),
  });
}

export function setGroupDeadline(groupId, title, dueDate, description = "") {
  return jsonFetch(`${API_BASE}/groups/${groupId}/deadline`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, due_date: dueDate, description }),
  });
}

export function postGroupCheckin(groupId, message) {
  return jsonFetch(`${API_BASE}/groups/${groupId}/checkin`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
}

export function getGroupCheckins(groupId, limit = 20) {
  return jsonFetch(`${API_BASE}/groups/${groupId}/checkins?limit=${limit}`);
}

export function getChallenges(pathId, phaseIdx) {
  return jsonFetch(`${API_BASE}/paths/${pathId}/phases/${phaseIdx}/challenges`);
}

export function getChallenge(challengeId) {
  return jsonFetch(`${API_BASE}/challenges/${challengeId}`);
}

export function runChallenge(challengeId, code) {
  return jsonFetch(`${API_BASE}/challenges/${challengeId}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
}

export function submitChallenge(challengeId) {
  return jsonFetch(`${API_BASE}/challenges/${challengeId}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
}

export function getLeaderboard(pathId, phaseIdx) {
  return jsonFetch(`${API_BASE}/paths/${pathId}/phases/${phaseIdx}/leaderboard`);
}

export function generateCodeChallenges(pathId, phaseIdx, body) {
  return jsonFetch(`${API_BASE}/paths/${pathId}/phases/${phaseIdx}/challenges/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// Gamification APIs
export function getUserLevel() {
  return jsonFetch(`${API_BASE}/gamification/level`);
}

export function getXpHistory() {
  return jsonFetch(`${API_BASE}/gamification/xp-history`);
}

export function getDailyQuests() {
  return jsonFetch(`${API_BASE}/gamification/quests`);
}

export function generateDailyQuests(body = {}) {
  return jsonFetch(`${API_BASE}/gamification/quests/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function completeQuest(questId) {
  return jsonFetch(`${API_BASE}/gamification/quests/${questId}/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
}

export function getSeasonalChallenges() {
  return jsonFetch(`${API_BASE}/gamification/challenges`);
}

export function getGamificationLeaderboard() {
  return jsonFetch(`${API_BASE}/gamification/leaderboard`);
}

export function getLearningStreak() {
  return jsonFetch(`${API_BASE}/gamification/streak`);
}

// Analytics APIs
export function getAnalyticsDashboard(pathId) {
  return jsonFetch(`${API_BASE}/analytics/dashboard/${pathId}`);
}

export function getDailyMetrics(pathId) {
  return jsonFetch(`${API_BASE}/analytics/daily/${pathId}`);
}

export function getLearningVelocity(pathId) {
  return jsonFetch(`${API_BASE}/analytics/velocity/${pathId}`);
}

export function getCohortComparison(pathId) {
  return jsonFetch(`${API_BASE}/analytics/cohort/${pathId}`);
}

// Peer Review APIs
export function getPendingReviews() {
  return jsonFetch(`${API_BASE}/reviews/pending`);
}

export function createReview(projectId, body) {
  return jsonFetch(`${API_BASE}/reviews/create/${projectId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getReviewDetail(reviewId) {
  return jsonFetch(`${API_BASE}/reviews/${reviewId}`);
}

export function addReviewComment(reviewId, body) {
  return jsonFetch(`${API_BASE}/reviews/${reviewId}/comment`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function submitReview(reviewId, body) {
  return jsonFetch(`${API_BASE}/reviews/${reviewId}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getUserReputation() {
  return jsonFetch(`${API_BASE}/reviews/reputation`);
}

export function getMyReviews() {
  return jsonFetch(`${API_BASE}/reviews/my-reviews`);
}

// Skill Graph APIs
export function getSkillGraph(pathId) {
  return jsonFetch(`${API_BASE}/skills/graph/${pathId}`);
}

export function getPhaseBlockers(pathId) {
  return jsonFetch(`${API_BASE}/skills/blockers/${pathId}`);
}

export function getCriticalPath(pathId) {
  return jsonFetch(`${API_BASE}/skills/critical-path/${pathId}`);
}

export function getSkillMasteryStatus() {
  return jsonFetch(`${API_BASE}/skills/mastery`);
}

export function getSkillPrerequisites(skillId) {
  return jsonFetch(`${API_BASE}/skills/${skillId}/prerequisites`);
}

export function getSkillUnlocks(skillId) {
  return jsonFetch(`${API_BASE}/skills/${skillId}/unlocks`);
}

// Marketplace APIs
export function browseMarketplace(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return jsonFetch(`${API_BASE}/marketplace/browse${qs ? `?${qs}` : ""}`);
}

export function getFeaturedPaths() {
  return jsonFetch(`${API_BASE}/marketplace/featured`);
}

export function getMarketplacePathDetail(pathId) {
  return jsonFetch(`${API_BASE}/marketplace/paths/${pathId}`);
}

export function purchasePath(pathId) {
  return jsonFetch(`${API_BASE}/marketplace/paths/${pathId}/purchase`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
}

export function reviewMarketplacePath(pathId, body) {
  return jsonFetch(`${API_BASE}/marketplace/paths/${pathId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function createCustomPath(body) {
  return jsonFetch(`${API_BASE}/marketplace/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function updateCustomPath(pathId, body) {
  return jsonFetch(`${API_BASE}/marketplace/paths/${pathId}/update`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getMyPurchases() {
  return jsonFetch(`${API_BASE}/marketplace/my-purchases`);
}

export function getMyCreatedPaths() {
  return jsonFetch(`${API_BASE}/marketplace/my-paths`);
}

// Video APIs
export function getVideoDetail(videoId) {
  return jsonFetch(`${API_BASE}/videos/${videoId}`);
}

export function updateVideoProgress(videoId, body) {
  return jsonFetch(`${API_BASE}/videos/${videoId}/progress`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function addVideoNote(videoId, body) {
  return jsonFetch(`${API_BASE}/videos/${videoId}/note`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function searchTranscript(videoId, query) {
  return jsonFetch(`${API_BASE}/videos/${videoId}/search?q=${encodeURIComponent(query)}`);
}

export function getMyVideoProgress() {
  return jsonFetch(`${API_BASE}/videos/my-progress`);
}

export function createVideoResource(body) {
  return jsonFetch(`${API_BASE}/videos/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getVideoRecommendations(pathId) {
  return jsonFetch(`${API_BASE}/paths/${pathId}/video-recommendations`);
}

// Voice Tutor APIs
export function getVoicePracticeScenarios(pathId, phaseIdx) {
  return jsonFetch(`${API_BASE}/voice/scenarios/${pathId}/${phaseIdx}`);
}

export function startVoiceSession(pathId, phaseIdx, body) {
  return jsonFetch(`${API_BASE}/voice/session/start/${pathId}/${phaseIdx}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function submitVoiceResponse(sessionId, body) {
  return jsonFetch(`${API_BASE}/voice/session/${sessionId}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getVoiceSessionHistory(pathId) {
  return jsonFetch(`${API_BASE}/voice/history/${pathId}`);
}

export function startTutorChat(body) {
  return jsonFetch(`${API_BASE}/voice/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function sendTutorMessage(conversationId, body) {
  return jsonFetch(`${API_BASE}/voice/chat/${conversationId}/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getMyConversations() {
  return jsonFetch(`${API_BASE}/voice/conversations`);
}

// Practice Scenarios APIs
export function getPracticeScenariosList(pathId, phaseIdx) {
  return jsonFetch(`${API_BASE}/practice/scenarios/${pathId}/${phaseIdx}`);
}

export function startPracticeScenario(pathId, phaseIdx, body) {
  return jsonFetch(`${API_BASE}/practice/start/${pathId}/${phaseIdx}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function submitPracticeResponse(conversationId, body) {
  return jsonFetch(`${API_BASE}/practice/${conversationId}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getPracticeHistory(pathId) {
  return jsonFetch(`${API_BASE}/practice/history/${pathId}`);
}

export function getPracticeTips() {
  return jsonFetch(`${API_BASE}/practice/tips`);
}

export function getInterviewQuestions() {
  return jsonFetch(`${API_BASE}/practice/interview-questions`);
}

export function getCodingChallenges() {
  return jsonFetch(`${API_BASE}/practice/coding-challenges`);
}

// Job Target APIs
export function analyzeJobDescription(jobDescription) {
  return jsonFetch(`${API_BASE}/job-target/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_description: jobDescription }),
  });
}

export function findSkillGaps(body) {
  return jsonFetch(`${API_BASE}/job-target/gaps`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getJobTargetPaths(body) {
  return jsonFetch(`${API_BASE}/job-target/paths`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getJobMarketInsights(body) {
  return jsonFetch(`${API_BASE}/job-target/insights`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
