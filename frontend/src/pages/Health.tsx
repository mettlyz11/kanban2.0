import { useState, useEffect } from 'react'
import { Heart, Calendar, FileText } from 'lucide-react'
import type { MedicalExamRecord } from '../types/health'
import { 
  sampleMedicalRecords, 
  examHistoryData
} from '../types/health'
import {
  BMITrendChart,
  BloodPressureChart,
  LipidChart,
  HealthIndicatorCards,
  ExamDataUpload
} from '../components/HealthCharts'

export function Health() {
  const [activeTab, setActiveTab] = useState<'overview' | 'daily' | 'exams' | 'trends'>('overview')
  const [, setSelectedExam] = useState<MedicalExamRecord | null>(null)
  const [hasRealData, setHasRealData] = useState(false)
  const [checkups, setCheckups] = useState<any[]>([])
  const [, setLatestCheckup] = useState<any>(null)
  const [, setLoading] = useState(true)
  const [healthRecords, setHealthRecords] = useState<any[]>([])
  const [hasHealthRecords, setHasHealthRecords] = useState(false)
  
  // 从API获取真实体检数据
  useEffect(() => {
    fetch('/api/health/checkups/latest')
      .then(res => res.json())
      .then(data => {
        if (data.success && data.checkup_count > 0) {
          setCheckups(data.checkups || [])
          setLatestCheckup(data.latest)
          setHasRealData(true)
        }
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to fetch health data:', err)
        setLoading(false)
      })
  }, [])
  
  // 获取日常健康记录
  useEffect(() => {
    fetch('/api/health/records')
      .then(res => res.json())
      .then(data => {
        if (data.success && data.records && data.records.length > 0) {
          setHealthRecords(data.records)
          setHasHealthRecords(true)
        }
      })
      .catch(err => {
        console.error('Failed to fetch health records:', err)
      })
  }, [])
  
  // 最新数据（优先使用真实数据）
  const latestHistory = examHistoryData[examHistoryData.length - 1]
  
  // 健康建议
  const healthTips = [
    '每天至少步行 8000 步',
    '保持 7-8 小时优质睡眠', 
    '每天喝够 2000ml 水',
    '每周运动 3-5 次，每次 30 分钟以上',
    '每工作 1 小时休息 10 分钟',
    '保持心情愉悦，适度减压'
  ]

  return (
    <div className="page-container" style={{ maxWidth: "100%", padding: "0 32px" }}>
      <div className="page-header" style={{ marginBottom: '32px' }}>
        <h2 className="page-title">💪 个人健康管理中心</h2>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            className={`btn ${activeTab === 'overview' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('overview')}
            style={{ padding: '10px 24px' }}
          >
            健康概览
          </button>
          <button
            className={`btn ${activeTab === 'daily' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('daily')}
            style={{ padding: '10px 24px' }}
          >
            日常记录
          </button>
          <button
            className={`btn ${activeTab === 'exams' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('exams')}
            style={{ padding: '10px 24px' }}
          >
            体检记录
          </button>
          <button
            className={`btn ${activeTab === 'trends' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('trends')}
            style={{ padding: '10px 24px' }}
          >
            趋势分析
          </button>
        </div>
      </div>

      {!hasRealData && (
        <ExamDataUpload onDataLoaded={(data) => {
          setHasRealData(true);
          console.log('Data loaded:', data);
        }} />
      )}

      {activeTab === 'overview' && (
        <>
          {/* 健康指标卡片 */}
          <HealthIndicatorCards latest={latestHistory} />

          {/* 主要趋势图 */}
          <div style={{ marginBottom: '24px' }}>
            <BMITrendChart data={examHistoryData.map(d => ({
              date: d.date,
              BMI: d.bmi,
              正常上限: 24,
              正常下限: 18.5
            }))} />
          </div>

          <div style={{ marginBottom: '24px' }}>
            <BloodPressureChart data={examHistoryData.map(d => ({
              date: d.date,
              收缩压: d.systolic,
              舒张压: d.diastolic,
              正常收缩压: 120,
              正常舒张压: 80
            }))} />
          </div>

          {/* 健康改善总结 */}
          <div style={{
            background: 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)',
            borderRadius: '16px',
            padding: '32px',
            marginBottom: '32px'
          }}>
            <h3 style={{ color: '#2e7d32', marginBottom: '20px', fontSize: '1.3rem' }}>
              🎉 健康改善总结 (2020-2025)
            </h3>
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '16px'
            }}>
              {[
                { label: 'BMI', from: '26.61', to: '22.9', status: '正常' },
                { label: '收缩压', from: '155', to: '128', unit: 'mmHg', status: '改善' },
                { label: '舒张压', from: '89', to: '75', unit: 'mmHg', status: '正常' },
                { label: '甘油三酯', from: '1.8', to: '1.2', unit: 'mmol/L', status: '改善' },
              ].map((item, i) => (
                <div key={i} style={{
                  background: 'white',
                  borderRadius: '12px',
                  padding: '20px',
                  textAlign: 'center'
                }}>
                  <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '8px' }}>{item.label}</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#e74c3c', textDecoration: 'line-through' }}>
                    {item.from}
                  </div>
                  <div style={{ fontSize: '2rem', fontWeight: 700, color: '#27ae60' }}>
                    {item.to} <span style={{ fontSize: '0.8rem' }}>{item.unit}</span>
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#27ae60', marginTop: '8px', fontWeight: 600 }}>
                    → {item.status}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 健康建议 */}
          <div style={{
            background: 'white',
            borderRadius: '16px',
            padding: '32px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.08)'
          }}>
            <h3 style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '12px', fontSize: '1.2rem' }}>
              <Heart size={24} color="#e74c3c" />
              每日健康建议
            </h3>
            <div style={{ display: 'grid', gap: '16px' }}>
              {healthTips.map((tip, index) => (
                <div 
                  key={index}
                  style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '16px',
                    padding: '16px 20px',
                    background: '#f8f9fa',
                    borderRadius: '12px',
                    fontSize: '1rem'
                  }}
                >
                  <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    background: '#667eea',
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.9rem',
                    fontWeight: 600
                  }}>
                    {index + 1}
                  </div>
                  <span style={{ color: '#333' }}>{tip}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {activeTab === 'exams' && (
        <>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '24px'
          }}>
            <h3 style={{ fontSize: '1.3rem' }}>体检记录列表</h3>
            <button className="btn btn-primary" style={{ padding: '12px 24px' }}>
              + 添加体检记录
            </button>
          </div>
          
          <div style={{
            background: '#f0f4ff',
            borderRadius: '12px',
            padding: '20px',
            marginBottom: '24px',
            display: 'flex',
            alignItems: 'center',
            gap: '16px'
          }}>
            <FileText size={32} color="#667eea" />
            <div>
              <div style={{ fontWeight: 600, marginBottom: '4px' }}>已发现 6 份体检报告</div>
              <div style={{ fontSize: '0.9rem', color: '#666' }}>
                位于 Files/体检/ 目录，时间跨度 2020-2025 年
              </div>
            </div>
          </div>
          
          {/* 真实体检数据 */}
          {hasRealData && checkups.length > 0 && (
            <div style={{ marginBottom: '32px' }}>
              <h4 style={{ marginBottom: '16px', color: '#667eea' }}>📋 刘宇宙体检报告 (北医三院)</h4>
              <div style={{ display: 'grid', gap: '16px' }}>
                {checkups.map((checkup, index) => (
                  <div 
                    key={index}
                    style={{
                      background: 'linear-gradient(135deg, #f8f9ff 0%, #f0f4ff 100%)',
                      borderRadius: '16px',
                      padding: '24px',
                      boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
                      border: '2px solid #e0e7ff',
                      cursor: 'pointer',
                      transition: 'transform 0.2s, box-shadow 0.2s'
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.transform = 'translateY(-2px)';
                      e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.12)';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = '0 2px 12px rgba(0,0,0,0.06)';
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '1.1rem', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <Calendar size={18} color="#667eea" />
                          {checkup.checkup_date}
                        </div>
                        <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '8px' }}>{checkup.hospital}</div>
                        <div style={{ 
                          fontSize: '0.85rem', 
                          color: '#667eea', 
                          background: '#e0e7ff',
                          padding: '4px 12px',
                          borderRadius: '12px',
                          display: 'inline-block',
                          fontWeight: 500
                        }}>
                          {checkup.checkup_items}
                        </div>
                      </div>
                      <div style={{
                        background: '#e8f5e9',
                        color: '#2e7d32',
                        padding: '8px 16px',
                        borderRadius: '20px',
                        fontSize: '0.9rem',
                        fontWeight: 500
                      }}>
                        ✓ 已归档
                      </div>
                    </div>
                    <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #e0e7ff' }}>
                      <div style={{ fontSize: '0.9rem', color: '#555', lineHeight: 1.6 }}>
                        {checkup.notes}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 原始模拟数据 */}
          <div style={{ display: 'grid', gap: '16px' }}>
            {sampleMedicalRecords.map((exam) => (
              <div 
                key={exam.id} 
                style={{
                  background: 'white',
                  borderRadius: '16px',
                  padding: '24px',
                  boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
                  cursor: 'pointer',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
                onClick={() => setSelectedExam(exam)}
                onMouseEnter={e => {
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.12)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = '0 2px 12px rgba(0,0,0,0.06)';
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: '1.1rem', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Calendar size={18} color="#667eea" />
                    {exam.examDate}
                  </div>
                  <div style={{ fontSize: '0.9rem', color: '#666' }}>{exam.hospital}</div>
                  <div style={{ fontSize: '0.85rem', color: '#999', marginTop: '8px' }}>
                    体重: {exam.basicInfo.weight}kg | BMI: {exam.basicInfo.bmi} | 血压: {exam.basicInfo.bloodPressure}
                  </div>
                </div>
                <div style={{
                  background: exam.abnormalItems?.length === 0 ? '#e8f5e9' : '#ffebee',
                  color: exam.abnormalItems?.length === 0 ? '#2e7d32' : '#c62828',
                  padding: '8px 16px',
                  borderRadius: '20px',
                  fontSize: '0.9rem',
                  fontWeight: 500
                }}>
                  {exam.abnormalItems?.length === 0 ? '✓ 全部正常' : `⚠ ${exam.abnormalItems?.length}项异常`}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {activeTab === 'trends' && (
        <>
          <LipidChart data={examHistoryData.map(d => ({
            date: d.date,
            总胆固醇: d.totalCholesterol,
            甘油三酯: d.triglycerides,
            LDL: d.ldl,
            HDL: d.hdl
          }))} />
        </>
      )}

      {activeTab === 'daily' && (
        <>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '24px'
          }}>
            <h3 style={{ fontSize: '1.3rem' }}>日常健康记录</h3>
            <button className="btn btn-primary" style={{ padding: '12px 24px' }}>
              + 添加记录
            </button>
          </div>

          {!hasHealthRecords ? (
            <div style={{
              background: '#f0f4ff',
              borderRadius: '12px',
              padding: '40px',
              textAlign: 'center'
            }}>
              <div style={{ fontSize: '1.1rem', color: '#666', marginBottom: '16px' }}>
                暂无日常健康记录
              </div>
              <button className="btn btn-primary">
                添加第一条记录
              </button>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: '16px' }}>
              {healthRecords.map((record: any) => (
                <div
                  key={record.id}
                  style={{
                    background: 'white',
                    borderRadius: '16px',
                    padding: '24px',
                    boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
                    gap: '16px',
                    alignItems: 'center'
                  }}
                >
                  <div>
                    <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>日期</div>
                    <div style={{ fontWeight: 600, fontSize: '1rem' }}>{record.record_date}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>体重</div>
                    <div style={{ fontWeight: 600, fontSize: '1.1rem', color: '#667eea' }}>
                      {record.weight} <span style={{ fontSize: '0.8rem' }}>kg</span>
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>睡眠</div>
                    <div style={{ fontWeight: 600 }}>{record.sleep_hours} 小时</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>运动</div>
                    <div style={{ fontWeight: 600 }}>{record.exercise_minutes} 分钟</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>饮水</div>
                    <div style={{ fontWeight: 600 }}>{record.water_intake} ml</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>心情</div>
                    <div style={{ fontSize: '1.2rem' }}>
                      {record.mood >= 8 ? '😊' : record.mood >= 5 ? '😐' : '😔'} {record.mood}/10
                    </div>
                  </div>
                  {record.notes && (
                    <div style={{ gridColumn: '1 / -1', paddingTop: '12px', borderTop: '1px solid #eee' }}>
                      <div style={{ fontSize: '0.85rem', color: '#666' }}>备注</div>
                      <div style={{ color: '#333' }}>{record.notes}</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
