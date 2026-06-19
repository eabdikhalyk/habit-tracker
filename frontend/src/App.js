import { useState } from "react";
import AuthForm from "./components/AuthForm";
import Dashboard from "./components/Dashboard";
import { getToken, clearToken } from "./api";
import "./App.css";

function App() {
  // Источник правды о том, залогинен ли пользователь, — наличие токена.
  // Инициализируем из localStorage, чтобы вход переживал перезагрузку страницы.
  const [token, setToken] = useState(getToken());

  // AuthForm вызовет onLogin при успешном входе и передаст сюда токен.
  function handleLogin(newToken) {
    setToken(newToken);
  }

  function handleLogout() {
    clearToken();
    setToken(null);
  }

  // Нет токена → показываем форму входа/регистрации.
  if (!token) {
    return (
      <div className="App">
        <AuthForm onLogin={handleLogin} />
      </div>
    );
  }

  // Есть токен → показываем приложение со списком привычек.
  return <Dashboard onLogout={handleLogout} />;
}

export default App;
