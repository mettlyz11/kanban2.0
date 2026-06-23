import React, { useState } from 'react'
import SdsArchDiagram from '../components/SdsArchDiagram'
import T109ArchDiagram from '../components/arch/T109ArchDiagram';
import DeployArchDiagram from '../components/arch/DeployArchDiagram';
import KanbanArchDiagram from '../components/arch/KanbanArchDiagram';
import SdsSchedulerDiagram from '../components/arch/SdsSchedulerDiagram';
import ActorArchDiagram from '../components/arch/ActorArchDiagram';

const s: Record<string, React.CSSProperties> = {
  page: { background: '#f0f2f5', minHeight: 'calc(100vh - 80px)', color: '#333', fontFamily: 'sans-serif' },
  container: { maxWidth: '1200px', margin: '0 auto', padding: '16px 20px' },
  tabNav: { display: 'flex', gap: '6px', marginBottom: '16px', borderBottom: '2px solid #e0e0e0', overflowX: 'auto', whiteSpace: 'nowrap' as const, WebkitOverflowScrolling: 'touch' },
  stats: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '12px', marginBottom: '20px' },
  statCard: { background: '#fff', padding: '14px', borderRadius: '6px', textAlign: 'center' as const, boxShadow: '0 1px 3px rgba(0,0,0,.08)' },
  grid3: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' },
  card: { background: '#fff', borderRadius: '8px', padding: '16px', marginBottom: '16px', boxShadow: '0 1px 3px rgba(0,0,0,.08)' },
  item: { display: 'flex', alignItems: 'flex-start', padding: '10px 0', borderBottom: '1px solid #f0f0f0' },
  folder: { background: '#f8f9fa', padding: '12px', borderRadius: '6px', fontFamily: 'monospace', fontSize: '12px', lineHeight: '1.6', color: '#333', whiteSpace: 'pre-wrap' },
  arch: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginTop: '12px' },
  flow: { display: 'flex', alignItems: 'center', gap: '8px', margin: '12px 0', fontSize: '12px', flexWrap: 'wrap' as const },
  flowBox: { background: '#e3f2fd', padding: '6px 12px', borderRadius: '4px', color: '#1565c0' },
  badge: (c: string) => ({ display: 'inline-block', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600, background: c === 'green' ? '#e8f5e9' : c === 'blue' ? '#e3f2fd' : '#fff3e0', color: c === 'green' ? '#2e7d32' : c === 'blue' ? '#1565c0' : '#ef6c00' }),
  icon: (bg: string) => ({ width: '32px', height: '32px', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: '12px', fontSize: '14px', background: bg }),
  archItem: { background: '#f8f9fa', padding: '12px', borderRadius: '6px' },
  safety: { background: '#fff3e0', padding: '12px', borderRadius: '6px', marginTop: '12px', fontSize: '12px', color: '#e65100' },
}

const Badge = ({ c, children }: { c: string; children: React.ReactNode }) => <span style={s.badge(c)}>{children}</span>

const Item = ({ icon, bg, title, badge, desc }: { icon: string; bg: string; title: string; badge?: [string, string]; desc: string }) => (
  <div style={s.item}>
    <div style={s.icon(bg)}>{icon}</div>
    <div>
      <div style={{ fontSize: '13px', fontWeight: 600, color: '#333' }}>{title} {badge && <Badge c={badge[0]}>{badge[1]}</Badge>}</div>
      <div style={{ fontSize: '12px', color: '#666', marginTop: '2px' }}>{desc}</div>
    </div>
  </div>
)

const StatsCard = ({ value, label, color }: { value: string; label: string; color?: string }) => (
  <div style={s.statCard}>
    <div style={{ fontSize: '22px', fontWeight: 700, color: color || '#667eea' }}>{value}</div>
    <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>{label}</div>
  </div>
)

