import { useEffect, useState } from 'react'

export default function P049Dashboard() {
  const [data, setData] = useState<any>(null)
  
  useEffect(() => {
    fetch('/api/projects/49').then(r => r.json()).then(setData)
  }, [])
  
  return (
    <div style={{ padding: 24 }}>
      <h1>P049 项目仪表盘</h1>
      <p>项目名称: {data?.name || '加载中...'}</p>
      <p>项目状态: {data?.status || '加载中...'}</p>
    </div>
  )
}
