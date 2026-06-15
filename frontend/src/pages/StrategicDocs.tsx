export const BUILD_VERSION = "1781420759";
import { useEffect, useMemo, useState } from "react";

type DocItem = {
  id: string;
  title: string;
  filename: string;
  category: string;
  source: string;
  size: number;
  modified: string;
};

const categoryLabels: Record<string, string> = {
  company: "公司战略",
  contracts: "合同文档",
  projects: "项目方案",
};

export default function StrategicDocs() {
  const [docs, setDocs] = useState<DocItem[]>([]);
  const [activeCategory, setActiveCategory] = useState("all");
  const [selected, setSelected] = useState<DocItem | null>(null);
  const [content, setContent] = useState("请选择左侧文档查看内容");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/strategy-docs/list")
      .then((r) => r.json())
      .then((data) => {
        if (data.success) {
          setDocs(data.docs || []);
          if ((data.docs || []).length > 0) {
            openDoc(data.docs[0]);
          }
        } else {
          setError(data.error || "加载战略文档失败");
        }
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const filteredDocs = useMemo(() => {
    if (activeCategory === "all") return docs;
    return docs.filter((d) => d.category === activeCategory);
  }, [docs, activeCategory]);

  const stats = useMemo(() => {
    return {
      total: docs.length,
      company: docs.filter((d) => d.category === "company").length,
      contracts: docs.filter((d) => d.category === "contracts").length,
      projects: docs.filter((d) => d.category === "projects").length,
    };
  }, [docs]);

  function openDoc(doc: DocItem) {
    setSelected(doc);
    setContent("加载中...");
    fetch(`/api/strategy-docs/content?category=${encodeURIComponent(doc.category)}&file=${encodeURIComponent(doc.filename)}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.success) setContent(data.content || "");
        else setContent(`读取失败：${data.error || "未知错误"}`);
      })
      .catch((e) => setContent(`读取失败：${String(e)}`));
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>📂 战略文档中心</h1>
        <p>聚合和光智成战略、融资、合同、项目方案与核心业务文档。</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card"><div className="stat-value">{stats.total}</div><div className="stat-label">全部文档</div></div>
        <div className="stat-card"><div className="stat-value">{stats.company}</div><div className="stat-label">公司战略</div></div>
        <div className="stat-card"><div className="stat-value">{stats.contracts}</div><div className="stat-label">合同文档</div></div>
        <div className="stat-card"><div className="stat-value">{stats.projects}</div><div className="stat-label">项目方案</div></div>
      </div>

      <div style={{ display: "flex", gap: 10, margin: "18px 0", flexWrap: "wrap" }}>
        {["all", "company", "contracts", "projects"].map((c) => (
          <button
            key={c}
            onClick={() => setActiveCategory(c)}
            style={{
              padding: "8px 14px",
              borderRadius: 999,
              border: activeCategory === c ? "1px solid #2563eb" : "1px solid #d1d5db",
              background: activeCategory === c ? "#2563eb" : "white",
              color: activeCategory === c ? "white" : "#374151",
              cursor: "pointer",
            }}
          >
            {c === "all" ? "全部" : categoryLabels[c] || c}
          </button>
        ))}
      </div>

      {loading && <div className="card">加载中...</div>}
      {error && <div className="card" style={{ color: "#b91c1c" }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 18, alignItems: "start" }}>
        <div className="card" style={{ maxHeight: "72vh", overflow: "auto" }}>
          <h3 style={{ marginTop: 0 }}>文档列表</h3>
          {filteredDocs.map((doc) => (
            <div
              key={doc.id}
              onClick={() => openDoc(doc)}
              style={{
                padding: "12px",
                borderRadius: 10,
                marginBottom: 10,
                border: selected?.id === doc.id ? "1px solid #2563eb" : "1px solid #e5e7eb",
                background: selected?.id === doc.id ? "#eff6ff" : "#fff",
                cursor: "pointer",
              }}
            >
              <div style={{ fontWeight: 700, color: "#111827" }}>{doc.title}</div>
              <div style={{ fontSize: 12, color: "#6b7280", marginTop: 6 }}>{categoryLabels[doc.category] || doc.category} · {(doc.size / 1024).toFixed(1)} KB</div>
              <div style={{ fontSize: 12, color: "#9ca3af", marginTop: 4 }}>{doc.modified}</div>
            </div>
          ))}
          {!filteredDocs.length && <div style={{ color: "#6b7280" }}>暂无文档</div>}
        </div>

        <div className="card" style={{ minHeight: "72vh" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <div>
              <h2 style={{ margin: 0 }}>{selected?.title || "文档内容"}</h2>
              {selected && <div style={{ fontSize: 13, color: "#6b7280", marginTop: 6 }}>{categoryLabels[selected.category] || selected.category} · {selected.filename}</div>}
            </div>
          </div>
          <pre style={{
            whiteSpace: "pre-wrap",
            lineHeight: 1.75,
            fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
            fontSize: 14,
            color: "#1f2937",
            margin: 0,
          }}>{content}</pre>
        </div>
      </div>
    </div>
  );
}
