const { chromium } = require('playwright');

(async () => {
  console.log('🚀 KOI 增强版 QA 测试 - 包含交互验证');
  
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  const results = [];
  const errors = [];
  const consoleErrors = [];
  
  // 捕获所有控制台错误
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push({
        type: 'console.error',
        text: msg.text(),
        location: msg.location(),
        time: new Date().toISOString()
      });
    }
  });
  
  page.on('pageerror', err => {
    errors.push({
      type: 'pageerror',
      message: err.message,
      stack: err.stack,
      time: new Date().toISOString()
    });
  });
  
  page.on('response', response => {
    if (!response.ok() && response.url().includes('/api/')) {
      consoleErrors.push({
        type: 'api.error',
        url: response.url(),
        status: response.status(),
        time: new Date().toISOString()
      });
    }
  });

  try {
    // ========================================
    // Test 1: 首页基础加载
    // ========================================
    await page.goto('http://localhost/', { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);
    results.push({ test: '首页加载', status: 'PASS' });
    await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/01-homepage.png' });

    // ========================================
    // Test 2: 任务页面 - 按钮交互
    // ========================================
    await page.goto('http://localhost/tasks', { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    // 点击 Tab 视图按钮
    const tabBtn = await page.locator('button:has-text("Tab")').first();
    if (await tabBtn.isVisible().catch(() => false)) {
      await tabBtn.click();
      await page.waitForTimeout(1000);
      results.push({ test: '任务-Tab切换', status: 'PASS' });
    } else {
      results.push({ test: '任务-Tab切换', status: 'SKIP', reason: '按钮未找到' });
    }
    
    await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/02-tasks.png' });

    // ========================================
    // Test 3: 项目页面 - 最大化按钮
    // ========================================
    await page.goto('http://localhost/projects', { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    // 尝试点击最大化按钮
    const maximizeBtn = await page.locator('button').filter({ has: page.locator('svg') }).first();
    if (await maximizeBtn.isVisible().catch(() => false)) {
      await maximizeBtn.click();
      await page.waitForTimeout(1500);
      
      // 检查模态框是否出现
      const modal = await page.locator('[class*="modal"], [class*="dialog"], .fixed').first();
      const hasModal = await modal.isVisible().catch(() => false);
      
      if (hasModal) {
        results.push({ test: '项目-最大化按钮', status: 'PASS' });
      } else {
        results.push({ test: '项目-最大化按钮', status: 'FAIL', reason: '点击后未出现模态框' });
      }
    } else {
      results.push({ test: '项目-最大化按钮', status: 'SKIP', reason: '按钮未找到' });
    }
    
    await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/03-projects.png' });

    // ========================================
    // Test 4: 战略全景 - 视图切换
    // ========================================
    await page.goto('http://localhost/strategic-map', { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    const treeBtn = await page.locator('button:has-text("树形")').first();
    const cardBtn = await page.locator('button:has-text("卡片")').first();
    
    if (await treeBtn.isVisible().catch(() => false)) {
      await treeBtn.click();
      await page.waitForTimeout(1500);
      results.push({ test: '战略全景-树形视图', status: 'PASS' });
    } else {
      results.push({ test: '战略全景-视图切换', status: 'SKIP', reason: '按钮未找到' });
    }
    
    await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/04-strategic.png' });

    // ========================================
    // Test 5: 会议纪要
    // ========================================
    await page.goto('http://localhost/meeting-notes', { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);
    results.push({ test: '会议纪要加载', status: 'PASS' });
    await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/05-meetings.png' });

    // ========================================
    // Test 6: 自我驱动系统 - 关键测试！
    // ========================================
    console.log('🔍 测试自我驱动系统...');
    await page.goto('http://localhost/self-driving-system', { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    results.push({ test: 'SDS-页面加载', status: 'PASS' });
    
    // 6.1 点击"历史趋势"标签
    const historyTab = await page.locator('button:has-text("历史"), button:has-text("趋势"), [role="tab"]:has-text("历史")').first();
    
    if (await historyTab.isVisible().catch(() => false)) {
      console.log('  找到历史趋势标签，点击...');
      await historyTab.click();
      await page.waitForTimeout(3000); // 等待数据加载
      
      // 检查是否有错误提示
      const errorAlert = await page.locator('[class*="error"], [class*="alert"], .text-red-500').first();
      const hasError = await errorAlert.isVisible().catch(() => false);
      
      if (hasError) {
        const errorText = await errorAlert.textContent().catch(() => 'Unknown error');
        results.push({ 
          test: 'SDS-历史趋势', 
          status: 'FAIL', 
          reason: `显示错误: ${errorText}` 
        });
      } else {
        // 检查是否有图表或数据表格
        const hasChart = await page.locator('canvas, [class*="chart"], svg').count() > 0;
        const hasTable = await page.locator('table, [class*="table"]').count() > 0;
        
        if (hasChart || hasTable) {
          results.push({ test: 'SDS-历史趋势', status: 'PASS', detail: hasChart ? '图表渲染' : '表格渲染' });
        } else {
          results.push({ test: 'SDS-历史趋势', status: 'WARN', reason: '无图表或表格数据' });
        }
      }
    } else {
      results.push({ test: 'SDS-历史趋势', status: 'FAIL', reason: '未找到"历史趋势"标签' });
    }
    
    // 6.2 点击"架构编辑"标签
    const archTab = await page.locator('button:has-text("架构"), button:has-text("编辑"), [role="tab"]:has-text("架构")').first();
    
    if (await archTab.isVisible().catch(() => false)) {
      await archTab.click();
      await page.waitForTimeout(1500);
      results.push({ test: 'SDS-架构编辑', status: 'PASS' });
    } else {
      results.push({ test: 'SDS-架构编辑', status: 'SKIP', reason: '标签未找到' });
    }
    
    await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/06-sds.png' });

    // ========================================
    // Test 7: API 直接测试
    // ========================================
    console.log('🔍 测试 API...');
    const apiTests = [
      { url: '/api/tasks?page=1&per_page=5', name: '任务列表' },
      { url: '/api/sds/stats', name: 'SDS统计' },
      { url: '/api/sds/history', name: 'SDS历史' }
    ];
    
    for (const api of apiTests) {
      try {
        const response = await page.evaluate(async (url) => {
          const res = await fetch(url);
          return { status: res.status, ok: res.ok };
        }, api.url);
        
        if (response.ok) {
          results.push({ test: `API-${api.name}`, status: 'PASS' });
        } else {
          results.push({ test: `API-${api.name}`, status: 'FAIL', reason: `HTTP ${response.status}` });
        }
      } catch (e) {
        results.push({ test: `API-${api.name}`, status: 'FAIL', reason: e.message });
      }
    }

  } catch (e) {
    results.push({ test: '执行过程', status: 'FAIL', reason: e.message });
  }
  
  // ========================================
  // 输出报告
  // ========================================
  console.log('\n========================================');
  console.log('  KOI 增强版 QA 测试报告');
  console.log('========================================');
  
  let pass = 0, fail = 0, warn = 0, skip = 0;
  
  for (const r of results) {
    const icon = r.status === 'PASS' ? '✅' : r.status === 'FAIL' ? '❌' : r.status === 'WARN' ? '⚠️' : '⏭️';
    console.log(`${icon} ${r.test}: ${r.status}${r.reason ? ' - ' + r.reason : ''}`);
    
    if (r.status === 'PASS') pass++;
    else if (r.status === 'FAIL') fail++;
    else if (r.status === 'WARN') warn++;
    else skip++;
  }
  
  console.log('\n----------------------------------------');
  console.log(`总计: ${pass} 通过, ${fail} 失败, ${warn} 警告, ${skip} 跳过`);
  console.log('----------------------------------------');
  
  // 错误详情
  if (consoleErrors.length > 0 || errors.length > 0) {
    console.log('\n📋 捕获的错误:');
    for (const err of [...errors, ...consoleErrors].slice(0, 10)) {
      console.log(`  ❌ [${err.type}] ${err.message || err.text || JSON.stringify(err).substring(0, 100)}`);
    }
    if (errors.length + consoleErrors.length > 10) {
      console.log(`  ... 还有 ${errors.length + consoleErrors.length - 10} 个错误`);
    }
  } else {
    console.log('\n✅ 无 JavaScript 错误');
  }
  
  console.log('========================================');
  
  // 保存 JSON 报告
  const fs = require('fs');
  fs.writeFileSync('/opt/kanban-react/qa-reports/enhanced-qa-report.json', JSON.stringify({
    timestamp: new Date().toISOString(),
    summary: { pass, fail, warn, skip },
    results,
    errors: [...errors, ...consoleErrors]
  }, null, 2));
  
  await browser.close();
  
  // 如果有失败，退出码设为 1
  if (fail > 0) {
    process.exit(1);
  }
})();
