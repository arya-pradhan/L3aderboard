// Thin fetch wrapper around the GamerLog FastAPI backend.
const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

let token = localStorage.getItem("gl_token") || null;

export function setToken(t) {
  token = t;
  if (t) localStorage.setItem("gl_token", t);
  else localStorage.removeItem("gl_token");
}
export function getToken() {
  return token;
}

async function request(path, { method = "GET", body, form, auth = true } = {}) {
  const headers = {};
  let payload;
  if (form) {
    payload = new URLSearchParams(form).toString();
    headers["Content-Type"] = "application/x-www-form-urlencoded";
  } else if (body !== undefined) {
    payload = JSON.stringify(body);
    headers["Content-Type"] = "application/json";
  }
  if (auth && token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { method, headers, body: payload });
  if (res.status === 204) return null;

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data && data.detail;
    const err = new Error(
      typeof detail === "string" ? detail : `Request failed (${res.status})`
    );
    err.status = res.status;
    throw err;
  }
  return data;
}

const qs = (status) => (status ? `?status=${encodeURIComponent(status)}` : "");
const u = (name) => encodeURIComponent(name);

export const api = {
  base: BASE,
  register: (d) => request("/auth/register", { method: "POST", body: d, auth: false }),
  login: (username, password) =>
    request("/auth/login", { method: "POST", form: { username, password }, auth: false }),
  me: () => request("/auth/me"),

  searchGames: (q, limit = 18) =>
    request(`/games/search?q=${encodeURIComponent(q)}&limit=${limit}`),

  myLibrary: (status) => request(`/library${qs(status)}`),
  addToLibrary: (d) => request("/library", { method: "POST", body: d }),
  updateEntry: (id, d) => request(`/library/${id}`, { method: "PATCH", body: d }),
  deleteEntry: (id) => request(`/library/${id}`, { method: "DELETE" }),
  steamImport: () => request("/library/steam/import", { method: "POST" }),

  profile: (name) => request(`/users/${u(name)}`),
  userLibrary: (name, status) => request(`/users/${u(name)}/library${qs(status)}`),
  follow: (name) => request(`/users/${u(name)}/follow`, { method: "POST" }),
  unfollow: (name) => request(`/users/${u(name)}/follow`, { method: "DELETE" }),

  feed: () => request("/feed"),
  recommendations: (limit = 12) => request(`/recommendations?limit=${limit}`),

  steamLoginUrl: () => `${BASE}/auth/steam/login`,
};
