import { useEffect, useState } from 'react'

export default function P049ProjectMembers() {
  const [members, setMembers] = useState<any[]>([])
  
  useEffect(() => {
    fetch('/api/projects/49/members')
      .then(r => r.json())
      .then(d => setMembers(d.data || []))
      .catch(() => setMembers([]))
  }, [])
  
  return (
    <div style={{ padding: 24 }}>
      <h1>P049 项目成员</h1>
      <p>管理项目成员和权限</p>
      <div style={{ marginTop: 16 }}>
        <p>成员数量: {members.length}</p>
        {members.length === 0 && <p>暂无成员</p>}
      </div>
    </div>
  )
}
