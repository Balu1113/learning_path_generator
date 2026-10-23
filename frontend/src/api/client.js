const API_BASE = "/api";

async function jsonFetch(url, options = {}) {
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
  return jsonFetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

export async function loginUser(username, password) {
  return jsonFetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

export async function logoutUser() {
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
    body: "{}",
  });
}
