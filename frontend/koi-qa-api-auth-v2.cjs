const { chromium } = require('playwright');

(async () => {
  console.log('🚀 KOI QA with API Auth v2');
  
  // Step 1: API 登录
  console.log('🔐 API 登录...');
  
  const loginResponse = await fetch('http://localhost/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: 'dudu2026' })
  });
  
  const loginData = await loginResponse.json();
  
  if (!loginData.success) {
    console.log('❌ API 登录失败:', loginData.message);
    process.exit(1);
  }
  
  const token = loginData.token;
  console.log('✅ API 登录成功');
  
  // Step 2: 使用 Playwright，设置正确的 token key
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  await page.goto('http://localhost/self-driving', { waitUntil: 'domcontentloaded', timeout: 15000 });
  
  // 使用正确的 key: kanban_token
  await page.evaluate((authToken, userData) => {
    localStorage.setItem('kanban_token', authToken);
    localStorage.setItem('kanban_user', JSON.stringify(userData));
  }, token, loginData.user);
  
  console.log('✅ Token 已设置 (kanban_token)');
  
  // 刷新页面
  await page.reload({ waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(3000);
  
  const results = [];
  const errors = [];
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push({ type: 'console', text: msg.text() });
      console.log('❌ Console:', msg.text());
    }
  });
  
  page.on('pageerror', err => {
    errors.push({ type: 'pageerror', message: err.message });
    console.log('❌ PageError:', err.message);
  });
  
  try {
    const pageText = await page.evaluate(() => document.body.innerText);
    
    if (pageText.includes('自我驱动') || pageText.includes('系统状态')) {
      console.log('✅ SDS 页面加载成功');
      results.push({ test: 'SDS页面', status: 'PASS' });
      
      // 获取按钮
      const buttons = await page.locator('button').all();
      const buttonTexts = [];
      for (const btn of buttons) {
        const text = await btn.textContent().catch(() => '');
        buttonTexts.push(text.trim());
      }
      
      console.log('📋 按钮:', buttonTexts);
      
      // 点击历史趋势
      const historyIndex = buttonTexts.findIndex(t => t.includes('历史'));
      if (historyIndex >= 0) {
        console.log('🖱️ 点击:', buttonTexts[historyIndex]);
        await buttons[historyIndex].click();
        await page.waitForTimeout(3000);
        
        // 检查错误
        const errorInfo = await page.evaluate(() => {
          const errorElements = document.querySelectorAll('[class*=error], .text-red-500, [class*=alert-error]');
          if (errorElements.length > 0) {
            return { hasError: true, text: errorElements[0].innerText.substring(0, 200) };
          }
          return { hasError: false };
        });
        
        if (errorInfo.hasError) {
          console.log('❌ 历史趋势错误:', errorInfo.text);
          results.push({ test: '历史趋势', status: 'FAIL', reason: errorInfo.text });
        } else {
          console.log('✅ 历史趋势正常');
          results.push({ test: '历史趋势', status: 'PASS' });
        }
      } else {
        results.push({ test: '历史趋势', status: 'FAIL', reason: '未找到按钮' });
      }
      
      await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/sds-final.png', fullPage: true });
      
    } else if (pageText.includes('请登录')) {
      console.log('❌ 仍需要登录');
      results.push({ test: 'SDS页面', status: 'FAIL', reason: 'Token 无效或过期' });
    } else {
      console.log('⚠️ 页面内容:', pageText.substring(0, 300));
      results.push({ test: 'SDS页面', status: 'WARN', reason: '未知状态' });
    }
    
  } catch (e) {
    console.error('❌ 执行错误:', e.message);
    results.push({ test: '执行', status: 'FAIL', reason: e.message });
  }
  
  console.log('\n========================================');
  console.log('  KOI QA API Auth v2 报告');
  console.log('========================================');
  for (const r of results) {
    const icon = r.status === 'PASS' ? '✅' : '❌';
    console.log();
  }
  
  if (errors.length > 0) {
    console.log('\n📋 JavaScript 错误:');
    errors.forEach(e => console.log('  ❌', e.text || e.message));
  } else {
    console.log('\n✅ 无 JavaScript 错误');
  }
  
  console.log('========================================');
  
  await browser.close();
})();
