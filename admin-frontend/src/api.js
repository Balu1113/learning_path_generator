const API = "/api";

async function req(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: options.body ? { "Content-Type": "application/json" } : {},
  });
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const err = new Error(
      (data && typeof data.error === "string" && data.error) || res.statusText || "Request failed"
    );
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

export function login(username, password) {
  return req(`${API}/auth/login`, {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function logout() {
  return req(`${API}/auth/logout`, { method: "POST", body: "{}" });
}

export function me() {
  return req(`${API}/auth/me`);
}

export function fetchMeta() {
  return req(`${API}/admin/_meta/`);
}

export function fetchCounts() {
  return req(`${API}/admin/counts/`);
}

export function listResource(name, { page = 1, pageSize = 20, search = "", sort = "" } = {}) {
  const qs = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (search) qs.set("search", search);
  if (sort) qs.set("sort", sort);
  return req(`${API}/admin/${name}/?${qs}`);
}

export function fetchResource(name, id) {
  return req(`${API}/admin/${name}/${encodeURIComponent(id)}/`);
}

export function createResource(name, payload) {
  return req(`${API}/admin/${name}/`, { method: "POST", body: JSON.stringify(payload) });
}

export function updateResource(name, id, payload) {
  return req(`${API}/admin/${name}/${encodeURIComponent(id)}/`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteResource(name, id) {
  return req(`${API}/admin/${name}/${encodeURIComponent(id)}/`, { method: "DELETE" });
}
