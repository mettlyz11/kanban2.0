const { chromium } = require('playwright');

(async () => {
  console.log('🚀 KOI QA v2 - 修复标签匹配');
  
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  const results = [];
  const errors = [];
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push({ type: 'console.error', text: msg.text() });
    }
  });
  
  page.on('pageerror', err => {
    errors.push({ type: 'pageerror', message: err.message });
  });

  try {
    // 测试 SDS 页面
    await page.goto('http://localhost/self-driving-system', { 
      waitUntil: 'domcontentloaded', 
      timeout: 15000 
    });
    await page.waitForTimeout(2000);
    
    results.push({ test: 'SDS-页面加载', status: 'PASS' });
    
    // 获取所有按钮文字
    const buttons = await page.locator('button').all();
    const buttonTexts = [];
    for (const btn of buttons) {
      const text = await btn.textContent().catch(() => '');
      buttonTexts.push(text.trim());
    }
    
    console.log('找到的按钮:', buttonTexts);
    
    // 查找包含历史的按钮
    const historyBtnIndex = buttonTexts.findIndex(t => t.includes('历史'));
    
    if (historyBtnIndex >= 0) {
      console.log('✅ 找到历史趋势按钮:', buttonTexts[historyBtnIndex]);
      
      // 点击按钮
      await buttons[historyBtnIndex].click();
      await page.waitForTimeout(3000);
      
      // 检查是否有错误
      const errorElements = await page.locator('[class*=error], .text-red-500, .ant-alert-error').count();
      
      if (errorElements > 0) {
        const errorText = await page.locator('[class*=error], .text-red-500').first().textContent().catch(() => 'Error');
        results.push({ test: 'SDS-历史趋势', status: 'FAIL', reason: errorText });
      } else {
        // 检查内容是否渲染
        const content = await page.locator('h2').filter({ hasText: /趋势/ }).count();
        if (content > 0) {
          results.push({ test: 'SDS-历史趋势', status: 'PASS' });
        } else {
          results.push({ test: 'SDS-历史趋势', status: 'WARN', reason: '可能未正确渲染' });
        }
      }
    } else {
      results.push({ test: 'SDS-历史趋势', status: 'FAIL', reason: '未找到包含历史的按钮' });
    }
    
    await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/sds-history.png' });

  } catch (e) {
    results.push({ test: '执行', status: 'FAIL', reason: e.message });
  }
  
  // 输出报告
  console.log('\n========================================');
  console.log('  KOI QA v2 报告');
  console.log('========================================');
  
  for (const r of results) {
    const icon = r.status === 'PASS' ? '✅' : r.status === 'FAIL' ? '❌' : '⚠️';
    console.log();
  }
  
  if (errors.length > 0) {
    console.log('\n📋 JavaScript 错误:');
    errors.forEach(e => console.log('  ❌', e.text || e.message));
  }
  
  console.log('========================================');
  
  await browser.close();
})();
