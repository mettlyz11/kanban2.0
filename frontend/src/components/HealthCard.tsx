import { useState, useEffect } from 'react'
import { Heart, Activity, FileText, Calendar } from 'lucide-react'

interface HealthCheckup {
  checkup_date: string
  hospital: string
  checkup_items: string
  notes: string
}

interface LatestHealth {
  person_name: string
  age: number
  blood_pressure_sys: number
  blood_pressure_dia: number
  heart_rate: number
}

export function HealthCard() {
  const [checkups, setCheckups] = useState<HealthCheckup[]>([])
  const [latest, setLatest] = useState<LatestHealth | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/health/checkups/latest')
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setCheckups(data.checkups || [])
          setLatest(data.latest)
        }
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to fetch health data:', err)
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <div style={{
        background: 'linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%)',
        borderRadius: '16px',
        padding: '24px',
        border: '2px solid #e0e7ff',
        marginBottom: '24px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: '#667eea' }}>
          <Heart size={24} />
          <span>加载健康数据中...</span>
        </div>
      </div>
    )
  }

  if (!latest || checkups.length === 0) {
    return null
  }

  const latestCheckup = checkups[0]

  return (
    <div style={{
      background: 'linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%)',
      borderRadius: '16px',
      padding: '24px',
      border: '2px solid #e0e7ff',
      marginBottom: '24px'
    }}>
      {/* 标题 */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '20px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '44px',
            height: '44px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white'
          }}>
            <Heart size={24} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#333', fontWeight: 600 }}>
              ❤️ 健康状态
            </h3>
            <p style={{ margin: 0, fontSize: '0.85rem', color: '#666' }}>
              {latest.person_name} · {latest.age}岁
            </p>
          </div>
        </div>
        <div style={{
          background: '#e8f5e9',
          color: '#2e7d32',
          padding: '6px 14px',
          borderRadius: '20px',
          fontSize: '0.85rem',
          fontWeight: 500
        }}>
          已同步 {checkups.length} 份报告
        </div>
      </div>

      {/* 关键指标 */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
        gap: '16px',
        marginBottom: '20px'
      }}>
        <div style={{
          background: 'white',
          borderRadius: '12px',
          padding: '16px',
          textAlign: 'center',
          boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
        }}>
          <Activity size={20} color="#667eea" style={{ marginBottom: '8px' }} />
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#333' }}>
            {latest.blood_pressure_sys}/{latest.blood_pressure_dia}
          </div>
          <div style={{ fontSize: '0.8rem', color: '#888' }}>血压 mmHg</div>
        </div>

        <div style={{
          background: 'white',
          borderRadius: '12px',
          padding: '16px',
          textAlign: 'center',
          boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
        }}>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#333', marginBottom: '4px' }}>
            {latest.heart_rate}
          </div>
          <div style={{ fontSize: '0.8rem', color: '#888' }}>心率 次/分</div>
        </div>

        <div style={{
          background: 'white',
          borderRadius: '12px',
          padding: '16px',
          textAlign: 'center',
          boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
        }}>
          <Calendar size={20} color="#667eea" style={{ marginBottom: '8px' }} />
          <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#333' }}>
            {latestCheckup?.checkup_date}
          </div>
          <div style={{ fontSize: '0.8rem', color: '#888' }}>最近体检</div>
        </div>
      </div>

      {/* 最新体检 */}
      {latestCheckup && (
        <div style={{
          background: 'white',
          borderRadius: '12px',
          padding: '16px',
          border: '1px solid #e0e7ff'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
            <FileText size={18} color="#667eea" />
            <span style={{ fontWeight: 600, color: '#333' }}>{latestCheckup.checkup_items}</span>
          </div>
          <p style={{ margin: 0, fontSize: '0.9rem', color: '#555', lineHeight: 1.5 }}>
            {latestCheckup.notes}
          </p>
          <div style={{ marginTop: '10px', fontSize: '0.8rem', color: '#888' }}>
            {latestCheckup.hospital}
          </div>
        </div>
      )}
    </div>
  )
}
