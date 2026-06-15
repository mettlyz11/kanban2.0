import { useEffect, useMemo, useState } from "react";

type Doc = {
  id: string; title: string; name: string; filename: string;
  category: string; source: string; size: number; mtime: number;
  modified: string; url: string;
};

const catEmoji: Record<string, string> = { industry: "\u{1F4CA}", articles: "\u{1F4DC}" };
const catLabel: Record<string, string> = { industry: "\u884C\u4E1A\u62A5\u544A", articles: "\u5B66\u672F\u6587\u7AE0" };

export default function KnowledgeLibrary() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [cats, setCats] = useState<any[]>([]);
  const [activeCat, setActiveCat] = useState("all");
  const [selected, setSelected] = useState<Doc | null>(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/knowledge-library/list")
      .then(r => r.json())
      .then(d => {
        if (!d.success) { setError(d.error || "加载失败"); return; }
        setDocs(d.docs || []);
        setCats(d.categories || []);
        if ((d.docs || []).length > 0) openDoc(d.docs[0]);
      })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    if (activeCat === "all") return docs;
    return docs.filter(d => d.category === activeCat);
  }, [docs, activeCat]);

  const stats = useMemo(() => ({
    total: docs.length,
    industry: docs.filter(d => d.category === "industry").length,
    articles: docs.filter(d => d.category === "articles").length,
  }), [docs]);

  function openDoc(doc: Doc) {
    setSelected(doc);
    setContent("加载中...");
    fetch("/api/knowledge-library/content?category=" + encodeURIComponent(doc.category) + "&file=" + encodeURIComponent(doc.filename))
      .then(r => r.json())
      .then(d => setContent(d.success ? (d.content || "") : "读取失败：" + (d.error||"")))
      .catch(e => setContent("读取失败：" + String(e)));
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>{'\u{1F4DA}'} 行业 & 学术文库</h1>
        <p>聚合行业研究报告与学术文章，每日自动同步。</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card"><div className="stat-value">{stats.total}</div><div className="stat-label">全部文献</div></div>
        <div className="stat-card"><div className="stat-value">{stats.industry}</div><div className="stat-label">行业报告</div></div>
        <div className="stat-card"><div className="stat-value">{stats.articles}</div><div className="stat-label">学术文章</div></div>
      </div>

      <div style={{ display: "flex", gap: 10, margin: "18px 0", flexWrap: "wrap" }}>
        {cats.map((c: any) => (
          <button key={c.key} onClick={() => setActiveCat(c.key === activeCat ? "all" : c.key)}
            style={{ padding: "8px 14px", borderRadius: 999, border: "1px solid " + (activeCat === c.key ? "#2563eb" : "#d1d5db"),
              background: activeCat === c.key ? "#2563eb" : "white", color: activeCat === c.key ? "white" : "#374151", cursor: "pointer" }}>
            {catEmoji[c.key] || "\uD83D\uDCC1"} {catLabel[c.key] || c.key} ({c.total})
          </button>
        ))}
        {activeCat !== "all" && <button onClick={() => setActiveCat("all")} style={{ padding: "8px 14px", borderRadius: 999, border: "1px solid #9ca3af", background: "#f3f4f6", cursor: "pointer" }}>✕ 清除筛选</button>}
      </div>

      {loading && <div className="card">加载中...</div>}
      {error && <div className="card" style={{ color: "#b91c1c" }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 18, alignItems: "start" }}>
        <div className="card" style={{ maxHeight: "72vh", overflow: "auto" }}>
          <h3 style={{ marginTop: 0 }}>文献列表</h3>
          {filtered.map(doc => (
            <div key={doc.id} onClick={() => openDoc(doc)}
              style={{ padding: 12, borderRadius: 10, marginBottom: 10, cursor: "pointer",
                border: selected?.id === doc.id ? "1px solid #2563eb" : "1px solid #e5e7eb",
                background: selected?.id === doc.id ? "#eff6ff" : "#fff" }}>
              <div style={{ fontWeight: 700, color: "#111", fontSize: 13 }}>{doc.title}</div>
              <div style={{ fontSize: 11, color: "#6b7280", marginTop: 4 }}>
                {catEmoji[doc.category] || "\uD83D\uDCC1"} {catLabel[doc.category] || doc.category} · {(doc.size / 1024).toFixed(0)} KB
              </div>
              <div style={{ fontSize: 11, color: "#9ca3af", marginTop: 2 }}>{doc.modified}</div>
            </div>
          ))}
          {!filtered.length && <div style={{ color: "#6b7280" }}>暂无文献</div>}
        </div>

        <div className="card" style={{ minHeight: "72vh" }}>
          <div style={{ marginBottom: 12 }}>
            <h2 style={{ margin: 0 }}>{selected?.title || "文献内容"}</h2>
            {selected && <div style={{ fontSize: 13, color: "#6b7280", marginTop: 6 }}>{catLabel[selected.category] || selected.category} · {selected.filename}</div>}
          </div>
          <pre style={{ whiteSpace: "pre-wrap", lineHeight: 1.75, fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif", fontSize: 14, color: "#1f2937", margin: 0 }}>{content}</pre>
        </div>
      </div>
    </div>
  );
}
