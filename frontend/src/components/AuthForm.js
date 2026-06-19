import { useState } from "react";
import { api, setToken } from "../api";

// Одна форма на вход и регистрацию — переключается режимом.
// После успешной регистрации сразу логиним пользователя (хороший UX).
export default function AuthForm({ onLogin }) {
  const [mode, setMode] = useState("login"); // 'login' | 'register'
  const [email, setEmail] = useState("");
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  // identifier — то, чем пользователь входит: email ИЛИ login.
  const [identifier, setIdentifier] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault(); // иначе браузер перезагрузит страницу
    setError("");
    setLoading(true);
    try {
      if (mode === "register") {
        await api.register(email, login, password);
        // После регистрации логинимся по email (он точно валиден как идентификатор).
        const { access_token } = await api.login(email, password);
        setToken(access_token);
        onLogin(access_token);
      } else {
        // Вход: отправляем то, что ввёл пользователь — бэкенд поймёт email или login.
        const { access_token } = await api.login(identifier, password);
        setToken(access_token);
        onLogin(access_token);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function toggleMode() {
    setMode(mode === "login" ? "register" : "login");
    setError("");
  }

  return (
    <form className="card auth" onSubmit={handleSubmit}>
      <h2>{mode === "login" ? "Вход" : "Регистрация"}</h2>

      {mode === "register" ? (
        <>
          <input
            type="text"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            type="text"
            placeholder="Login (ник)"
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            required
          />
        </>
      ) : (
        <input
          type="text"
          placeholder="Email или login"
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          required
        />
      )}
      <input
        type="password"
        placeholder="Пароль"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />

      {error && <p className="error">{error}</p>}

      <button className="btn" type="submit" disabled={loading}>
        {loading ? "Минутку..." : mode === "login" ? "Войти" : "Зарегистрироваться"}
      </button>

      <p className="switch">
        {mode === "login" ? "Нет аккаунта? " : "Уже есть аккаунт? "}
        <span onClick={toggleMode}>
          {mode === "login" ? "Создать" : "Войти"}
        </span>
      </p>
    </form>
  );
}