const EvolutionTab = () => (
  <>
    <div style={s.stats}>
      <StatsCard value="3,025" label="已应用改进" color="#e53935" />
      <StatsCard value="~498" label="待验证版本" color="#f57c00" />
      <StatsCard value="~731" label="已验证通过" color="#388e3c" />
      <StatsCard value="6" label="头脑风暴策略" />
      <StatsCard value="5" label="研究方法" />
    </div>

    <div style={s.grid3}>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🎯 8种进化模式</h3>
        <Item icon="1" bg="#e8f5e9" title="meta_evolve" badge={['green', 'active']} desc="元进化：STD-EVAL评分驱动自我优化" />
        <Item icon="2" bg="#e3f2fd" title="std_eval" badge={['blue', 'cycle']} desc="标准评估：13项测试任务周期评分" />
        <Item icon="3" bg="#fff3e0" title="type_fix" badge={['orange', 'batch']} desc="类型修复：批量验证20项/批次" />
        <Item icon="4" bg="#fce4ec" title="brainstorm_v2" badge={['green', '6策略']} desc="头脑风暴V2：SCAMPER/六顶思考帽等" />
        <Item icon="5" bg="#f3e5f5" title="shadow_validate" badge={['blue', '并行']} desc="影子验证：新旧版本并行对比测试" />
        <Item icon="6" bg="#e0f2f1" title="multi_model_vote" badge={['green', '3模型']} desc="多模型投票：Kimi/Ark/DeepSeek共识" />
        <Item icon="7" bg="#fff8e1" title="improvement_learn" badge={['orange', 'RL']} desc="强化学习：成功率预测与权重调整" />
        <Item icon="8" bg="#e8eaf6" title="root_cause_analyze" badge={['blue', '5Whys']} desc="根因分析：深度问题定位与置信度评分" />
      </div>

      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🧠 6种头脑风暴策略</h3>
        <Item icon="S" bg="#e8f5e9" title="SCAMPER" badge={['green', '7角度']} desc="替代/组合/适应/修改/用途/消除/反转" />
        <Item icon="6H" bg="#e3f2fd" title="Six Thinking Hats" badge={['blue', '并行']} desc="白红黑白黄绿蓝六角度并行思考" />
        <Item icon="R" bg="#fff3e0" title="Reverse" badge={['orange', '逆向']} desc="先想最坏情况，再反转得最优解" />
        <Item icon="W" bg="#fce4ec" title="SWOT" badge={['green', '四象限']} desc="优势/劣势/机会/威胁全面分析" />
        <Item icon="★" bg="#f3e5f5" title="Starbursting" badge={['blue', '6W']} desc="Who/What/When/Where/Why/How提问" />
        <Item icon="M" bg="#e0f2f1" title="Mindmap" badge={['green', '发散']} desc="中心主题向6个方向发散思考" />
      </div>

      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>📊 5种研究方法</h3>
        <Item icon="A/B" bg="#e8f5e9" title="A/B Testing" badge={['green', '对比']} desc="前后对比实验，量化改进效果" />
        <Item icon="📈" bg="#e3f2fd" title="Longitudinal" badge={['blue', '30天']} desc="长期追踪，观察改进趋势变化" />
        <Item icon="∑" bg="#fff3e0" title="Meta Analysis" badge={['orange', '3000+']} desc="聚合3000+改进数据，发现统计规律" />
        <Item icon="🔍" bg="#fce4ec" title="Pattern Mining" badge={['green', '自动']} desc="自动发现成功/失败模式，提取经验" />
        <Item icon="📋" bg="#f3e5f5" title="Case Study" badge={['blue', '深度']} desc="单个改进深度分析，提取详细洞察" />
      </div>
    </div>

    <h4 style={{ fontSize: '16px', fontWeight: 600, color: '#333', margin: '20px 0 12px' }}>🏗️ 系统架构</h4>
    
    {/* SDS架构图 */}
    <div style={{ background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '16px', marginBottom: '20px', textAlign: 'center' }}>
      <SdsArchDiagram style={{ maxWidth: '1000px' }} />
      <p style={{ fontSize: '12px', color: '#666', marginTop: '12px', textAlign: 'left' }}>
        <b>SDS 自我驱动系统架构</b> — 展示从用户触发到任务完成的完整数据流。
        核心处理层包含任务分析、生成、守卫、调度、验证五个阶段，
        通过 LLM Client 统一调用大模型，由 Subagent Executor 执行子代理任务。
      </p>
    </div>
    
    <div style={s.arch}>
      <div style={s.archItem}>
        <div style={{ fontSize: '13px', fontWeight: 600, color: '#333', marginBottom: '8px' }}>🎯 进化控制层</div>
        <div style={{ fontSize: '12px', color: '#666', lineHeight: '1.8' }}>
          evolution_daemon.py (894行)<br />
          orchestrator.py (409行)<br />
          evolib/ (11模块 · 2,300行)
        </div>
      </div>
      <div style={s.archItem}>
        <div style={{ fontSize: '13px', fontWeight: 600, color: '#333', marginBottom: '8px' }}>🔬 精准改进系统</div>
        <div style={{ fontSize: '12px', color: '#666', lineHeight: '1.8' }}>
          根因分析 → 头脑风暴<br />
          依赖分析 → 多模型投票<br />
          影子验证 → 强化学习
        </div>
      </div>
      <div style={s.archItem}>
        <div style={{ fontSize: '13px', fontWeight: 600, color: '#333', marginBottom: '8px' }}>🎭 Actor通道</div>
        <div style={{ fontSize: '12px', color: '#666', lineHeight: '1.8' }}>
          HTTP轮询/WebSocket<br />
          自动策略选择 (WebSocket 9.99分)<br />
          质量优化器持续调优
        </div>
      </div>
    </div>

    <div style={s.flow}>
      <div style={s.flowBox}>STD-EVAL评分</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>头脑风暴V2</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>依赖分析</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>多模型投票</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>影子验证</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>强化学习</div>
    </div>

    <div style={s.safety}>
      <b>4层安全保护</b>：meta_evolver声明 + applier前缀拦截 + auto_evolver保护列表 + communication_strategies限制
    </div>

    <h4 style={{ fontSize: '16px', fontWeight: 600, color: '#333', margin: '20px 0 12px' }}>五、文件结构</h4>
    <p style={{ fontSize: '13px', color: '#666', lineHeight: 1.6, marginBottom: '12px' }}>
      <b>图例:</b> <span style={{color:'#e53935'}}>🔴 不可修改</span> · <span style={{color:'#388e3c'}}>🟢 可修改(进化目标)</span> · <span style={{color:'#f57c00'}}>🟠 镜像代码(可被进化)</span>
    </p>
    <div style={s.folder}>
{`sds_evolution/
🔴 进化控制系统 — 控制进化过程，不可被自己修改
├── 🔴 evolution_daemon.py          主进程，控制整个进化流程 (894行)
├── 🔴 orchestrator.py              任务编排器，协调进化各阶段 (409行)
├── 🔴 run.py                       启动脚本，初始化进化系统 (200行)
├── 🔴 watchdog.py                  看门狗进程，监控系统健康 (68行)
├── 🔴 evolib/                      进化模块库 (11文件 · 2,300行)
│   ├── brainstorm_strategies/    6种头脑风暴策略 (642行)
│   ├── brainstormer_v2.py        多策略头脑风暴引擎V2 (189行)
│   ├── root_cause_analyzer.py    根因分析器，5Whys深度分析 (205行)
│   ├── code_dependency_analyzer.py 代码依赖分析器 (254行)
│   ├── multi_model_voter.py      多模型投票器，3模型交叉验证 (228行)
│   ├── shadow_validator.py       影子验证器，并行测试新旧代码 (259行)
│   ├── improvement_learner.py    强化学习模块 (292行)
│   ├── actor_quality_optimizer.py 质量优化器 (261行)
│   ├── auto_evolver.py           自动进化引擎，每10分钟进化 (394行)
│   ├── research_methods/         5种科学研究方法 (868行)
│   ├── mirror.py                 镜像管理器 (241行)
│   ├── applier.py                改进应用器 (397行)
│   ├── evaluator.py              评估器 (500行)
│   └── meta_evolver.py           元进化引擎 (606行)
├── 🔴 core/                       任务核心模块 (2文件 · 61行)
├── 🔴 agent_runtime/              代理运行时框架
├── 🔴 agent_framework/            代理框架基础设施
└── 🔴 SAFETY.md                   安全规则文档 (38行)
⚪ 配置数据 — 人工维护
├── config/                        进化配置目录 (353行)
├── std_tests/                     标准测试集 (52文件 · 3,326行)
├── mirrors/mirror_a/              镜像测试配置
├── scripts/mirror_runner.py       镜像运行脚本 (15行)
└── tools/mirror_resilience_drill.py 韧性演练工具 (9行)
🟠 镜像SDS — 实际进化目标
└── snapshots/evo_mirror_1_*/      镜像SDS快照 (1,217文件 · 99,885行)
    ├── scheduler/                 任务调度器 (37文件 · 2,700行)
    ├── executor/                  任务执行器 (4文件 · 152行)
    ├── evolution/                 SDS自身进化模块 (6文件 · 315行)
    ├── subagent_executor/         子代理执行器 (2文件 · 29行)
    ├── std_eval/                  标准评估模块 (7文件 · 191行)
    ├── core/                      核心模块 (62文件 · 3,409行)
    ├── evolution_daemon.py        SDS主进程 (281行)
    └── main.py                    程序入口 (16行)
💡 命名规则: evo_mirror_{镜像ID}_v{时间戳}
📊 总代码量: 27,393行 (进化体系) + 99,885行 (镜像SDS) = 127,278行`}
    </div>
  </>
)


