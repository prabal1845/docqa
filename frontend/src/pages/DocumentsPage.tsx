import { useCallback, useEffect, useRef, useState, type DragEvent } from "react";
import { api, type DocumentInfo } from "../api";

const POLL_MS = 1500;

export function StatusBadge({ status }: { status: DocumentInfo["status"] }) {
  return <span className={`badge ${status}`}>{status}</span>;
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(0);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      setDocs(await api.listDocuments());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents");
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll only while something is still being ingested
  const inProgress = docs?.some((d) => d.status === "pending" || d.status === "processing");
  useEffect(() => {
    if (!inProgress) return;
    const timer = setTimeout(refresh, POLL_MS);
    return () => clearTimeout(timer);
  }, [docs, inProgress, refresh]);

  async function upload(files: FileList | File[]) {
    setError(null);
    const list = Array.from(files);
    setUploading((n) => n + list.length);
    for (const file of list) {
      try {
        const doc = await api.uploadDocument(file);
        setDocs((prev) => [doc, ...(prev ?? [])]);
      } catch (err) {
        setError(`${file.name}: ${err instanceof Error ? err.message : "upload failed"}`);
      } finally {
        setUploading((n) => n - 1);
      }
    }
  }

  async function remove(doc: DocumentInfo) {
    if (!window.confirm(`Delete "${doc.filename}"? This can't be undone.`)) return;
    try {
      await api.deleteDocument(doc.id);
      setDocs((prev) => prev?.filter((d) => d.id !== doc.id) ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) upload(e.dataTransfer.files);
  }

  return (
    <div className="page">
      <h1>Documents</h1>

      <div
        className={`dropzone ${dragging ? "dragging" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          hidden
          onChange={(e) => {
            if (e.target.files?.length) upload(e.target.files);
            e.target.value = "";
          }}
        />
        <strong>{uploading ? `Uploading ${uploading} file(s)…` : "Drop PDFs here"}</strong>
        <span className="muted">or click to choose · text PDFs up to 10 MB</span>
      </div>

      {error && <div className="error">{error}</div>}

      {docs === null ? (
        <p className="muted">Loading…</p>
      ) : docs.length === 0 ? (
        <p className="muted empty">No documents yet. Upload a PDF to get started.</p>
      ) : (
        <ul className="doc-list">
          {docs.map((d) => (
            <li key={d.id} className="card doc-row">
              <div className="doc-main">
                <span className="filename" title={d.filename}>
                  {d.filename}
                </span>
                <span className="muted small">
                  {new Date(d.created_at).toLocaleString()}
                  {d.status === "ready" && ` · ${d.page_count} pages · ${d.chunk_count} chunks`}
                </span>
                {d.error && <span className="error-text small">{d.error}</span>}
              </div>
              <StatusBadge status={d.status} />
              <button className="link danger" onClick={() => remove(d)}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
