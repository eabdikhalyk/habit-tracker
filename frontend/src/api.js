// Единая точка общения с бэкендом.
// Зачем выносить отдельно: компоненты не должны знать про URL, заголовки и токены —
// они просто вызывают api.getHabits(). Это принцип разделения ответственности (SRP).

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

const TOKEN_KEY = "habit_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// Базовая обёртка над fetch: подставляет токен и единообразно обрабатывает ошибки.
async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    // FastAPI кладёт текст ошибки в поле detail
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Ошибка ${res.status}`);
  }

  return res.json();
}

export const api = {
  register: (email, login, password) =>
    request("/auth/register", {
      method: "POST",
      body: { email, login, password },
      auth: false,
    }),

  // ВАЖНО: /auth/login — особый случай. Бэкенд использует OAuth2PasswordRequestForm,
  // а он ждёт НЕ JSON, а form-urlencoded с полями username/password (не email!).
  async login(email, password) {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);

    const res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "Неверный email или пароль");
    }
    return res.json(); // { access_token, token_type }
  },

  getHabits: () => request("/habits/"),
  createHabit: (title) => request("/habits/", { method: "POST", body: { title } }),
  deleteHabit: (id) => request(`/habits/${id}`, { method: "DELETE" }),
  checkin: (id) => request(`/habits/${id}/checkin`, { method: "POST" }),
  relapse: (id, note) =>
    request(`/habits/${id}/relapse`, { method: "POST", body: { note } }),
};

export { API_URL };