const T109Tab = () => (
  <>
    <div style={s.stats}>
      <StatsCard value="v4.0.0" label="当前版本" color="#1565c0" />
      <StatsCard value="64天" label="运行时间" color="#2e7d32" />
      <StatsCard value="2" label="Celery Workers" color="#e53935" />
      <StatsCard value="1" label="后端API实例" />
      <StatsCard value="2" label="服务器节点" />
    </div>

    <div style={s.grid3}>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🧪 核心能力</h3>
        <Item icon="⚛" bg="#e8f5e9" title="过渡态AI预测" badge={['green', '核心']} desc="ML模型直接预测化学反应过渡态几何结构" />
        <Item icon="🔬" bg="#e3f2fd" title="多基组计算" badge={['blue', '优化']} desc="多基组计算策略自动选择与任务分发" />
        <Item icon="🔄" bg="#fff3e0" title="反应路径搜索" badge={['orange', 'NEB']} desc="NEB + CI-NEB 最小能量路径自动搜索" />
        <Item icon="🧠" bg="#fce4ec" title="Hermes子代理" badge={['green', '训练中']} desc="过渡态寻找专用AI Agent 持续训练" />
        <Item icon="📊" bg="#f3e5f5" title="数据库化" badge={['blue', '4.0']} desc="MySQL持久化 + 计算结果自动归档" />
      </div>

      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>📦 技术栈</h3>
        <Item icon="🐍" bg="#e8f5e9" title="Python 3.9" badge={['green', 't109 env']} desc="Miniconda3 独立环境，/opt/miniconda3/envs/t109" />
        <Item icon="⚡" bg="#e3f2fd" title="Celery" badge={['blue', '2 workers']} desc="异步任务队列，c=2，qchem_tasks 模块" />
        <Item icon="🗄️" bg="#fff3e0" title="MySQL" badge={['orange', '3306']} desc="本地 MySQL，数据库持久化存储计算结果" />
        <Item icon="🌐" bg="#fce4ec" title="Flask API" badge={['green', '8000']} desc="simple_db_api.py，RESTful + 数据库集成" />
        <Item icon="⚙️" bg="#f3e5f5" title="Supervisor" badge={['blue', '守护']} desc="t109-api + t109-celery 自动重启守护" />
      </div>

      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>📋 关键任务</h3>
        <Item icon="🛡️" bg="#e8f5e9" title="IP护城河建设" badge={['green', '#1571']} desc="T109知识产权布局，专利+技术秘密+监控" />
        <Item icon="🎯" bg="#e3f2fd" title="Hermes子代理训练" badge={['blue', '#1573']} desc="ML过渡态预测对标世界领先水平" />
        <Item icon="🏗️" bg="#fff3e0" title="平台发布" badge={['orange', '#284']} desc="T3.1.1 里程碑，T109正式发布" />
        <Item icon="📋" bg="#fce4ec" title="域名备案" badge={['red', '#348']} desc="Critical级，T109合法运营必要条件" />
        <Item icon="🔬" bg="#f3e5f5" title="己二腈催化剂" badge={['blue', '进口替代']} desc="T109核心验证项目，催化剂国产化替代" />
      </div>
    </div>

    <h4 style={{ fontSize: '16px', fontWeight: 600, color: '#333', margin: '20px 0 12px' }}>🏗️ 系统架构图</h4>
    <div style={{ background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '10px', marginBottom: '12px', textAlign: 'center' }}>
      <T109ArchDiagram />
    </div>

    <div style={s.flow}>
      <div style={s.flowBox}>用户请求</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>Flask API (:8000)</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>Celery Workers</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>PySCF计算</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>MySQL持久化</div>
    </div>

    <h4 style={{ fontSize: '16px', fontWeight: 600, color: '#333', margin: '20px 0 12px' }}>📂 文件结构</h4>
    <div style={s.folder}>
{`/opt/T109/
├── simple_db_api.py        Flask API + DB集成 (5,720行)
├── pyscf_db_api.py         PySCF量子化学API (6,725行)
├── pyscf_api.py            PySCF原始API (4,018行)
├── simple_async_api.py     异步API (1,478行)
├── qchem_tasks.py          Celery任务定义 (3,555行)
├── tasks.py                任务调度 (3,569行)
├── celery_app.py           Celery应用 (495行)
├── celery_config.py        Celery配置 (399行)
├── real_calculation.py     真实计算接口 (2,571行)
├── run_task.py             任务运行入口 (228行)
├── simple_api.py           Simple API (1,208行)
├── final_async_api.py      最终异步API (2,184行)
├── async_api.py            异步API (2,861行)
├── main.py                 程序入口 (103行)
├── t109/                   T109核心模块
├── backend/                Django后端模块 (10个目录)
├── backend_api/            后端API模块 (6个目录)
├── tests/                  测试目录 (11个目录)
/opt/t109-frontend/
├── dist/                   前端构建输出
├── src/                    源码
├── node_modules/           依赖 (160个目录)
└── package.json            npm项目配置
🔗 supervisor: t109-api | t109-celery
🔗 nginx: proxy /api/ → 127.0.0.1:8000`}
    </div>
  </>
)



const SdsTab = () => (
  <>
    <div style={s.stats}>
      <StatsCard value="9,554行" label="后端路由总量" color="#1565c0" />
      <StatsCard value="35+" label="API路由文件" color="#2e7d32" />
      <StatsCard value="10+" label="Cron任务" color="#e53935" />
      <StatsCard value="3级" label="优先级分级" />
      <StatsCard value="连续" label="调度模式" />
    </div>
    <div style={s.grid3}>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🎯 调度核心</h3>
        <Item icon="1" bg="#e8f5e9" title="任务调度器" badge={['green', 'orchestrator']} desc="协调子代理执行、依赖链管理、重试逻辑" />
        <Item icon="2" bg="#e3f2fd" title="子代理执行器" badge={['blue', 'isolated']} desc="每个子代理独立会话，互不干扰" />
        <Item icon="3" bg="#fff3e0" title="标准评估" badge={['orange', 'std_eval']} desc="13项测试任务周期评分驱动优化" />
        <Item icon="4" bg="#fce4ec" title="审核巡逻" badge={['red', 'audit']} desc="自动审核 pending 任务状态一致性" />
        <Item icon="5" bg="#f3e5f5" title="依赖链巡检" badge={['blue', 'chain']} desc="上下游依赖自动激活/阻塞处理" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>📦 后端路由</h3>
        <Item icon="📋" bg="#e8f5e9" title="tasks_api.py" badge={['green', '972行']} desc="任务CRUD + 状态管理 + 批量操作" />
        <Item icon="🧬" bg="#e3f2fd" title="cron_api.py" badge={['blue', 'cron']} desc="定时任务调度 + 执行记录" />
        <Item icon="📊" bg="#fff3e0" title="cockpit.py" badge={['orange', '驾驶舱']} desc="系统仪表盘聚合数据API" />
        <Item icon="🕵️" bg="#fce4ec" title="audit_api.py" badge={['green', '审计']} desc="操作日志追踪 + 审核流水" />
        <Item icon="🤖" bg="#f3e5f5" title="brain_chat_api.py" badge={['blue', 'AI']} desc="AI对话 + 头脑风暴API" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>⚙️ 调度流程</h3>
        <Item icon="🔄" bg="#e8f5e9" title="轮询" badge={['green', '10s']} desc="调度器每10秒扫描pending任务" />
        <Item icon="🎯" bg="#e3f2fd" title="优先级排序" badge={['blue', 'P1→P9']} desc="按优先级+创建时间排序调度" />
        <Item icon="🔗" bg="#fff3e0" title="依赖检查" badge={['orange', 'block']} desc="前置任务未完成自动跳过" />
        <Item icon="⚡" bg="#fce4ec" title="子代理分发" badge={['green', 'isolated']} desc="spawn独立会话执行任务" />
        <Item icon="📝" bg="#f3e5f5" title="结果回写" badge={['blue', 'DB']} desc="执行日志+结果摘要自动入库" />
      </div>
    </div>
    <h4 style={{ fontSize: '16px', fontWeight: 600, color: '#333', margin: '20px 0 12px' }}>🏗️ 调度架构图</h4>
    <div style={{ background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '10px', marginBottom: '12px', textAlign: 'center' }}>
      <SdsSchedulerDiagram />
    </div>
    <div style={s.flow}>
      <div style={s.flowBox}>扫描pending</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>优先排序</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>依赖检查</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>子代理spawn</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>执行+审计</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>DB入库</div>
    </div>
  </>
)


