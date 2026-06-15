import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'

const SPROUT_API = '/api/sprout'
const PLANS = {
  seed: { name: '种子', price: 0, desc: '免费体验', features: ['1个花园', '基础功能'] },
  growth: { name: '生长', price: 19, desc: '个人版', features: ['5个花园', '自然语言', '导出功能'] },
  bloom: { name: '开花', price: 99, desc: '专业版', features: ['无限花园', '高级场景', '团队协作'] },
  garden: { name: '花园', price: 499, desc: '企业版', features: ['私有化部署', '定制开发', '专属支持'] }
}

const PaymentPage: React.FC = () => {
  const [searchParams] = useSearchParams()
  const [plan, setPlan] = useState(searchParams.get('plan') || 'growth')
  const [order, setOrder] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [qrCode, setQrCode] = useState('')

  useEffect(() => {
    createOrder()
  }, [plan])

  const createOrder = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('sprout_token') || 'guest'
      const res = await fetch(SPROUT_API + '/payment/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_token: token, plan })
      })
      const data = await res.json()
      setOrder(data)
      
      // Generate QR code
      const qrRes = await fetch(SPROUT_API + '/payment/qr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_id: data.order_id })
      })
      const qrData = await qrRes.json()
      if (qrData.qr_data) setQrCode(qrData.qr_data)
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  const currentPlan = PLANS[plan as keyof typeof PLANS]

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: '#e2e8f0', padding: '40px 20px' }}>
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        <h1 style={{ fontSize: '28px', fontWeight: 700, textAlign: 'center', marginBottom: '8px' }}>
          💳 升级你的花园
        </h1>
        <p style={{ textAlign: 'center', color: '#64748b', marginBottom: '32px' }}>
          选择适合你的计划，开始养系统
        </p>

        {/* Plan Selection */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '16px', marginBottom: '32px' }}>
          {Object.entries(PLANS).map(([key, p]) => (
            <div
              key={key}
              onClick={() => setPlan(key)}
              style={{
                padding: '20px',
                borderRadius: '12px',
                border: plan === key ? '2px solid #22c55e' : '1px solid #334155',
                background: plan === key ? '#1e293b' : '#0f172a',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              <div style={{ fontSize: '20px', fontWeight: 600, marginBottom: '4px' }}>{p.name}</div>
              <div style={{ fontSize: '24px', fontWeight: 700, color: '#22c55e' }}>
                ¥{p.price}<span style={{ fontSize: '12px', color: '#64748b' }}>/月</span>
              </div>
              <div style={{ fontSize: '12px', color: '#64748b', marginTop: '8px' }}>{p.desc}</div>
            </div>
          ))}
        </div>

        {/* Payment Section */}
        <div style={{ background: '#1e293b', borderRadius: '16px', padding: '32px', border: '1px solid #334155' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '16px' }}>
            {currentPlan.name}计划 - ¥{currentPlan.price}
          </h2>
          
          <div style={{ marginBottom: '24px' }}>
            {currentPlan.features.map((f, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: '#94a3b8' }}>
                <span style={{ color: '#22c55e' }}>✓</span> {f}
              </div>
            ))}
          </div>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>加载中...</div>
          ) : order ? (
            <div style={{ textAlign: 'center' }}>
              <div style={{ background: '#fff', padding: '20px', borderRadius: '12px', marginBottom: '16px', display: 'inline-block' }}>
                {qrCode ? (
                  <img src={qrCode} alt=支付二维码 style={{ width: '200px', height: '200px' }} />
                ) : (
                  <div style={{ width: '200px', height: '200px', background: '#f1f5f9', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
                    二维码生成中...
                  </div>
                )}
              </div>
              <div style={{ fontSize: '14px', color: '#64748b', marginBottom: '8px' }}>
                订单号: {order.order_id}
              </div>
              <div style={{ fontSize: '12px', color: '#475569' }}>
                请使用微信扫码支付 ¥{order.amount}
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', color: '#64748b' }}>创建订单失败</div>
          )}
        </div>
      </div>
    </div>
  )
}

export default PaymentPage
