import { useEffect, useMemo, useState } from "react";

type Contact = {
  id: number; name: string; org: string; title: string;
  department: string; email: string; phone: string;
  wechat: string; company: string; notes: string; status: string;
};

type Profile = { name: string; filename: string; content: string; size: number };

export default function Contacts() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedProfile, setSelectedProfile] = useState<Profile | null>(null);
  const [profileContent, setProfileContent] = useState("");

  useEffect(() => {
    loadContacts();
  }, []);

  function loadContacts(q?: string) {
    setLoading(true);
    setError("");
    const params = q ? "?q=" + encodeURIComponent(q) : "";
    fetch("/api/contacts/list" + params)
      .then(r => r.json())
      .then(d => {
        if (!d.success) { setError(d.error || "加载失败"); return; }
        setContacts(d.contacts || []);
        setProfiles(d.profiles || []);
        setTotal(d.total || 0);
      })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }

  function doSearch() {
    loadContacts(search);
  }

  function openProfile(p: Profile) {
    setSelectedProfile(p);
    setProfileContent("加载中...");
    fetch("/api/contacts/profile?name=" + encodeURIComponent(p.name))
      .then(r => r.json())
      .then(d => setProfileContent(d.success ? d.content : "读取失败"))
      .catch(e => setProfileContent("读取失败: " + String(e)));
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>{'\u{1F465}'} 联系人总览</h1>
        <p>云端联系人数据库 + 本地成员档案，统一搜索查看。</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card"><div className="stat-value">{total}</div><div className="stat-label">联系人</div></div>
        <div className="stat-card"><div className="stat-value">{profiles.length}</div><div className="stat-label">本地档案</div></div>
      </div>

      <div className="card" style={{ margin: "18px 0" }}>
        <div style={{ display: "flex", gap: 10 }}>
          <input value={search} onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === "Enter" && doSearch()}
            placeholder="搜索姓名 / 公司 / 机构..."
            style={{ flex: 1, padding: "10px 14px", borderRadius: 8, border: "1px solid #d1d5db", fontSize: 14 }}
          />
          <button onClick={doSearch}
            style={{ padding: "10px 20px", borderRadius: 8, border: "none", background: "#2563eb", color: "white", cursor: "pointer" }}>
            搜索
          </button>
          {search && <button onClick={() => { setSearch(""); loadContacts(); }}
            style={{ padding: "10px 14px", borderRadius: 8, border: "1px solid #d1d5db", background: "white", cursor: "pointer" }}>
            清除
          </button>}
        </div>
      </div>

      {loading && <div className="card">加载中...</div>}
      {error && <div className="card" style={{ color: "#b91c1c" }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: profiles.length > 0 ? "2fr 1fr" : "1fr", gap: 18, alignItems: "start" }}>
        <div className="card" style={{ overflowX: "auto" }}>
          <h3 style={{ marginTop: 0 }}>联系人列表（{contacts.length} / {total}）</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#f9fafb" }}>
                <th style={th}>姓名</th>
                <th style={th}>机构</th>
                <th style={th}>职位</th>
                <th style={th}>公司</th>
                <th style={th}>邮箱</th>
                <th style={th}>电话</th>
              </tr>
            </thead>
            <tbody>
              {contacts.map(c => (
                <tr key={c.id}>
                  <td style={td}>{c.name}</td>
                  <td style={td}>{c.org || "-"}</td>
                  <td style={td}>{c.title || c.notes || "-"}</td>
                  <td style={td}>{c.company || "-"}</td>
                  <td style={td}>{c.email || "-"}</td>
                  <td style={td}>{c.phone || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {profiles.length > 0 && (
          <div>
            <div className="card" style={{ maxHeight: "40vh", overflow: "auto", marginBottom: 12 }}>
              <h4 style={{ marginTop: 0 }}>本地成员档案</h4>
              {profiles.map(p => (
                <div key={p.name} onClick={() => openProfile(p)}
                  style={{ padding: 10, borderRadius: 8, marginBottom: 8, cursor: "pointer",
                    border: selectedProfile?.name === p.name ? "1px solid #2563eb" : "1px solid #e5e7eb",
                    background: selectedProfile?.name === p.name ? "#eff6ff" : "#fff" }}>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>{p.name}</div>
                  <div style={{ fontSize: 11, color: "#6b7280" }}>{(p.size / 1024).toFixed(0)} KB</div>
                </div>
              ))}
            </div>

            {selectedProfile && (
              <div className="card" style={{ maxHeight: "30vh", overflow: "auto" }}>
                <h4 style={{ margin: 0, marginBottom: 8 }}>{selectedProfile.name} 档案</h4>
                <pre style={{ whiteSpace: "pre-wrap", lineHeight: 1.6, fontFamily: "-apple-system, sans-serif", fontSize: 13, margin: 0 }}>{profileContent}</pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

const th: React.CSSProperties = { textAlign: "left", padding: 10, borderBottom: "1px solid #e5e7eb", whiteSpace: "nowrap" };
const td: React.CSSProperties = { padding: 10, borderBottom: "1px solid #f3f4f6", verticalAlign: "top" };
