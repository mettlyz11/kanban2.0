import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

type Metric = { label: string; value: string | number; icon: string; path: string; color: string };

export default function KanbanOverview() {
  const [metrics, setMetrics] = useState<Metric[]>([
    { label: "加载中...", value: "-", icon: "⏳", path: "/", color: "#6b7280" },
  ]);
  const [daily, setDaily] = useState<{ title: string; content: string } | null>(null);
  const [time, setTime] = useState("");

  useEffect(() => {
    Promise.all([
      fetch("/api/strategy-docs/list").then(r => r.json()),
      fetch("/api/llm-providers").then(r => r.json()),
      fetch("/api/knowledge-library/list").then(r => r.json()),
      fetch("/api/contacts/list?limit=5").then(r => r.json()),
      fetch("/api/system/config-browser?limit=1").then(r => r.json()),
      fetch("/api/research-daily/list").then(r => r.json()),
    ]).then(([sd, llm, kl, ct, sc, rd]) => {
      const m: Metric[] = [
        { label: "战略文档", value: sd.total || "-", icon: "📂", path: "/strategic-docs", color: "#2563eb" },
        { label: "LLM Provider", value: (llm.providers?.length || 0) + "/" + (llm.models?.length || 0), icon: "🧠", path: "/llm-providers", color: "#8b5cf6" },
        { label: "行业&学术文库", value: kl.total || "-", icon: "📚", path: "/knowledge-library", color: "#10b981" },
        { label: "联系人", value: ct.total || "-", icon: "👥", path: "/contacts", color: "#f59e0b" },
        { label: "系统配置", value: sc.total || "-", icon: "⚙", path: "/sys-config", color: "#6b7280" },
        { label: "AI日报", value: rd.total || "0", icon: "🔬", path: "/research-daily", color: "#ec4899" },
      ];
      setMetrics(m);

      // Try to load latest daily report snippet
      if (rd?.reports?.length > 0) {
        const r = rd.reports[0];
        setDaily({ title: r.date || '最新日报', content: r.summary || '' });
        // Also fetch full content
        fetch('/api/research-daily/content?file=' + encodeURIComponent(r.filename))
          .then(r => r.json()).then(d => {
            if (d.success && d.content) {
              setDaily({ title: r.filename?.replace(/.md$/, '').replace(/_/g, ' ') || '最新日报', content: d.content.slice(0, 600) });
            }
          }).catch(() => {});
      }
    }).catch(() => {});

    setTime(new Date().toLocaleString("zh-CN", { timeZone: "Asia/Shanghai" }));
  }, []);

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>{'\u{1F4CA}'} 看板总览</h1>
        <p>聚合所有模块状态。最后更新：{time || "-"}</p>
      </div>

      <div className="stats-grid">
        {metrics.map(m => (
          <Link to={m.path} key={m.label} style={{ textDecoration: "none" }}>
            <div className="stat-card" style={{ cursor: "pointer", transition: "transform .15s" }}
              onMouseEnter={e => (e.currentTarget.style.transform = "translateY(-2px)")}
              onMouseLeave={e => (e.currentTarget.style.transform = "translateY(0)")}>
              <div className="stat-icon">{m.icon}</div>
              <div className="stat-value" style={{ color: m.color }}>{m.value}</div>
              <div className="stat-label">{m.label}</div>
            </div>
          </Link>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, marginTop: 18 }}>
        {/* Daily Report */}
        <div className="card">
          <h3 style={{ marginTop: 0, display: "flex", justifyContent: "space-between" }}>
            <span>{'\u{1F4DD}'} 最新 AI 日报</span>
            <Link to="/research-daily" style={{ fontSize: 13, color: "#2563eb", textDecoration: "none" }}>查看全部 →</Link>
          </h3>
          {daily ? (
            <>
              <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 8 }}>{daily.title}</div>
              <pre style={{ whiteSpace: "pre-wrap", lineHeight: 1.6, fontSize: 13, fontFamily: "-apple-system, sans-serif", color: "#374151", margin: 0, maxHeight: 400, overflow: "auto" }}>
                {daily.content}
              </pre>
            </>
          ) : (
            <div style={{ color: "#9ca3af", padding: "30px 0", textAlign: "center" }}>
              暂无日报（每日 09:35 自动生成）
            </div>
          )}
        </div>

        {/* Quick Links */}
        <div>
          <div className="card" style={{ marginBottom: 18 }}>
            <h3 style={{ marginTop: 0 }}>{'\u{1F680}'} 快速入口</h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              {[
                ["📂 战略文档", "/strategic-docs"],
                ["🧠 LLM 仪表盘", "/llm-providers"],
                ["📚 行业文库", "/knowledge-library"],
                ["👥 联系人", "/contacts"],
                ["⚙ 系统配置", "/sys-config"],
                ["🔬 AI 日报", "/research-daily"],
                ["🏢 公司信息", "/company"],
                ["🧪 和光智成", "/molecules"],
                ["📈 资产", "/stocks"],
                ["🎮 远程控制", "/remote-control"],
              ].map(([label, path]) => (
                <Link key={path} to={path} style={{
                  padding: "12px", borderRadius: 10, border: "1px solid #e5e7eb",
                  background: "#f9fafb", color: "#374151", fontSize: 13,
                  textDecoration: "none", textAlign: "center", transition: "background .1s",
                }}
                  onMouseEnter={e => (e.currentTarget.style.background = "#eff6ff")}
                  onMouseLeave={e => (e.currentTarget.style.background = "#f9fafb")}>
                  {label}
                </Link>
              ))}
            </div>
          </div>

          <div className="card">
            <h3 style={{ marginTop: 0 }}>{'\u{1F4C5}'} 每日同步计划</h3>
            <div style={{ fontSize: 13, lineHeight: 2 }}>
              <div>{'\u{1F4E6}'} <strong>09:00 CST</strong> — 看板全量内容同步（战略/Provider/文库/联系人/配置/备份）</div>
              <div>{'\u{1F52C}'} <strong>09:35 CST</strong> — AI+材料科学每日自动调研报告</div>
              <div>{'\u{1F4EC}'} 以上均推送到企业微信</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
