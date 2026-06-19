import { useState, useEffect } from "react";
import { api } from "../api";

// Главный экран: список вредных привычек + действия над ними.
export default function Dashboard({ onLogout }) {
  const [habits, setHabits] = useState([]);
  const [title, setTitle] = useState("");   // поле "новая привычка"
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  // useEffect с [] = выполнить один раз при появлении компонента.
  // Внутрь нельзя писать async напрямую, поэтому вызываем отдельную функцию.
  useEffect(() => {
    loadHabits();
  }, []);

  async function loadHabits() {
    try {
      const data = await api.getHabits();
      setHabits(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    const t = title.trim();
    if (!t) return;            // не создаём пустую привычку
    try {
      await api.createHabit(t);
      setTitle("");
      loadHabits();            // перезагружаем список, чтобы увидеть новую
    } catch (err) {
      setError(err.message);
    }
  }

  // Три действия устроены одинаково: дернуть API → перезагрузить список.
  async function handleCheckin(id) {
    try { await api.checkin(id); loadHabits(); }
    catch (err) { setError(err.message); }
  }

  async function handleRelapse(id) {
    try { await api.relapse(id, null); loadHabits(); }
    catch (err) { setError(err.message); }
  }

  async function handleDelete(id) {
    try { await api.deleteHabit(id); loadHabits(); }
    catch (err) { setError(err.message); }
  }

  return (
    <div className="dashboard">
      <header className="topbar">
        <h1>🔥 Мои привычки</h1>
        <button className="btn ghost" onClick={onLogout}>Выйти</button>
      </header>

      {/* Форма добавления */}
      <form className="add-form" onSubmit={handleCreate}>
        <input
          type="text"
          placeholder="С чем борешься? (напр. Курение)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <button className="btn" type="submit">Добавить</button>
      </form>

      {error && <p className="error">{error}</p>}

      {/* Три состояния экрана: загрузка → пусто → список */}
      {loading ? (
        <p className="muted">Загрузка...</p>
      ) : habits.length === 0 ? (
        <p className="muted">Привычек пока нет. Добавь первую! 💪</p>
      ) : (
        <div className="habit-list">
          {habits.map((h) => (
            // key обязателен — по нему React отслеживает элементы списка
            <div className="habit-card" key={h.id}>
              <div className="habit-info">
                <h3>{h.title}</h3>
                <span className="streak">🔥 {h.streak} дней</span>
              </div>
              <div className="actions">
                <button className="btn small" onClick={() => handleCheckin(h.id)}>
                  ✅ Держусь
                </button>
                <button className="btn small ghost" onClick={() => handleRelapse(h.id)}>
                  😔 Сорвался
                </button>
                <button className="btn small danger" onClick={() => handleDelete(h.id)}>
                  🗑
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}