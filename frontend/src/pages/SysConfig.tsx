import { useEffect, useMemo, useState } from "react";

type Config = {
  id: number; config_type: string; config_data: string;
  updated_at: string; dlen: number;
};

const SENSITIVE_TYPES = ["key", "password", "secret", "token", "private"];

function isSensitive(type: string): boolean {
  return SENSITIVE_TYPES.some(k => type.toLowerCase().includes(k));
}

function maskData(val: string): string {
  if (val.length <= 6) return "****";
  return val.slice(0, 2) + "****" + val.slice(-2);
}

function tryPretty(val: string): string {
  try { return JSON.stringify(JSON.parse(val), null, 2).slice(0, 2000); }
  catch { return val.slice(0, 2000); }
}

export default function SysConfig() {
  const [configs, setConfigs] = useState<Config[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showSensitive, setShowSensitive] = useState(false);
  const [selected, setSelected] = useState<Config | null>(null);
  const [groupByType, setGroupByType] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch("/api/system/config-browser")
      .then(r => r.json())
      .then(d => {
        if (!d.success) { setError(d.error || "加载失败"); return; }
        setConfigs(d.configs || []);
        setTotal(d.total || 0);
        if ((d.configs || []).length > 0) setSelected(d.configs[0]);
      })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  // Group by config_type for overview
  const groups = useMemo(() => {
    const g: Record<string, Config[]> = {};
    for (const c of configs) {
      if (!g[c.config_type]) g[c.config_type] = [];
      g[c.config_type].push(c);
    }
    const arr = Object.entries(g).map(([type, items]) => ({
      type, count: items.length, latest: items.sort((a, b) => b.id - a.id)[0],
      totalDataLen: items.reduce((s, i) => s + (i.dlen || 0), 0),
      sensitive: isSensitive(type),
    }));
    arr.sort((a, b) => b.count - a.count);
    return arr;
  }, [configs]);

  const filteredGroups = useMemo(() => {
    if (!search) return groups;
    const q = search.toLowerCase();
    return groups.filter(g => g.type.toLowerCase().includes(q));
  }, [groups, search]);

  function selectConfigType(type: string) {
    const items = configs.filter(c => c.config_type === type);
    const latest = items.sort((a, b) => b.id - a.id)[0];
    if (latest) setSelected(latest);
  }

  function copyToClipboard(val: string) {
    navigator.clipboard?.writeText(val).catch(() => {});
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>{'\u2699\uFE0F'} 系统配置浏览</h1>
        <p>查看 system_configs 表中存储的所有配置项。API Key / 密钥自动遮罩。</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card"><div className="stat-value">{groups.length}</div><div className="stat-label">配置类型</div></div>
        <div className="stat-card"><div className="stat-value">{total}</div><div className="stat-label">配置条目</div></div>
        <div className="stat-card"><div className="stat-value">{groups.filter(g => g.sensitive).length}</div><div className="stat-label">密钥/Token 类</div></div>
      </div>

      <div className="card" style={{ margin: "18px 0" }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="搜索配置类型..."
            style={{ flex: 1, padding: "10px 14px", borderRadius: 8, border: "1px solid #d1d5db", fontSize: 14 }}
          />
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, cursor: "pointer" }}>
            <input type="checkbox" checked={showSensitive} onChange={e => setShowSensitive(e.target.checked)} />
            显示密钥（危险）
          </label>
        </div>
      </div>

      {loading && <div className="card">加载中...</div>}
      {error && <div className="card" style={{ color: "#b91c1c" }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "380px 1fr", gap: 18, alignItems: "start" }}>
        <div className="card" style={{ maxHeight: "78vh", overflow: "auto" }}>
          <h3 style={{ marginTop: 0, marginBottom: 12 }}>配置清单</h3>
          {filteredGroups.map(g => (
            <div key={g.type} onClick={() => selectConfigType(g.type)}
              style={{
                padding: "10px 12px", borderRadius: 10, marginBottom: 8, cursor: "pointer",
                border: selected?.config_type === g.type ? "1px solid #2563eb" : "1px solid #e5e7eb",
                background: selected?.config_type === g.type ? "#eff6ff" : "#fff",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontWeight: 700, fontSize: 13, fontFamily: g.sensitive ? "monospace" : undefined }}>
                  {g.sensitive ? '\u{1F512} ' : ''}{g.type}
                </span>
                <span style={{ fontSize: 11, color: "#6b7280", background: "#f3f4f6", padding: "2px 8px", borderRadius: 999 }}>
                  {g.count}
                </span>
              </div>
              {!g.sensitive && (
                <div style={{ fontSize: 11, color: "#6b7280", marginTop: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {tryPretty(g.latest?.config_data || "").substring(0, 80)}
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="card" style={{ minHeight: "78vh" }}>
          {selected ? (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <div>
                  <h3 style={{ margin: 0, fontFamily: isSensitive(selected.config_type) ? "monospace" : undefined }}>
                    {isSensitive(selected.config_type) ? '\u{1F512} ' : ''}{selected.config_type}
                  </h3>
                  <div style={{ fontSize: 12, color: "#6b7280" }}>
                    ID: {selected.id} {(selected.dlen / 1024).toFixed(1)} KB · 更新: {selected.updated_at || "-"}
                  </div>
                </div>
                <button onClick={() => copyToClipboard(showSensitive ? selected.config_data : "")}
                  style={{ padding: "6px 12px", borderRadius: 8, border: "1px solid #d1d5db", background: "white", cursor: "pointer", fontSize: 12 }}>
                  {isSensitive(selected.config_type) ? "密钥已保护" : "复制"}
                </button>
              </div>
              <pre style={{
                whiteSpace: "pre-wrap", lineHeight: 1.6, fontSize: 12,
                fontFamily: "monospace", color: "#1f2937", margin: 0,
                background: "#f9fafb", padding: 16, borderRadius: 10,
                maxHeight: "65vh", overflow: "auto"
              }}>
                {isSensitive(selected.config_type)
                  ? (showSensitive ? selected.config_data : maskData(selected.config_data) + '\n\n' + '\u26A0\uFE0F 勾选「显示密钥」查看完整内容（危险操作）')
                  : tryPretty(selected.config_data)}
              </pre>
            </>
          ) : (
            <div style={{ color: "#6b7280", textAlign: "center", padding: "40px 0" }}>选择一个配置类型查看详情</div>
          )}
        </div>
      </div>
    </div>
  );
}
