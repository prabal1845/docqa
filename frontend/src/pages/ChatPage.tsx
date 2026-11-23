import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link } from "react-router-dom";
import { api, type Citation, type DocumentInfo, type QueryResponse } from "../api";

interface Turn {
  id: number;
  question: string;
  response?: QueryResponse;
  error?: string;
}

export default function ChatPage() {
  const [docs, setDocs] = useState<DocumentInfo[] | null>(null);
  const [selected, setSelected] = useState<number[]>([]);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api
      .listDocuments()
      .then(setDocs)
      .catch(() => setDocs([]));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  const readyDocs = docs?.filter((d) => d.status === "ready") ?? [];

  async function ask(e?: FormEvent) {
    e?.preventDefault();
    const q = question.trim();
    if (q.length < 3 || asking) return;
    const id = Date.now();
    setTurns((t) => [...t, { id, question: q }]);
    setQuestion("");
    setAsking(true);
    try {
      const response = await api.query(q, selected);
      setTurns((t) => t.map((turn) => (turn.id === id ? { ...turn, response } : turn)));
    } catch (err) {
      const error = err instanceof Error ? err.message : "Something went wrong";
      setTurns((t) => t.map((turn) => (turn.id === id ? { ...turn, error } : turn)));
    } finally {
      setAsking(false);
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      ask();
    }
  }

  function toggle(id: number) {
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }

  return (
    <div className="chat-layout">
      <aside className="sidebar">
        <h2>Search in</h2>
        {docs === null ? (
          <p className="muted small">Loading…</p>
        ) : readyDocs.length === 0 ? (
          <p className="muted small">
            No ready documents. <Link to="/documents">Upload one</Link>
          </p>
        ) : (
          <>
            <label className="check">
              <input
                type="checkbox"
                checked={selected.length === 0}
                onChange={() => setSelected([])}
              />
              All documents
            </label>
            {readyDocs.map((d) => (
              <label key={d.id} className="check" title={d.filename}>
                <input
                  type="checkbox"
                  checked={selected.includes(d.id)}
                  onChange={() => toggle(d.id)}
                />
                <span className="truncate">{d.filename}</span>
              </label>
            ))}
          </>
        )}
      </aside>

      <section className="chat">
        <div className="messages">
          {turns.length === 0 && (
            <div className="empty-chat">
              <h1>Ask your documents anything</h1>
              <p className="muted">
                Answers come only from your PDFs. Click a <span className="cite static">1</span>{" "}
                marker to see the exact passage and page.
              </p>
            </div>
          )}
          {turns.map((turn) => (
            <div key={turn.id} className="turn">
              <div className="bubble user">{turn.question}</div>
              {turn.response ? (
                <Answer response={turn.response} />
              ) : turn.error ? (
                <div className="bubble assistant error">{turn.error}</div>
              ) : (
                <div className="bubble assistant muted thinking">Searching your documents…</div>
              )}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        <form className="composer" onSubmit={ask}>
          <textarea
            rows={1}
            placeholder={
              readyDocs.length ? "Ask a question… (Enter to send)" : "Upload a document first"
            }
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={onKeyDown}
            maxLength={1000}
          />
          <button className="primary" disabled={asking || question.trim().length < 3}>
            Ask
          </button>
        </form>
      </section>
    </div>
  );
}

function Answer({ response }: { response: QueryResponse }) {
  const [active, setActive] = useState<number | null>(null);
  const [showAll, setShowAll] = useState(false);
  const sourceRefs = useRef<Record<number, HTMLLIElement | null>>({});

  const byIndex = new Map(response.citations.map((c) => [c.index, c]));
  const cited = response.citations.filter((c) => c.cited);
  const others = response.citations.filter((c) => !c.cited);
  const visible = showAll ? response.citations : cited;

  function open(index: number) {
    setActive(index);
    if (!byIndex.get(index)?.cited) setShowAll(true);
    // Wait for the source list to render before scrolling to it
    requestAnimationFrame(() =>
      sourceRefs.current[index]?.scrollIntoView({ behavior: "smooth", block: "nearest" }),
    );
  }

  // Turn "[2]" markers into buttons; leave numbers with no matching source as plain text
  const parts = response.answer.split(/(\[\d+\])/g).map((part, i) => {
    const match = /^\[(\d+)\]$/.exec(part);
    const index = match ? Number(match[1]) : null;
    if (index === null || !byIndex.has(index)) return part;
    const c = byIndex.get(index)!;
    return (
      <button
        key={i}
        className={`cite ${active === index ? "active" : ""}`}
        onClick={() => open(index)}
        title={`${c.filename}, page ${c.page}`}
      >
        {index}
      </button>
    );
  });

  return (
    <div className="bubble assistant">
      <p className="answer">{parts}</p>
      {response.citations.length > 0 && (
        <div className="sources">
          <div className="sources-head">
            <span className="muted small">Sources</span>
            {others.length > 0 && (
              <button className="link small" onClick={() => setShowAll((s) => !s)}>
                {showAll ? "Hide uncited" : `Show ${others.length} more retrieved`}
              </button>
            )}
          </div>
          <ul>
            {visible.map((c) => (
              <Source
                key={c.index}
                citation={c}
                active={active === c.index}
                onClick={() => setActive(active === c.index ? null : c.index)}
                ref={(el) => {
                  sourceRefs.current[c.index] = el;
                }}
              />
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Source({
  citation: c,
  active,
  onClick,
  ref,
}: {
  citation: Citation;
  active: boolean;
  onClick: () => void;
  ref: (el: HTMLLIElement | null) => void;
}) {
  return (
    <li ref={ref} className={`source ${active ? "active" : ""} ${c.cited ? "" : "uncited"}`}>
      <button className="source-head" onClick={onClick} aria-expanded={active}>
        <span className="cite static">{c.index}</span>
        <span className="truncate">{c.filename}</span>
        <span className="muted small">p. {c.page}</span>
        <span className="muted small score" title="Similarity to your question">
          {Math.round(c.score * 100)}% match
        </span>
      </button>
      {active && (
        <blockquote>
          {c.snippet}
          {c.snippet.length >= 300 && "…"}
        </blockquote>
      )}
    </li>
  );
}
