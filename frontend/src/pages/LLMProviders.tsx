import { useEffect, useMemo, useState } from "react";

type Provider = { name: string; baseUrl: string; modelCount: number; active?: boolean };
type Model = { provider: string; model: string; name?: string; reasoning?: boolean; contextWindow?: number; maxTokens?: number };

function fmt(n?: number) {
  if (!n) return "-";
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `${Math.round(n / 1000)}K`;
  return String(n);
}

export default function LLMProviders() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  const [selectedProvider, setSelectedProvider] = useState("all");
  const [query, setQuery] = useState("");
  const [updatedAt, setUpdatedAt] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/llm-providers")
      .then((r) => r.json())
      .then((data) => {
        if (data.success) {
          setProviders(data.providers || []);
          setModels(data.models || []);
          setUpdatedAt(data.updated_at || "");
        } else {
          setError(data.error || "加载 LLM Provider 失败");
        }
      })
      .catch((e) => setError(String(e)));
  }, []);

  const filtered = useMemo(() => {
    return models.filter((m) => {
      const okProvider = selectedProvider === "all" || m.provider === selectedProvider;
      const text = `${m.provider} ${m.model} ${m.name || ""}`.toLowerCase();
      return okProvider && text.includes(query.toLowerCase());
    });
  }, [models, selectedProvider, query]);

  const totalContext = useMemo(() => models.reduce((max, m) => Math.max(max, m.contextWindow || 0), 0), [models]);
  const reasoningCount = useMemo(() => models.filter((m) => m.reasoning).length, [models]);

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>🧠 LLM Provider 仪表盘</h1>
        <p>从 OpenClaw 配置生成脱敏快照，只展示 Provider、模型、上下文和能力，不暴露 API Key。</p>
      </div>

      {error && <div className="card" style={{ color: "#b91c1c" }}>{error}</div>}

      <div className="stats-grid">
        <div className="stat-card"><div className="stat-value">{providers.length}</div><div className="stat-label">Provider</div></div>
        <div className="stat-card"><div className="stat-value">{models.length}</div><div className="stat-label">模型总数</div></div>
        <div className="stat-card"><div className="stat-value">{reasoningCount}</div><div className="stat-label">Reasoning 模型</div></div>
        <div className="stat-card"><div className="stat-value">{fmt(totalContext)}</div><div className="stat-label">最大上下文</div></div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <div style={{ color: "#6b7280" }}>更新时间：{updatedAt || "-"}</div>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索 provider / model..."
            style={{ padding: "9px 12px", borderRadius: 8, border: "1px solid #d1d5db", minWidth: 260 }}
          />
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 18, marginTop: 18, alignItems: "start" }}>
        <div className="card" style={{ maxHeight: "74vh", overflow: "auto" }}>
          <h3 style={{ marginTop: 0 }}>Provider 列表</h3>
          <div
            onClick={() => setSelectedProvider("all")}
            style={{ padding: 12, borderRadius: 10, marginBottom: 10, cursor: "pointer", background: selectedProvider === "all" ? "#eff6ff" : "#fff", border: selectedProvider === "all" ? "1px solid #2563eb" : "1px solid #e5e7eb" }}
          >全部模型 · {models.length}</div>
          {providers.map((p) => (
            <div
              key={p.name}
              onClick={() => setSelectedProvider(p.name)}
              style={{ padding: 12, borderRadius: 10, marginBottom: 10, cursor: "pointer", background: selectedProvider === p.name ? "#eff6ff" : "#fff", border: selectedProvider === p.name ? "1px solid #2563eb" : "1px solid #e5e7eb" }}
            >
              <div style={{ fontWeight: 700 }}>{p.name}</div>
              <div style={{ fontSize: 12, color: "#6b7280", marginTop: 6 }}>{p.modelCount} models</div>
              <div style={{ fontSize: 11, color: "#9ca3af", marginTop: 4, wordBreak: "break-all" }}>{p.baseUrl}</div>
            </div>
          ))}
        </div>

        <div className="card" style={{ overflowX: "auto" }}>
          <h3 style={{ marginTop: 0 }}>模型清单（{filtered.length}）</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#f9fafb" }}>
                <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #e5e7eb" }}>Provider</th>
                <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #e5e7eb" }}>Model</th>
                <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #e5e7eb" }}>Name</th>
                <th style={{ textAlign: "right", padding: 10, borderBottom: "1px solid #e5e7eb" }}>Context</th>
                <th style={{ textAlign: "right", padding: 10, borderBottom: "1px solid #e5e7eb" }}>Max Tokens</th>
                <th style={{ textAlign: "center", padding: 10, borderBottom: "1px solid #e5e7eb" }}>Reasoning</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((m, idx) => (
                <tr key={`${m.provider}-${m.model}-${idx}`}>
                  <td style={{ padding: 10, borderBottom: "1px solid #f3f4f6", fontWeight: 600 }}>{m.provider}</td>
                  <td style={{ padding: 10, borderBottom: "1px solid #f3f4f6", fontFamily: "monospace" }}>{m.model}</td>
                  <td style={{ padding: 10, borderBottom: "1px solid #f3f4f6" }}>{m.name || "-"}</td>
                  <td style={{ padding: 10, borderBottom: "1px solid #f3f4f6", textAlign: "right" }}>{fmt(m.contextWindow)}</td>
                  <td style={{ padding: 10, borderBottom: "1px solid #f3f4f6", textAlign: "right" }}>{fmt(m.maxTokens)}</td>
                  <td style={{ padding: 10, borderBottom: "1px solid #f3f4f6", textAlign: "center" }}>{m.reasoning ? "✅" : "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
