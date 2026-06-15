import React from 'react'
export default function Pricing(){
  const plans=[
    ['种子','免费','1棵树 / 5片叶子 / 基础功能','开始体验',''],
    ['生长','¥19/月','3棵树 / 50片叶子 / 导出','推荐','border:#22c55e'],
    ['开花','¥99/月','10棵树 / 无限叶子 / 团队协作','升级',''],
    ['花园','¥499/月','私有部署 / 无限用户 / 定制支持','联系部署',''],
  ]
  return <div style={{minHeight:'100vh',background:'#0f172a',color:'#e2e8f0',fontFamily:'system-ui',padding:24}}><div style={{maxWidth:1000,margin:'0 auto'}}>
    <a href='/' style={{color:'#64748b',textDecoration:'none'}}>← 首页</a><h1 style={{fontSize:42}}>💰 SproutOS 定价</h1><p style={{color:'#94a3b8'}}>免费种下，按生长付费。科研用户友好。</p>
    <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(210px,1fr))',gap:14,marginTop:28}}>{plans.map((p,i)=><div key={i} style={{background:'#1e293b',border:p[4]?'1px solid #22c55e':'1px solid #334155',borderRadius:16,padding:22}}><h2>{p[0]}</h2><div style={{fontSize:32,fontWeight:800,color:'#22c55e'}}>{p[1]}</div><p style={{color:'#94a3b8',lineHeight:1.8}}>{p[2]}</p><a href='/payment?plan='+p[0].toLowerCase() style={{display:'block',textAlign:'center',background:i===1?'#22c55e':'#334155',color:i===1?'#020617':'#e2e8f0',borderRadius:10,padding:10,textDecoration:'none',fontWeight:700}}>{p[3]}</a></div>)}</div>
    <section style={{marginTop:30,background:'#111827',border:'1px solid #334155',borderRadius:16,padding:20}}><h2>🎓 学术友好</h2><p style={{color:'#94a3b8'}}>高校/课题组可申请免费或低价额度；科研场景是第一优先级。</p></section>
  </div></div>
}
