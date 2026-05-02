import { useState } from 'react'

export default function TestSelfDriving() {
  const [count, setCount] = useState(0)
  return (
    <div style={{ padding: 40 }}>
      <h1>✅ 自我驱动系统测试页面</h1>
      <p>如果你看到这段文字，说明组件加载成功了！</p>
      <button onClick={() => setCount(c => c + 1)}>点击次数: {count}</button>
    </div>
  )
}
