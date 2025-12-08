// frontend/src/App.jsx
import React, { useState } from "react";
import "./App.css";

export default function App() {
  const [repoA, setRepoA] = useState([]);
  const [repoB, setRepoB] = useState([]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");

  const handleFolder = (e, setter) => {
    const files = Array.from(e.target.files || []);
    setter(files);
  };

  function pct(v) {
    if (v == null) return "—";
    return `${Math.round(v * 100)}%`;
  }

  function downloadResultsJson(obj) {
    const blob = new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "detailed_output.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  async function handleCheck() {
    if (!repoA.length || !repoB.length) {
      setError("Please select both repository folders first.");
      return;
    }

    setError("");
    setResults(null);
    setLoading(true);
    setProgress(5);

    try {
      const fd = new FormData();
      repoA.forEach((f) => fd.append("repoA", f, f.webkitRelativePath || f.name));
      repoB.forEach((f) => fd.append("repoB", f, f.webkitRelativePath || f.name));

      setProgress(20);

      const resp = await fetch("http://localhost:8000/api/compare", {
        method: "POST",
        body: fd,
      });

      setProgress(60);
      const txt = await resp.text();

      let payload;
      try {
        // normal case: backend returned a JSON object string
        payload = JSON.parse(txt);
      } catch (e) {
        // sometimes backend returns {"output_raw":"{...json...}"} or similar
        try {
          const wrapped = JSON.parse(txt);
          if (wrapped && wrapped.output_raw) {
            payload = JSON.parse(wrapped.output_raw);
          } else {
            payload = wrapped;
          }
        } catch (e2) {
          console.error("Failed to parse server response:", txt, e, e2);
          throw new Error("Server returned invalid JSON. Check backend logs or network response.");
        }
      }

      setResults(payload);
      setProgress(100);
    } catch (err) {
      console.error(err);
      setError(String(err.message || err));
    } finally {
      setLoading(false);
      setTimeout(() => setProgress(0), 700);
    }
  }

  return (
    <div className="page">
      <div className="card">
        <h1 className="title">🔍 Repo Similarity Checker</h1>

        <p className="subtitle">
          Pick two project folders (click folder, not zip). The server will receive the file tree,
          run the analyzer and return results.
        </p>

        <div className="grid">
          <label className="panel">
            <div className="label">Upload Repo A</div>
            <input
              type="file"
              webkitdirectory="true"
              directory="true"
              multiple
              onChange={(e) => handleFolder(e, setRepoA)}
            />
            <div className="meta">Files: {repoA.length}</div>
          </label>

          <label className="panel">
            <div className="label">Upload Repo B</div>
            <input
              type="file"
              webkitdirectory="true"
              directory="true"
              multiple
              onChange={(e) => handleFolder(e, setRepoB)}
            />
            <div className="meta">Files: {repoB.length}</div>
          </label>
        </div>

        <div className="actions">
          <button className="btn primary" onClick={handleCheck} disabled={loading}>
            {loading ? "Checking..." : "Check Similarity"}
          </button>

          <div className="progressWrap">
            <div className="progressBar">
              <div className="progressFill" style={{ width: `${progress}%` }} />
            </div>
            <div className="progressText">{loading ? `${progress}%` : ""}</div>
          </div>
        </div>

        {error && <div className="errorBox">⚠️ {error}</div>}

        {results && (
          <div className="results">
            <div className="resultsHeader">
              <div>
                <div className="small">Overall similarity</div>
                <div className="big">{pct(results.overall_repo_similarity)}</div>
              </div>

              <div>
                <button className="btn" onClick={() => downloadResultsJson(results)}>
                  Download JSON
                </button>
              </div>
            </div>

            <div className="small muted" style={{ marginTop: 8 }}>
              Files A: {results.filesA?.length || 0} • Files B: {results.filesB?.length || 0}
            </div>

            <div className="matches" style={{ marginTop: 12 }}>
              <div className="small muted">All file-to-file comparisons</div>
              {results.pairs && results.pairs.length ? (
                results.pairs.slice(0, 30).map((p, i) => (
                  <div className="matchRow" key={i}>
                    <div className="matchFiles">
                      <div className="fileA" title={p.fileA}>{p.fileA}</div>
                      <div className="arrow">↔</div>
                      <div className="fileB" title={p.fileB}>{p.fileB}</div>
                    </div>
                    <div className="matchScore">{Math.round(p.jaccard * 100)}%</div>
                  </div>
                ))
              ) : (
                <div className="muted">No matches found.</div>
              )}
            </div>

            <details className="rawJson" style={{ marginTop: 12 }}>
              <summary>Show full JSON output</summary>
              <pre>{JSON.stringify(results, null, 2)}</pre>
            </details>
          </div>
        )}
      </div>
    </div>
  );
}
