import { useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";

const MAX_HISTORY = 20; // matches the backend cap

const SUGGESTIONS = [
  "What should I play next from my backlog?",
  "Something short I can finish this weekend?",
  "Recommend a game like my top-rated ones",
];

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const send = async (text) => {
    const content = text.trim();
    if (!content || busy) return;
    const next = [...messages, { role: "user", content }].slice(-MAX_HISTORY);
    setMessages(next);
    setInput("");
    setErr("");
    setBusy(true);
    try {
      const { reply } = await api.chat(next);
      setMessages([...next, { role: "assistant", content: reply }]);
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page" style={{ maxWidth: 760 }}>
      <div className="section-head">
        <h3 id="chat-heading">Assistant</h3>
        <span className="sub">beat your backlog, find what to play next</span>
      </div>

      <div className="panel pad chat-log" role="log" aria-labelledby="chat-heading" aria-live="polite">
        {messages.length === 0 && (
          <div className="empty" style={{ padding: "36px 12px" }}>
            Ask me about your library. I can see your backlog, ratings, and recommendations.
            <div className="row" style={{ gap: 8, flexWrap: "wrap", justifyContent: "center", marginTop: 16 }}>
              {SUGGESTIONS.map((s) => (
                <button key={s} className="btn sm" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            {m.content}
          </div>
        ))}
        {busy && <div className="chat-msg assistant muted">Thinking…</div>}
        <div ref={endRef} />
      </div>

      {err && <div className="banner error" style={{ marginTop: 12 }}>{err}</div>}

      <form
        className="row"
        style={{ gap: 8, marginTop: 12 }}
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input
          className="input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your backlog…"
          aria-label="Message the assistant"
          maxLength={2000}
          disabled={busy}
        />
        <button className="btn primary" type="submit" disabled={busy || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
