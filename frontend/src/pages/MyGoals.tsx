import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Target, Edit3 } from 'lucide-react';

interface Goal {
  id: string;
  title: string;
  description: string;
  progress: number;
  status: 'todo' | 'progress' | 'done';
  icon: string;
  krs: { text: string; completed: boolean }[];
}

const defaultGoals: Goal[] = [
  {
    id: 't1',
    title: 'T1: 技术精进',
    description: '成为AI+化学计算领域的顶尖技术专家，掌握核心技术栈，建立完整的技术体系和知识产权。',
    progress: 65,
    status: 'progress',
    icon: '🔬',
    krs: [
      { text: 'T109平台开发完成', completed: true },
      { text: 'Pepi数字员工系统上线', completed: true },
      { text: '申请3项核心专利', completed: false },
      { text: '发表2篇顶级论文', completed: false }
    ]
  },
  {
    id: 't2',
    title: 'T2: 事业成就',
    description: '建立"和光智成"科技公司，成为AI化学计算领域的领军企业，服务全球100+科研机构和企业。',
    progress: 40,
    status: 'progress',
    icon: '🚀',
    krs: [
      { text: '公司注册成立', completed: true },
      { text: '完成A轮融资', completed: false },
      { text: '签约10家标杆客户', completed: false },
      { text: '年收入突破1000万', completed: false }
    ]
  },
  {
    id: 't3',
    title: 'T3: 学术影响',
    description: '在AI4Science领域建立学术声誉，发表高影响力论文，成为该领域的意见领袖和标准制定者。',
    progress: 30,
    status: 'progress',
    icon: '📚',
    krs: [
      { text: 'Nature/Science子刊1篇', completed: false },
      { text: '顶级会议论文3篇', completed: false },
      { text: 'H指数达到15', completed: false },
      { text: '受邀国际会议报告', completed: false }
    ]
  },
  {
    id: 't4',
    title: 'T4: 财务增值',
    description: '建立多元化收入结构，实现财务自由，投资组合年收益率15%+，为长期发展提供坚实经济基础。',
    progress: 25,
    status: 'todo',
    icon: '💰',
    krs: [
      { text: '被动收入覆盖生活费', completed: false },
      { text: '投资组合达500万', completed: false },
      { text: '年投资收益15%+', completed: false },
      { text: '建立家族信托', completed: false }
    ]
  },
  {
    id: 't5',
    title: 'T5: 家庭幸福',
    description: '营造和谐幸福的家庭氛围，陪伴家人成长，建立良好的亲子关系，实现工作与生活的平衡。',
    progress: 70,
    status: 'progress',
    icon: '❤️',
    krs: [
      { text: '每周家庭聚餐3次+', completed: true },
      { text: '每年家庭旅行2次', completed: false },
      { text: '子女教育基金准备', completed: false },
      { text: '改善家庭居住环境', completed: false }
    ]
  },
  {
    id: 't6',
    title: 'T6: 社会贡献',
    description: '积极参政议政，推动科技进步政策制定；投身公益事业，用技术回馈社会，建立个人社会影响力。',
    progress: 20,
    status: 'todo',
    icon: '🌍',
    krs: [
      { text: '提交政协提案2份', completed: false },
      { text: '参与行业标准制定', completed: false },
      { text: '技术公益服务100小时', completed: false },
      { text: '培养行业人才10人', completed: false }
    ]
  },
  {
    id: 't7',
    title: 'T7: 身心健康',
    description: '保持规律运动习惯，维持健康体重和体脂率，定期体检，培养冥想等心理健康习惯，确保长期可持续奋斗。',
    progress: 55,
    status: 'progress',
    icon: '💪',
    krs: [
      { text: '每周运动3次+', completed: true },
      { text: 'BMI控制在正常范围', completed: false },
      { text: '每年全面体检', completed: false },
      { text: '学习冥想/瑜伽', completed: false }
    ]
  }
];