const SdsArchTab = () => (
  <>
    <div style={s.stats}>
      <StatsCard value="5阶段" label="核心处理层" color="#1565c0" />
      <StatsCard value="300s" label="调度周期" color="#2e7d32" />
      <StatsCard value="3600s" label="分析周期" color="#e53935" />
      <StatsCard value="9Provider" label="LLM Fallback" />
      <StatsCard value="64模型" label="可用模型数" />
    </div>
    
    {/* SDS架构图 */}
    <div style={{ background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '10px', marginBottom: '10px', textAlign: 'center' }}>
      <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#333', marginBottom: '8px', textAlign: 'left' }}>🏗️ SDS 自我驱动系统架构图</h3>
      <SdsArchDiagram style={{ maxWidth: '1000px' }} />
      <div style={{ background: '#f8f9fa', padding: '8px', borderRadius: '4px', marginTop: '8px', textAlign: 'left' }}>
        <h4 style={{ fontSize: '13px', fontWeight: 600, color: '#333', marginBottom: '6px' }}>📋 架构说明</h4>
        <p style={{ fontSize: '12px', color: '#666', lineHeight: '1.5', marginBottom: '6px' }}>
          <b>SDS（Self-Driving System）自我驱动系统</b>是一个全自动化的任务调度与执行平台。
          系统采用分层架构设计，从用户交互到任务执行形成完整闭环。
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '6px', marginTop: '6px' }}>
          <div style={{ background: '#e3f2fd', padding: '8px', borderRadius: '4px' }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#1565c0', marginBottom: '6px' }}>👤 用户层</div>
            <div style={{ fontSize: '11px', color: '#666' }}>用户触发查询，与系统交互</div>
          </div>
          <div style={{ background: '#e8f5e9', padding: '12px', borderRadius: '6px' }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#2e7d32', marginBottom: '6px' }}>🎯 主循环层</div>
            <div style={{ fontSize: '11px', color: '#666' }}>sds_main.py 每5分钟执行完整周期</div>
          </div>
          <div style={{ background: '#fff3e0', padding: '12px', borderRadius: '6px' }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#ef6c00', marginBottom: '6px' }}>⚙️ 核心处理层</div>
            <div style={{ fontSize: '11px', color: '#666' }}>分析→生成→守卫→调度→验证</div>
          </div>
          <div style={{ background: '#fce4ec', padding: '12px', borderRadius: '6px' }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#c2185b', marginBottom: '6px' }}>🤖 执行层</div>
            <div style={{ fontSize: '11px', color: '#666' }}>LLM Client + Subagent Executor</div>
          </div>
          <div style={{ background: '#f3e5f5', padding: '12px', borderRadius: '6px' }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#7b1fa2', marginBottom: '6px' }}>💾 数据层</div>
            <div style={{ fontSize: '11px', color: '#666' }}>看板数据库 + 配置中心 + 仪表盘</div>
          </div>
        </div>
      </div>
    </div>
    
    {/* 数据流说明 */}
    <div style={s.grid3}>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🔵 主数据流</h3>
        <Item icon="1" bg="#e3f2fd" title="任务生成" desc="AutoTaskGenerator 调用 LLM 生成推荐任务" />
        <Item icon="2" bg="#e8f5e9" title="守卫检查" desc="Guard V48 三重保障验证任务合法性" />
        <Item icon="3" bg="#fff3e0" title="子代理执行" desc="SubagentScheduler 分配任务给子代理" />
        <Item icon="4" bg="#fce4ec" title="结果验证" desc="ResultCollector 验证执行结果质量" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🟠 控制/触发</h3>
        <Item icon="⏱️" bg="#e3f2fd" title="每300秒" desc="调度器 + 验证器 + 健康监控执行" />
        <Item icon="⏰" bg="#e8f5e9" title="每3600秒" desc="任务分析 + 任务生成执行" />
        <Item icon="🔄" bg="#fff3e0" title="每周期" desc="守卫检查 + 预防层扫描" />
        <Item icon="📊" bg="#fce4ec" title="仪表盘更新" desc="可观测性页面实时更新" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🟣 LLM调用链</h3>
        <Item icon="1" bg="#e3f2fd" title="Primary" desc="deepseek-v4-flash 主模型" />
        <Item icon="2" bg="#e8f5e9" title="Fallback 1-2" desc="alicodingplan / alitokenplan" />
        <Item icon="3" bg="#fff3e0" title="Fallback 3-4" desc="kimicode / huoshanCoding" />
        <Item icon="4" bg="#fce4ec" title="总计" desc="9 Provider / 64 模型" />
      </div>
    </div>
    
    {/* 图例 */}
    <div style={{ background: '#fff', padding: '8px', borderRadius: '6px', marginTop: '8px', border: '1px solid #e0e0e0' }}>
      <h4 style={{ fontSize: '12px', fontWeight: 600, color: '#333', marginBottom: '6px' }}>📊 图例说明</h4>
      <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', fontSize: '12px', color: '#666' }}>
        <span><span style={{ color: '#2563eb' }}>━━</span> 主数据流</span>
        <span><span style={{ color: '#ea580c' }}>━━</span> 控制/触发</span>
        <span><span style={{ color: '#059669' }}>━━</span> 数据读取</span>
        <span><span style={{ color: '#059669', textDecoration: 'line-through' }}>━━</span> 数据写入</span>
        <span><span style={{ color: '#7c3aed' }}>━━</span> LLM调用</span>
        <span><span style={{ color: '#6b7280' }}>- -</span> 异步事件</span>
      </div>
    </div>
  </>
)

const ActorTab = () => (
  <>
    <div style={s.stats}>
      <StatsCard value="2通道" label="通信模式" color="#1565c0" />
      <StatsCard value="9.99分" label="WebSocket评分" color="#2e7d32" />
      <StatsCard value="15s" label="心跳间隔" color="#e53935" />
      <StatsCard value="100%" label="在线用户追踪" />
      <StatsCard value="实时" label="同步模式" />
    </div>
    <div style={s.grid3}>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🎭 双通道架构</h3>
        <Item icon="🌐" bg="#e8f5e9" title="HTTP轮询" badge={['green', '兼容']} desc="传统请求/响应模式，通用性最强" />
        <Item icon="🔌" bg="#e3f2fd" title="WebSocket" badge={['blue', '9.99分']} desc="Socket.IO双向通信，实时推送" />
        <Item icon="⚡" bg="#fff3e0" title="自动策略选择" badge={['orange', '智能']} desc="根据网络条件自动选择最优通道" />
        <Item icon="🔄" bg="#fce4ec" title="质量优化器" badge={['green', '持续']} desc="Actor质量评分与自动调优" />
        <Item icon="🧹" bg="#f3e5f5" title="僵尸锁清理" badge={['blue', '维护']} desc="自动清理过期死锁，防止阻塞" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>📦 实时能力</h3>
        <Item icon="👤" bg="#e8f5e9" title="在线用户" badge={['green', '实时']} desc="用户上下线实时通知与列表同步" />
        <Item icon="📝" bg="#e3f2fd" title="任务事件" badge={['blue', '推送']} desc="task_created/updated/deleted 实时推送" />
        <Item icon="🔒" bg="#fff3e0" title="编辑锁" badge={['orange', '协作']} desc="lock_request/release 防冲突编辑" />
        <Item icon="💓" bg="#fce4ec" title="心跳监控" badge={['green', '30s']} desc="30秒心跳，60秒超时自动清理" />
        <Item icon="🏠" bg="#f3e5f5" title="项目房间" badge={['blue', '分组']} desc="按项目分组订阅，精准推送" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>📂 源码结构</h3>
        <Item icon="🔧" bg="#e8f5e9" title="socket.ts" badge={['green', '前端']} desc="SocketIOManager 类，连接/心跳/事件管理" />
        <Item icon="🔌" bg="#e3f2fd" title="websocket/index.py" badge={['blue', '后端']} desc="SocketIO初始化 + eventlet async_mode" />
        <Item icon="🔐" bg="#fff3e0" title="auth.py" badge={['orange', '鉴权']} desc="WebSocket连接鉴权" />
        <Item icon="💓" bg="#fce4ec" title="heartbeat.py" badge={['green', '30s']} desc="心跳监控，自动清理断连用户" />
        <Item icon="📡" bg="#f3e5f5" title="events.py" badge={['blue', '事件']} desc="所有事件处理器 (12+事件类型)" />
      </div>
    </div>
    <h4 style={{ fontSize: '16px', fontWeight: 600, color: '#333', margin: '20px 0 12px' }}>🏗️ 通道架构图</h4>
    <div style={{ background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '10px', marginBottom: '12px', textAlign: 'center' }}>
      <ActorArchDiagram />
    </div>
    <div style={s.flow}>
      <div style={s.flowBox}>SocketIO init</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>Auth鉴权</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>事件注册</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>心跳+监控</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>实时推送</div>
    </div>
  </>
)

const MonitorTab = () => (
  <>
    <div style={s.stats}>
      <StatsCard value="4个" label="感知监听器" color="#1565c0" />
      <StatsCard value="8765" label="WebSocket端口" color="#2e7d32" />
      <StatsCard value="30s" label="心跳间隔" color="#e53935" />
      <StatsCard value="60s" label="超时阈值" />
      <StatsCard value="90s" label="心跳超时" />
    </div>
    <div style={s.grid3}>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🎯 PerceptionAgent</h3>
        <Item icon="📝" bg="#e8f5e9" title="LogListener" badge={['green', '日志']} desc="系统日志实时监控与异常检测" />
        <Item icon="🚨" bg="#e3f2fd" title="ErrorListener" badge={['blue', '错误']} desc="运行时错误捕获与告警分级" />
        <Item icon="📊" bg="#fff3e0" title="MetricListener" badge={['orange', '指标']} desc="性能指标采集(P99/QPS/错误率)" />
        <Item icon="🔍" bg="#fce4ec" title="BehaviorListener" badge={['red', '行为']} desc="异常行为模式检测与标记" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>📡 监控中继</h3>
        <Item icon="🔄" bg="#e8f5e9" title="monitor_relay.py" badge={['green', '中继']} desc="系统指标WebSocket中继服务(8765)" />
        <Item icon="🌐" bg="#e3f2fd" title="nginx代理" badge={['blue', '/monitor/']} desc="wss://kanbanyun.com/monitor/ → 8765" />
        <Item icon="🖥️" bg="#fff3e0" title="SDS控制台" badge={['orange', '/sds-console']} desc="可视化监控面板，WS实时数据刷新" />
        <Item icon="📊" bg="#fce4ec" title="系统页面" badge={['green', '/system']} desc="进程/CPU/内存/磁盘实时状态" />
        <Item icon="🔐" bg="#f3e5f5" title="健康检查" badge={['blue', '/api/health']} desc="系统健康端点+checkups详细状态" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>⚙️ 监控架构</h3>
        <Item icon="🏗️" bg="#e8f5e9" title="Gunicorn" badge={['green', '8086']} desc="kanban-api.service (4 workers, eventlet)" />
        <Item icon="🔄" bg="#e3f2fd" title="SocketIO" badge={['blue', '8085']} desc="kanban-backend.service (eventlet, 1 worker)" />
        <Item icon="🔁" bg="#fff3e0" title="心跳监控" badge={['orange', '30s']} desc="间隔30s，超时90s自动清理" />
        <Item icon="🕒" bg="#fce4ec" title="自动重启" badge={['green', '5s']} desc="RestartSec=5，失败秒级恢复" />
        <Item icon="📋" bg="#f3e5f5" title="事件系统" badge={['blue', '系统']} desc="SystemEventHandler 事件生命周期管理" />
      </div>
    </div>
  </>
)

const DataTab = () => (
  <>
    <div style={s.stats}>
      <StatsCard value="MySQL" label="数据库引擎" color="#1565c0" />
      <StatsCard value="RDS" label="云数据库" color="#2e7d32" />
      <StatsCard value="9+步" label="同步流水线" color="#e53935" />
      <StatsCard value="242条" label="系统配置" />
      <StatsCard value="360+" label="联系人" />
    </div>
    <div style={s.grid3}>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🗄️ 核心表</h3>
        <Item icon="📋" bg="#e8f5e9" title="tasks" badge={['green', '主表']} desc="任务: id/title/status/details/priority/audit" />
        <Item icon="📂" bg="#e3f2fd" title="projects" badge={['blue', '项目']} desc="项目: name/summary/stats/deadline" />
        <Item icon="🏷️" bg="#fff3e0" title="task_categories" badge={['orange', '分类']} desc="任务分类: id/name/description" />
        <Item icon="📝" bg="#fce4ec" title="execution_logs" badge={['green', '日志']} desc="执行日志: task_id/log_entry/created_at" />
        <Item icon="🔧" bg="#f3e5f5" title="system_configs" badge={['blue', '配置']} desc="全局配置: LLM/服务器/系统参数" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🔄 同步流水线</h3>
        <Item icon="1" bg="#e8f5e9" title="LLM上下文" badge={['green', '每日']} desc="LLM全局上下文同步到system_configs" />
        <Item icon="2" bg="#e3f2fd" title="文件索引" badge={['blue', '每日']} desc="本地文件索引 → 后端local_files_index.json" />
        <Item icon="3" bg="#fff3e0" title="每日日报" badge={['orange', '09:35']} desc="AI+材料科学日报同步到看板" />
        <Item icon="4" bg="#fce4ec" title="个人档案" badge={['green', '每日']} desc="刘宇宙个人信息 → system_configs" />
        <Item icon="5" bg="#f3e5f5" title="人员档案" badge={['blue', '每日']} desc="10个本地人物profile同步" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🔐 安全策略</h3>
        <Item icon="🔑" bg="#e8f5e9" title="密码遮罩" badge={['green', '强制']} desc="所有API返回时密钥自动遮罩" />
        <Item icon="🗄️" bg="#e3f2fd" title="自动备份" badge={['blue', '每日']} desc="数据库每日dump压缩.gz归档" />
        <Item icon="🔙" bg="#fff3e0" title="备份保留" badge={['orange', '30天']} desc="自动清理超过30天的旧备份" />
        <Item icon="📡" bg="#fce4ec" title="RDS连接" badge={['green', '稳定']} desc="rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com" />
        <Item icon="🔄" bg="#f3e5f5" title="热重载" badge={['blue', 'API']} desc="systemctl restart + health check" />
      </div>
    </div>
    <div style={s.safety}>
      <b>🔴 安全红线</b>：密码永不硬编码（统一.env读取）· API Key从环境变量获取 · 前端不暴露敏感信息
    </div>
  </>
)

const RemoteTab = () => (
  <>
    <div style={s.stats}>
      <StatsCard value="4台" label="阿里云服务器" color="#1565c0" />
      <StatsCard value="3台" label="SSH可访问" color="#2e7d32" />
      <StatsCard value="1套" label="noVNC" color="#e53935" />
      <StatsCard value="10+" label="远程命令" />
      <StatsCard value="实时" label="控制模式" />
    </div>
    <div style={s.grid3}>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🖥️ 服务器拓扑</h3>
        <Item icon="1" bg="#e8f5e9" title="服务器1" badge={['green', '看板']} desc="47.93.184.128 - 看板系统/API/SocketIO" />
        <Item icon="2" bg="#e3f2fd" title="服务器2" badge={['orange', '不可达']} desc="网络不通, SSH认证失败" />
        <Item icon="3" bg="#fff3e0" title="服务器3" badge={['green', 'T109']} desc="60.205.197.9 - T109 API+Celery+MySQL" />
        <Item icon="4" bg="#fce4ec" title="服务器4" badge={['green', '待查']} desc="39.102.78.71 - 有aliserver4.pem" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🎮 远程控制台</h3>
        <Item icon="🏗️" bg="#e8f5e9" title="重启调度器" badge={['green', 'CMD']} desc="强制调度器重新扫描pending任务" />
        <Item icon="🕵️" bg="#e3f2fd" title="触发审核" badge={['blue', 'CMD']} desc="立即执行审核巡逻" />
        <Item icon="🔗" bg="#fff3e0" title="依赖链巡检" badge={['orange', 'CMD']} desc="检查上下游依赖链" />
        <Item icon="🔄" bg="#fce4ec" title="重跑任务" badge={['green', 'CMD']} desc="输入TaskID重置状态重执行" />
        <Item icon="🧹" bg="#f3e5f5" title="清空黑名单" badge={['blue', 'CMD']} desc="LLM故障恢复后解除限制" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>📡 远程桌面</h3>
        <Item icon="🖥️" bg="#e8f5e9" title="noVNC" badge={['green', '部署']} desc="Web VNC客户端，public/vnc/目录" />
        <Item icon="🔑" bg="#e3f2fd" title="SSH Key" badge={['blue', '6把']} desc="aliserver1-4.pem + GPU1.pem" />
        <Item icon="🔌" bg="#fff3e0" title="VNC端口" badge={['orange', '待开']} desc="Mac mini本机VNC需手动开启" />
        <Item icon="⚡" bg="#fce4ec" title="systemctl" badge={['green', '服务']} desc="kanban-api 4种systemd服务管理" />
        <Item icon="🔄" bg="#f3e5f5" title="nginx reload" badge={['blue', '热更新']} desc="修改配置后nginx -s reload" />
      </div>
    </div>
  </>
)

const ResearchTab = () => (
  <>
    <div style={s.stats}>
      <StatsCard value="每日" label="调研频率" color="#1565c0" />
      <StatsCard value="09:35" label="执行时间" color="#2e7d32" />
      <StatsCard value="2.0" label="报告版本" color="#e53935" />
      <StatsCard value="3路" label="投递渠道" />
      <StatsCard value="全自动" label="运行模式" />
    </div>
    <div style={s.grid3}>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🎯 调研能力</h3>
        <Item icon="🌐" bg="#e8f5e9" title="全球动态跟踪" badge={['green', 'Web搜索']} desc="AI+材料科学最新进展每日检索" />
        <Item icon="📄" bg="#e3f2fd" title="NLP摘要" badge={['blue', 'LLM']} desc="论文/新闻智能摘要生成" />
        <Item icon="🧠" bg="#fff3e0" title="深度分析" badge={['orange', 'Research']} desc="关键突破/趋势/商业化路径深度分析" />
        <Item icon="🔗" bg="#fce4ec" title="知识关联" badge={['green', '联网']} desc="自动关联已有知识库和文献" />
        <Item icon="📊" bg="#f3e5f5" title="结构化输出" badge={['blue', 'Markdown']} desc="标准格式报告，含引用链接" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>📦 投递渠道</h3>
        <Item icon="📋" bg="#e8f5e9" title="看板系统" badge={['green', '/research-daily']} desc="前端页面展示 + API读取" />
        <Item icon="📝" bg="#e3f2fd" title="Obsidian" badge={['blue', '本地']} desc="同步到memory/knowledge-base/" />
        <Item icon="🔐" bg="#fff3e0" title="阿里云看板" badge={['orange', 'SCP']} desc="scp同步到 /opt/kanban-react/backend/uploads/reports/" />
        <Item icon="💬" bg="#fce4ec" title="企业微信" badge={['green', '投递']} desc="cron自动投递到LiuYuZhou" />
        <Item icon="🌐" bg="#f3e5f5" title="LLM上下文" badge={['blue', 'system_configs']} desc="每日调研摘要注入LLM全局上下文" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>⚙️ 流水线</h3>
        <Item icon="1" bg="#e8f5e9" title="Web搜索" badge={['green', '检索']} desc="Tavily/Gemini搜索最新文献动态" />
        <Item icon="2" bg="#e3f2fd" title="AI生成" badge={['blue', 'LLM']} desc="DeepSeek/Kimi生成深度报告" />
        <Item icon="3" bg="#fff3e0" title="本地归档" badge={['orange', '存储']} desc="Markdown写入memory/knowledge-base/" />
        <Item icon="4" bg="#fce4ec" title="SCP同步" badge={['green', '服务器']} desc="scp到阿里云看板后端uploads" />
        <Item icon="5" bg="#f3e5f5" title="结果入库" badge={['blue', 'DB']} desc="每日调研记录写入数据库" />
      </div>
    </div>
    <div style={s.flow}>
      <div style={s.flowBox}>📡 09:35触发</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>🌐 Web搜索</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>🧠 LLM生成报告</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>📝 本地归档</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>🔄 3路同步投递</div>
    </div>
    <div style={s.safety}>
      <b>⏰ Cron配置</b>：`35 9 * * *` (09:35 CST) · 看板同步 `0 9 * * *` · Job IDs: b8cd6e94 / 88ba0449
    </div>
  </>
)



const KanbanTab = () => (
  <>
    <div style={s.stats}>
      <StatsCard value="React+TS" label="前端框架" color="#1565c0" />
      <StatsCard value="Flask+MySQL" label="后端引擎" color="#2e7d32" />
      <StatsCard value="55+" label="源码文件" color="#e53935" />
      <StatsCard value="9,554行" label="后端路由" />
      <StatsCard value="2,000+" label="前端组件行" />
    </div>
    <div style={s.grid3}>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🎯 前端架构</h3>
        <Item icon="📄" bg="#e8f5e9" title="main.tsx" badge={['green', '入口']} desc="React 应用入口，SW清理 + 全局初始化" />
        <Item icon="🧭" bg="#e3f2fd" title="router.tsx" badge={['blue', '路由']} desc="React Router v6，18+页面路由配置" />
        <Item icon="📐" bg="#fff3e0" title="Layout.tsx" badge={['orange', '布局']} desc="侧边栏 + WebSocket连接 + Outlet" />
        <Item icon="🎨" bg="#fce4ec" title="组件库" badge={['green', '复用']} desc="TaskAccordion/TaskAttachments/OnlineUsers" />
        <Item icon="🔧" bg="#f3e5f5" title="utils/api.ts" badge={['blue', 'API']} desc="统一API请求封装，axios风格调用" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>📦 后端架构</h3>
        <Item icon="🏗️" bg="#e8f5e9" title="app.py" badge={['green', '主入口']} desc="Flask APP + 蓝图注册 + SocketIO初始化" />
        <Item icon="🗄️" bg="#e3f2fd" title="routes/" badge={['blue', '35+文件']} desc="API路由模块化，9,554行总量" />
        <Item icon="🔌" bg="#fff3e0" title="database_config.py" badge={['orange', 'DB']} desc="MySQL连接池 + RDS配置" />
        <Item icon="🔐" bg="#fce4ec" title="auth.py" badge={['green', '鉴权']} desc="密码/API密钥管理 + 管理员后台" />
        <Item icon="📡" bg="#f3e5f5" title="src/websocket/" badge={['blue', '12+文件']} desc="SocketIO事件+心跳+Presence+锁" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🗂️ 前端页面</h3>
        <Item icon="📊" bg="#e8f5e9" title="Projects" badge={['green', '项目页']} desc="项目列表+任务展开+文件管理" />
        <Item icon="🤖" bg="#e3f2fd" title="SelfDriving" badge={['blue', 'SDS页面']} desc="自我驱动系统控制台" />
        <Item icon="🖥️" bg="#fff3e0" title="SDSConsole" badge={['orange', '总控台']} desc="进化系统可视化监控" />
        <Item icon="👤" bg="#fce4ec" title="SystemPages" badge={['green', '系统']} desc="系统状态+进程+监控仪表盘" />
        <Item icon="📋" bg="#f3e5f5" title="+14个页面" badge={['blue', '路由']} desc="看板总览/LLM/联系人文库配置等" />
      </div>
    </div>
    <h4 style={{ fontSize: '16px', fontWeight: 600, color: '#333', margin: '20px 0 12px' }}>🏗️ 看板架构图</h4>
    <div style={{ background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '10px', marginBottom: '12px', textAlign: 'center' }}>
      <KanbanArchDiagram />
    </div>
    <div style={s.flow}>
      <div style={s.flowBox}>nignx 443/80</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>dist静态文件</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>React SPA渲染</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>API请求</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>Flask API :8086</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>RDS MySQL</div>
    </div>
  </>
)

const SecurityTab = () => (
  <>
    <div style={s.stats}>
      <StatsCard value="3层" label="认证体系" color="#1565c0" />
      <StatsCard value="2种" label="密钥类型" color="#2e7d32" />
      <StatsCard value="全覆盖" label="访问控制" color="#e53935" />
      <StatsCard value="自动" label="审计日志" />
      <StatsCard value="严格" label="加密策略" />
    </div>
    <div style={s.grid3}>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🔑 认证体系</h3>
        <Item icon="🔐" bg="#e8f5e9" title="密码管理" badge={['green', 'P049-T007']} desc="密码加密存储 + 验证接口" />
        <Item icon="🔑" bg="#e3f2fd" title="API密钥管理" badge={['blue', 'P049-T008']} desc="密钥生成/轮换/撤销全生命周期" />
        <Item icon="🛡️" bg="#fff3e0" title="管理员后台" badge={['orange', 'P049-T8-2']} desc="管理员权限鉴别 + 操作审批" />
        <Item icon="🕵️" bg="#fce4ec" title="审核流水" badge={['green', 'audit']} desc="所有敏感操作日志不可篡改" />
        <Item icon="📋" bg="#f3e5f5" title="访问日志" badge={['blue', 'access_logs']} desc="IP/路径/时间完整追踪" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🔒 安全策略</h3>
        <Item icon="🔏" bg="#e8f5e9" title="密码永不硬编码" badge={['green', '永久规则']} desc="统一从.env文件/环境变量读取" />
        <Item icon="👁️" bg="#e3f2fd" title="API脱敏" badge={['blue', '强制']} desc="所有返回中密码/密钥自动遮罩" />
        <Item icon="🚫" bg="#fff3e0" title="前端不暴露敏感信息" badge={['orange', '隔离']} desc="DB密码/API Key不进入前端代码" />
        <Item icon="🔄" bg="#fce4ec" title="密钥轮换" badge={['green', '定期']} desc="发现泄露立即轮换" />
        <Item icon="🗑️" bg="#f3e5f5" title="敏感文件排除" badge={['blue', 'gitignore']} desc=".env / __pycache__ / .pem 不入库" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🛡️ 基础设施</h3>
        <Item icon="🌐" bg="#e8f5e9" title="HTTPS" badge={['green', '强制']} desc="nginx SSL + 自动跳转80→443" />
        <Item icon="📝" bg="#e3f2fd" title="CSP策略" badge={['blue', '限制']} desc="Content-Security-Policy 严格限制" />
        <Item icon="🔌" bg="#fff3e0" title="SSH密钥" badge={['orange', '6把pem']} desc="aliyun EC2 SSH Key认证" />
        <Item icon="💾" bg="#fce4ec" title="数据库备份" badge={['green', '每日']} desc="gz加密压缩，30天保留" />
        <Item icon="🚨" bg="#f3e5f5" title="Sentry" badge={['blue', '监控']} desc="前端错误上报 + 性能追踪" />
      </div>
    </div>
  </>
)

const DeployTab = () => (
  <>
    <div style={s.stats}>
      <StatsCard value="4个" label="systemd服务" color="#1565c0" />
      <StatsCard value="38s" label="平均构建时间" color="#2e7d32" />
      <StatsCard value="9步" label="同步流水线" color="#e53935" />
      <StatsCard value="5s" label="失败重启间隔" />
      <StatsCard value="实时" label="nginx热更新" />
    </div>
    <div style={s.grid3}>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>📦 systemd服务</h3>
        <Item icon="1" bg="#e8f5e9" title="kanban-api.service" badge={['green', '8086']} desc="gunicorn 4 workers, eventlet, REST API" />
        <Item icon="2" bg="#e3f2fd" title="kanban-backend.service" badge={['blue', '8085']} desc="eventlet 1 worker, SocketIO WebSocket" />
        <Item icon="3" bg="#fff3e0" title="monitor-relay.service" badge={['orange', '8765']} desc="WebSocket监控中继，系统指标推送" />
        <Item icon="4" bg="#fce4ec" title="email-api.service" badge={['green', '8089']} desc="邮件API服务" />
        <Item icon="5" bg="#f3e5f5" title="nginx.service" badge={['blue', '443/80']} desc="静态文件 + 反向代理 + SSL" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>🔄 部署流程</h3>
        <Item icon="1" bg="#e8f5e9" title="源码修改" badge={['green', '本地/SSH']} desc="编辑前端/src 或 后端/routes" />
        <Item icon="2" bg="#e3f2fd" title="Vite构建" badge={['blue', '38秒']} desc="npm run build → dist/assets/ 带contenthash" />
        <Item icon="3" bg="#fff3e0" title="nginx检测" badge={['orange', 'nginx -t']} desc="配置语法检查，失败不回滚" />
        <Item icon="4" bg="#fce4ec" title="服务重启" badge={['green', 'systemctl']} desc="restart + health check 双重验证" />
        <Item icon="5" bg="#f3e5f5" title="API测试" badge={['blue', 'curl']} desc="关键端点自动验证 HTTP 200" />
      </div>
      <div style={s.card}>
        <h3 style={{ fontSize: '15px', marginBottom: '12px', color: '#333' }}>⚙️ 运维体系</h3>
        <Item icon="🔄" bg="#e8f5e9" title="每日同步" badge={['green', '09:00']} desc="sync_kanban.py 9步全量同步" />
        <Item icon="📋" bg="#e3f2fd" title="文件索引" badge={['blue', '自动']} desc="local_files_index.json 自动生成" />
        <Item icon="💾" bg="#fff3e0" title="数据备份" badge={['orange', '每日']} desc="MySQL dump → gz → 30天循环" />
        <Item icon="🚨" bg="#fce4ec" title="健康检查" badge={['green', '定期']} desc="API /api/health + checkups" />
        <Item icon="📡" bg="#f3e5f5" title="版本控制" badge={['blue', 'GitHub+GitLab']} desc="GitHub(远程) + GitLab(自建) 双备份" />
      </div>
    </div>
    <h4 style={{ fontSize: '16px', fontWeight: 600, color: '#333', margin: '20px 0 12px' }}>🏗️ 部署架构图</h4>
    <div style={{ background: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px', padding: '10px', marginBottom: '12px', textAlign: 'center' }}>
      <DeployArchDiagram />
    </div>
    <div style={s.flow}>
      <div style={s.flowBox}>Edit</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>Build (38s)</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>nginx -t</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>systemctl restart</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>Health Check</div><span style={{color:'#999'}}>→</span>
      <div style={s.flowBox}>✅ OK</div>
    </div>
  </>
)


const ProjectDesign: React.FC = () => {
  const [tab, setTab] = useState('evolution')

  const TabBtn = ({ id, label }: { id: string; label: string }) => (
    <button
      onClick={() => setTab(id)}
      style={{
        padding: '10px 24px', border: 'none', background: 'transparent', color: tab === id ? '#667eea' : '#666',
        fontSize: '14px', cursor: 'pointer', borderBottom: `3px solid ${tab === id ? '#667eea' : 'transparent'}`,
        fontWeight: tab === id ? 600 : 400, transition: 'all .2s',
      }}
    >{label}</button>
  )

  return (
    <div style={s.page}>
      <div style={s.container}>
        <div style={s.tabNav}>
          <TabBtn id="evolution" label="🧠 镜像进化" />
          <TabBtn id="t109" label="📋 T109" />
          <TabBtn id="sds" label="🧬 SDS调度" />
          <TabBtn id="sds-arch" label="🏗️ SDS架构" />
          <TabBtn id="actor" label="⚡ Actor通道" />
          <TabBtn id="monitor" label="📡 监控告警" />
          <TabBtn id="data" label="🗄️ 数据架构" />
          <TabBtn id="remote" label="🖥️ 远程操控" />
          <TabBtn id="research" label="🤖 AI调研" />
          <TabBtn id="kanban" label="🏭 看板全貌" />
          <TabBtn id="security" label="🔐 安全认证" />
          <TabBtn id="deploy" label="📦 部署发布" />
        </div>

        {tab === 'evolution' && <EvolutionTab />}
        {tab === 't109' && <T109Tab />}
        {tab === 'sds' && <SdsTab />}
        {tab === 'sds-arch' && <SdsArchTab />}
        {tab === 'actor' && <ActorTab />}
        {tab === 'monitor' && <MonitorTab />}
        {tab === 'data' && <DataTab />}
        {tab === 'remote' && <RemoteTab />}
        {tab === 'research' && <ResearchTab />}
        {tab === 'kanban' && <KanbanTab />}
        {tab === 'security' && <SecurityTab />}
        {tab === 'deploy' && <DeployTab />}
      </div>
    </div>
  )
}

export default ProjectDesign
