import React, { useState, useEffect } from 'react'

const SPROUT_API = '/api/sprout'

const UserProfile: React.FC = () => {
  const [user, setUser] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState('')

  useEffect(() => {
    loadUser()
  }, [])

  const loadUser = async () => {
    const token = localStorage.getItem('sprout_token')
    if (!token) {
      setLoading(false)
      return
    }
    try {
      const res = await fetch(SPROUT_API + '/auth/user?token=' + token)
      const data = await res.json()
      setUser(data)
      setName(data.name || '')
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  const updateProfile = async () => {
    const token = localStorage.getItem('sprout_token')
    try {
      await fetch(SPROUT_API + '/auth/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, name })
      })
      setEditing(false)
      loadUser()
    } catch (e) {
      console.error(e)
    }
  }

  const logout = () => {
    localStorage.removeItem('sprout_token')
    localStorage.removeItem('sprout_name')
    window.location.href = '/login'
  }

  if (loading) return <div style={{minHeight:'100vh',background:'#0f172a',color:'#e2e8f0',display:'flex',alignItems:'center',justifyContent:'center'}}>加载中...</div>

  return (
    <div style={{minHeight:'100vh',background:'#0f172a',color:'#e2e8f0',padding:'40px 20px'}}>
      <div style={{maxWidth:'600px',margin:'0 auto'}}>
        <h1 style={{fontSize:'28px',fontWeight:700,marginBottom:'32px'}}>👤 个人中心</h1>

        <div style={{background:'#1e293b',borderRadius:'16px',padding:'32px',border:'1px solid #334155',marginBottom:'24px'}}>
          <div style={{display:'flex',alignItems:'center',gap:'20px',marginBottom:'24px'}}>
            <div style={{width:'80px',height:'80px',borderRadius:'50%',background:'linear-gradient(135deg,#22c55e,#3b82f6)',display:'flex',alignItems:'center',justifyContent:'center',fontSize:'32px'}}>
              {user?.name?.[0] || '👤'}
            </div>
            <div>
              {editing ? (
                <input
                  value={name}
                  onChange={e => setName(e.target.value)}
                  style={{background:'#0f172a',border:'1px solid #334155',borderRadius:'8px',padding:'8px 12px',color:'#e2e8f0',fontSize:'18px',fontWeight:600}}
                />
              ) : (
                <div style={{fontSize:'24px',fontWeight:600}}>{user?.name || '未命名用户'}</div>
              )}
              <div style={{fontSize:'14px',color:'#64748b',marginTop:'4px'}}>ID: {user?.id || 'unknown'}</div>
            </div>
          </div>

          {editing ? (
            <div style={{display:'flex',gap:'12px'}}>
              <button onClick={updateProfile} style={{padding:'10px 20px',background:'#22c55e',borderRadius:'8px',border:'none',color:'#fff',fontSize:'14px',fontWeight:600,cursor:'pointer'}}>保存</button>
              <button onClick={() => setEditing(false)} style={{padding:'10px 20px',background:'transparent',border:'1px solid #334155',borderRadius:'8px',color:'#94a3b8',fontSize:'14px',cursor:'pointer'}}>取消</button>
            </div>
          ) : (
            <button onClick={() => setEditing(true)} style={{padding:'10px 20px',background:'#3b82f6',borderRadius:'8px',border:'none',color:'#fff',fontSize:'14px',fontWeight:600,cursor:'pointer'}}>编辑资料</button>
          )}
        </div>

        <div style={{background:'#1e293b',borderRadius:'16px',padding:'24px',border:'1px solid #334155',marginBottom:'24px'}}>
          <h3 style={{fontSize:'18px',fontWeight:600,marginBottom:'16px'}}>📊 统计</h3>
          <div style={{display:'grid',gridTemplateColumns:'repeat(2,1fr)',gap:'16px'}}>
            <div style={{background:'#0f172a',borderRadius:'12px',padding:'16px',textAlign:'center'}}>
              <div style={{fontSize:'28px',fontWeight:700,color:'#22c55e'}}>{user?.garden_count || 0}</div>
              <div style={{fontSize:'12px',color:'#64748b'}}>花园</div>
            </div>
            <div style={{background:'#0f172a',borderRadius:'12px',padding:'16px',textAlign:'center'}}>
              <div style={{fontSize:'28px',fontWeight:700,color:'#3b82f6'}}>{user?.leaf_count || 0}</div>
              <div style={{fontSize:'12px',color:'#64748b'}}>叶子</div>
            </div>
          </div>
        </div>

        <div style={{background:'#1e293b',borderRadius:'16px',padding:'24px',border:'1px solid #334155'}}>
          <h3 style={{fontSize:'18px',fontWeight:600,marginBottom:'16px'}}>⚙️ 设置</h3>
          <button onClick={logout} style={{width:'100%',padding:'12px',background:'#ef4444',borderRadius:'8px',border:'none',color:'#fff',fontSize:'14px',fontWeight:600,cursor:'pointer'}}>退出登录</button>
        </div>
      </div>
    </div>
  )
}

export default UserProfile
