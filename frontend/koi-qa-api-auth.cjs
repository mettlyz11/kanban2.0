const { chromium } = require('playwright');

(async () => {
  console.log('🚀 KOI QA with API Auth');
  
  // Step 1: 通过 API 登录获取 token
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
  console.log('✅ API 登录成功，获取 token');
  
  // Step 2: 使用 Playwright 访问页面，带上 token
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // 设置 localStorage token（前端通常从这里读取）
  await page.goto('http://localhost/self-driving', { waitUntil: 'domcontentloaded', timeout: 15000 });
  
  await page.evaluate((authToken) => {
    localStorage.setItem('token', authToken);
    localStorage.setItem('user', JSON.stringify({ id: 1, username: 'admin', is_admin: true }));
  }, token);
  
  console.log('✅ Token 已设置到 localStorage');
  
  // 刷新页面以使用 token
  await page.reload({ waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(3000);
  
  const results = [];
  const errors = [];
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push({ type: 'console', text: msg.text() });
    }
  });
  
  page.on('pageerror', err => {
    errors.push({ type: 'pageerror', message: err.message });
  });
  
  try {
    // 检查是否已登录
    const pageText = await page.evaluate(() => document.body.innerText);
    
    if (pageText.includes('自我驱动') || pageText.includes('SDS')) {
      console.log('✅ 已登录，SDS 页面加载成功');
      results.push({ test: 'SDS页面加载', status: 'PASS' });
      
      // 获取所有按钮
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
        console.log('🖱️ 点击历史趋势:', buttonTexts[historyIndex]);
        await buttons[historyIndex].click();
        await page.waitForTimeout(3000);
        
        // 检查错误
        const errorInfo = await page.evaluate(() => {
          const errorElements = document.querySelectorAll('[class*=error], .text-red-500, [class*=alert-error]');
          if (errorElements.length > 0) {
            return { hasError: true, text: errorElements[0].innerText.substring(0, 200) };
          }
          
          // 也检查 console.error
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
      
      await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/sds-api-auth.png', fullPage: true });
      
    } else if (pageText.includes('请登录')) {
      console.log('❌ 仍需要登录');
      results.push({ test: 'SDS页面加载', status: 'FAIL', reason: 'Token 无效' });
    } else {
      console.log('⚠️ 页面内容:', pageText.substring(0, 200));
      results.push({ test: 'SDS页面加载', status: 'FAIL', reason: '未知页面状态' });
    }
    
  } catch (e) {
    console.error('❌ 错误:', e.message);
    results.push({ test: '执行', status: 'FAIL', reason: e.message });
  }
  
  console.log('\n========================================');
  console.log('  KOI QA API Auth 报告');
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
