const { chromium } = require('playwright');

(async () => {
  console.log('🚀 启动看板系统 QA 测试...');
  
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  const results = [];
  const jsErrors = [];
  
  page.on('console', msg => {
    if (msg.type() === 'error') jsErrors.push(msg.text());
  });
  page.on('pageerror', err => jsErrors.push(err.message));

  // Test 1: 首页
  await page.goto('http://localhost/', { waitUntil: 'networkidle', timeout: 10000 });
  results.push('✅ 首页加载成功');
  
  // Test 2: 任务页面
  await page.goto('http://localhost/tasks', { waitUntil: 'networkidle', timeout: 10000 });
  await page.waitForTimeout(1000);
  const taskTitle = await page.locator('h1').textContent().catch(() => '');
  results.push(taskTitle.includes('任务') ? '✅ 任务页面正常' : '⚠️ 任务页面标题异常');
  
  // Test 3: 项目页面 - 检查最大化按钮
  await page.goto('http://localhost/projects', { waitUntil: 'networkidle', timeout: 10000 });
  await page.waitForTimeout(1000);
  const maximizeBtns = await page.locator('svg').filter({ hasText: /maximize/i }).count();
  results.push(maximizeBtns > 0 ?  : '⚠️ 项目页面: 未找到最大化按钮');
  
  // Test 4: 战略全景
  await page.goto('http://localhost/strategic-map', { waitUntil: 'networkidle', timeout: 10000 });
  await page.waitForTimeout(1000);
  const hasTreeBtn = await page.locator('button:has-text("树形视图")').isVisible().catch(() => false);
  const hasCardBtn = await page.locator('button:has-text("卡片视图")').isVisible().catch(() => false);
  results.push(hasTreeBtn && hasCardBtn ? '✅ 战略全景: 视图切换按钮存在' : '⚠️ 战略全景: 按钮未找到');
  
  // Test 5: 会议纪要
  await page.goto('http://localhost/meeting-notes', { waitUntil: 'networkidle', timeout: 10000 });
  await page.waitForTimeout(1000);
  results.push('✅ 会议纪要页面加载成功');
  
  // Test 6: 自我驱动系统
  await page.goto('http://localhost/self-driving-system', { waitUntil: 'networkidle', timeout: 10000 });
  await page.waitForTimeout(1000);
  const hasHistory = await page.locator('button:has-text("历史趋势")').isVisible().catch(() => false);
  const hasArch = await page.locator('button:has-text("架构编辑")').isVisible().catch(() => false);
  results.push(hasHistory && hasArch ? '✅ 自我驱动系统: 标签正常' : '⚠️ 自我驱动系统: 标签异常');
  
  // 输出结果
  console.log('\n' + '='.repeat(50));
  console.log('📊 看板系统自动化验收测试报告');
  console.log('='.repeat(50));
  results.forEach(r => console.log(r));
  
  console.log('\n📋 JavaScript 错误:');
  if (jsErrors.length > 0) {
    jsErrors.slice(0, 5).forEach(e => console.log('  ⚠️ ' + e.substring(0, 100)));
  } else {
    console.log('  ✅ 无 JavaScript 错误');
  }
  console.log('='.repeat(50));
  
  await browser.close();
})();
