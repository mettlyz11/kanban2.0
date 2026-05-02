const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  console.log('🚀 启动看板系统自动化验收测试...\n');
  
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  
  const results = [];
  const errors = [];
  
  // 捕获所有控制台错误
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push();
    }
  });
  
  // 捕获所有页面错误
  page.on('pageerror', err => {
    errors.push();
  });

  try {
    // ===== Test 1: 首页加载 =====
    console.log('📄 Test 1: 首页加载...');
    await page.goto('http://localhost/', { waitUntil: 'networkidle', timeout: 15000 });
    await page.screenshot({ path: '/tmp/qa-screenshots/01-homepage.png' });
    const title = await page.title();
    results.push();
    
    // ===== Test 2: 任务页面 - 按钮布局 =====
    console.log('📋 Test 2: 任务页面按钮布局...');
    await page.goto('http://localhost/tasks', { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    // 检查按钮是否在一排
    const hasButtonRow = await page.locator('button:has-text("Tab视图")').isVisible().catch(() => false);
    const hasNewTaskBtn = await page.locator('button:has-text("新建任务")').isVisible().catch(() => false);
    
    if (hasButtonRow && hasNewTaskBtn) {
      results.push('✅ 任务页面: 按钮布局正常');
    } else {
      results.push('❌ 任务页面: 按钮布局异常');
    }
    await page.screenshot({ path: '/tmp/qa-screenshots/02-tasks.png' });
    
    // ===== Test 3: 项目页面 - 最大化按钮 =====
    console.log('📁 Test 3: 项目页面最大化功能...');
    await page.goto('http://localhost/projects', { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    // 检查 Maximize2 按钮是否存在
    const hasMaximize = await page.locator('svg[class*="lucide"][class*="maximize"], button svg[data-lucide="maximize2"]').count() > 0;
    
    if (hasMaximize) {
      results.push('✅ 项目页面: 最大化按钮存在');
      // 尝试点击第一个最大化按钮
      try {
        await page.locator('button').filter({ has: page.locator('svg[class*="maximize"]') }).first().click({ timeout: 5000 });
        await page.waitForTimeout(1000);
        const hasModal = await page.locator('.fixed, [class*="modal"], [class*="dialog"]').isVisible().catch(() => false);
        if (hasModal) {
          results.push('✅ 项目页面: 最大化模态框可打开');
        } else {
          results.push('⚠️ 项目页面: 点击后未检测到模态框');
        }
      } catch (e) {
        results.push();
      }
    } else {
      results.push('❌ 项目页面: 最大化按钮未找到');
    }
    await page.screenshot({ path: '/tmp/qa-screenshots/03-projects.png' });
    
    // ===== Test 4: 战略全景 - 视图切换 =====
    console.log('🎯 Test 4: 战略全景视图切换...');
    await page.goto('http://localhost/strategic-map', { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    const hasTreeBtn = await page.locator('button:has-text("树形视图")').isVisible().catch(() => false);
    const hasCardBtn = await page.locator('button:has-text("卡片视图")').isVisible().catch(() => false);
    
    if (hasTreeBtn && hasCardBtn) {
      results.push('✅ 战略全景: 视图切换按钮存在');
      // 测试切换
      try {
        await page.locator('button:has-text("树形视图")').click({ timeout: 5000 });
        await page.waitForTimeout(1000);
        results.push('✅ 战略全景: 可切换到树形视图');
      } catch (e) {
        results.push();
      }
    } else {
      results.push('❌ 战略全景: 视图切换按钮未找到');
    }
    await page.screenshot({ path: '/tmp/qa-screenshots/04-strategic.png' });
    
    // ===== Test 5: 会议纪要 - 时间线 =====
    console.log('📝 Test 5: 会议纪要时间线...');
    await page.goto('http://localhost/meeting-notes', { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    const hasTimeline = await page.locator('[class*="timeline"], [class*="meeting-timeline"]').count() > 0;
    const hasCards = await page.locator('[class*="meeting-card"]').count() > 0;
    
    if (hasTimeline || hasCards) {
      results.push('✅ 会议纪要: 时间线/卡片布局存在');
    } else {
      results.push('⚠️ 会议纪要: 未检测到时间线样式（可能数据为空）');
    }
    await page.screenshot({ path: '/tmp/qa-screenshots/05-meetings.png' });
    
    // ===== Test 6: 自我驱动系统 =====
    console.log('🤖 Test 6: 自我驱动系统...');
    await page.goto('http://localhost/self-driving-system', { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    const hasHistoryTab = await page.locator('button:has-text("历史趋势")').isVisible().catch(() => false);
    const hasArchTab = await page.locator('button:has-text("架构编辑")').isVisible().catch(() => false);
    
    if (hasHistoryTab && hasArchTab) {
      results.push('✅ 自我驱动系统: 历史趋势/架构编辑标签存在');
      
      // 测试历史趋势
      try {
        await page.locator('button:has-text("历史趋势")').click({ timeout: 5000 });
        await page.waitForTimeout(1500);
        const hasChart = await page.locator('[class*="chart"], canvas, [style*="height"]').count() > 0;
        if (hasChart) {
          results.push('✅ 自我驱动系统: 历史趋势图表可显示');
        } else {
          results.push('⚠️ 自我驱动系统: 历史趋势无图表数据');
        }
      } catch (e) {
        results.push();
      }
      
      // 测试架构编辑
      try {
        await page.locator('button:has-text("架构编辑")').click({ timeout: 5000 });
        await page.waitForTimeout(1500);
        const hasContent = await page.locator('pre, [class*="code"], [class*="json"]').count() > 0;
        if (hasContent) {
          results.push('✅ 自我驱动系统: 架构编辑可显示');
        } else {
          results.push('⚠️ 自我驱动系统: 架构编辑无内容');
        }
      } catch (e) {
        results.push();
      }
    } else {
      results.push('❌ 自我驱动系统: 标签未找到');
    }
    await page.screenshot({ path: '/tmp/qa-screenshots/06-sds.png' });
    
  } catch (e) {
    results.push();
  }
  
  // 输出结果
  console.log('\n' + '='.repeat(50));
  console.log('📊 看板系统自动化验收测试报告');
  console.log('='.repeat(50));
  results.forEach(r => console.log(r));
  
  console.log('\n📋 JavaScript 控制台错误:');
  if (errors.length > 0) {
    errors.slice(0, 10).forEach(e => console.log());
    if (errors.length > 10) console.log();
  } else {
    console.log('  ✅ 无 JavaScript 错误');
  }
  
  console.log('\n📸 截图保存位置: /tmp/qa-screenshots/');
  console.log('='.repeat(50));
  
  await browser.close();
})();