const MyGoals: React.FC = () => {
  const [goals, setGoals] = useState<Goal[]>(() => {
    const saved = localStorage.getItem('myLifeGoals');
    return saved ? JSON.parse(saved) : defaultGoals;
  });
  const [editing, setEditing] = useState<string | null>(null);
  const [editText, setEditText] = useState('');

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    localStorage.setItem('myLifeGoals', JSON.stringify(goals));
  }, [goals]);

  const updateProgress = (id: string, progress: number) => {
    setGoals(goals.map(g => g.id === id ? { ...g, progress } : g));
  };

  const toggleKR = (goalId: string, krIndex: number) => {
    setGoals(goals.map(g => {
      if (g.id === goalId) {
        const newKrs = [...g.krs];
        newKrs[krIndex].completed = !newKrs[krIndex].completed;
        return { ...g, krs: newKrs };
      }
      return g;
    }));
  };

  const startEdit = (goal: Goal) => {
    setEditing(goal.id);
    setEditText(goal.description);
  };

  const saveEdit = (id: string) => {
    setGoals(goals.map(g => g.id === id ? { ...g, description: editText } : g));
    setEditing(null);
  };

  const avgProgress = Math.round(goals.reduce((sum, g) => sum + g.progress, 0) / goals.length);
  const completedGoals = goals.filter(g => g.progress >= 100).length;
  const activeGoals = goals.filter(g => g.progress > 0 && g.progress < 100).length;

  return (
    <div className="page-container" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', minHeight: '100vh' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '20px' }}>
        {/* Header */}
        <div style={{ 
          background: 'rgba(255,255,255,0.95)', 
          padding: '20px', 
          borderRadius: '12px', 
          marginBottom: '20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div>
            <Link to="/dashboard" style={{ textDecoration: 'none', color: '#667eea', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <ArrowLeft size={20} />
              返回看板
            </Link>
            <h1 style={{ 
              fontSize: '28px', 
              background: 'linear-gradient(135deg, #ff6b6b, #feca57)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              margin: 0 
            }}>
              🎯 我的人生目标 (T1-T7)
            </h1>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#667eea' }}>{avgProgress}%</div>
            <div style={{ color: '#666', fontSize: '14px' }}>总体进度</div>
          </div>
        </div>

        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px', marginBottom: '30px' }}>
          <div style={{ background: 'rgba(255,255,255,0.95)', padding: '25px', borderRadius: '12px', textAlign: 'center' }}>
            <div style={{ fontSize: '36px', fontWeight: 'bold', color: '#667eea' }}>7</div>
            <div style={{ color: '#666' }}>人生维度</div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.95)', padding: '25px', borderRadius: '12px', textAlign: 'center' }}>
            <div style={{ fontSize: '36px', fontWeight: 'bold', color: '#28a745' }}>{activeGoals}</div>
            <div style={{ color: '#666' }}>进行中</div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.95)', padding: '25px', borderRadius: '12px', textAlign: 'center' }}>
            <div style={{ fontSize: '36px', fontWeight: 'bold', color: '#17a2b8' }}>{completedGoals}</div>
            <div style={{ color: '#666' }}>已完成</div>
          </div>
          <div style={{ background: 'rgba(255,255,255,0.95)', padding: '25px', borderRadius: '12px', textAlign: 'center' }}>
            <div style={{ fontSize: '36px', fontWeight: 'bold', color: '#ffc107' }}>{new Date().toLocaleDateString()}</div>
            <div style={{ color: '#666' }}>最后更新</div>
          </div>
        </div>

        {/* Goals */}
        {goals.map((goal, index) => (
          <div key={goal.id} style={{ 
            background: 'rgba(255,255,255,0.95)', 
            borderRadius: '16px', 
            padding: '25px', 
            marginBottom: '20px',
            borderLeft: `5px solid ${['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22'][index]}`
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '15px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                <div style={{ 
                  width: '50px', 
                  height: '50px', 
                  borderRadius: '50%', 
                  background: ['#ffebee', '#e3f2fd', '#e8f5e9', '#fff3e0', '#f3e5f5', '#e0f2f1', '#ffe0b2'][index],
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '24px'
                }}>
                  {goal.icon}
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: '20px', color: '#333' }}>{goal.title}</h3>
                  <small style={{ color: '#666' }}>
                    {['Technology Excellence', 'Career Achievement', 'Academic Impact', 'Financial Growth', 'Family Happiness', 'Social Contribution', 'Health & Wellness'][index]}
                  </small>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ 
                  padding: '6px 14px', 
                  borderRadius: '20px', 
                  fontSize: '13px', 
                  fontWeight: 600,
                  background: goal.status === 'done' ? '#e8f5e9' : goal.status === 'progress' ? '#e3f2fd' : '#fff3e0',
                  color: goal.status === 'done' ? '#2e7d32' : goal.status === 'progress' ? '#1565c0' : '#e65100'
                }}>
                  {goal.status === 'done' ? '已完成' : goal.status === 'progress' ? '进行中' : '待开始'}
                </span>
                <button 
                  onClick={() => startEdit(goal)}
                  style={{ 
                    background: '#f0f0f0', 
                    border: 'none', 
                    padding: '6px 12px', 
                    borderRadius: '6px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <Edit3 size={16} />
                  编辑
                </button>
              </div>
            </div>

            {editing === goal.id ? (
              <div style={{ marginBottom: '15px' }}>
                <textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '2px solid #667eea', minHeight: '100px', fontFamily: 'inherit' }}
                />
                <div style={{ marginTop: '10px', display: 'flex', gap: '10px' }}>
                  <button 
                    onClick={() => saveEdit(goal.id)}
                    style={{ background: '#28a745', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer' }}
                  >
                    保存
                  </button>
                  <button 
                    onClick={() => setEditing(null)}
                    style={{ background: '#6c757d', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '6px', cursor: 'pointer' }}
                  >
                    取消
                  </button>
                </div>
              </div>
            ) : (
              <p style={{ color: '#555', lineHeight: 1.6, marginBottom: '15px' }}>{goal.description}</p>
            )}

            {/* Progress */}
            <div style={{ marginBottom: '15px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '14px', color: '#666' }}>完成进度</span>
                <span style={{ fontSize: '14px', fontWeight: 600, color: '#667eea' }}>{goal.progress}%</span>
              </div>
              <div style={{ height: '10px', background: '#e0e0e0', borderRadius: '5px', overflow: 'hidden' }}>
                <div style={{ 
                  width: `${goal.progress}%`, 
                  height: '100%', 
                  background: `linear-gradient(90deg, ${['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22'][index]}, ${['#c0392b', '#2980b9', '#27ae60', '#e67e22', '#8e44ad', '#16a085', '#d35400'][index]})`,
                  borderRadius: '5px',
                  transition: 'width 0.5s'
                }} />
              </div>
              <input 
                type="range" 
                min="0" 
                max="100" 
                value={goal.progress} 
                onChange={(e) => updateProgress(goal.id, parseInt(e.target.value))}
                style={{ width: '100%', marginTop: '10px' }}
              />
            </div>

            {/* Key Results */}
            <div style={{ marginTop: '20px', paddingTop: '20px', borderTop: '1px dashed #ddd' }}>
              <h4 style={{ fontSize: '16px', marginBottom: '12px', color: '#333' }}>
                <Target size={18} style={{ verticalAlign: 'middle', marginRight: '8px' }} />
                关键成果 (KR)
              </h4>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {goal.krs.map((kr, i) => (
                  <li key={i} style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '10px', 
                    padding: '10px 0',
                    borderBottom: '1px dashed #eee'
                  }}>
                    <input 
                      type="checkbox" 
                      checked={kr.completed}
                      onChange={() => toggleKR(goal.id, i)}
                      style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                    />
                    <span style={{ 
                      textDecoration: kr.completed ? 'line-through' : 'none',
                      color: kr.completed ? '#999' : '#333'
                    }}>
                      {kr.text}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MyGoals;
