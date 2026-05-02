const { chromium } = require('playwright');

(async () => {
  console.log('🚀 KOI QA Final - 修复参数问题');
  
  // Step 1: API 登录
  console.log('🔐 API 登录...');
  
  const loginResponse = await fetch('http://localhost/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: 'dudu2026' })
  });
  
  const loginData = await loginResponse.json();
  
  if (!loginData.success) {
    console.log('❌ API 登录失败');
    process.exit(1);
  }
  
  console.log('✅ API 登录成功');
  
  // Step 2: 使用 Playwright
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  await page.goto('http://localhost/self-driving', { waitUntil: 'domcontentloaded', timeout: 15000 });
  
  // 只传递一个参数（对象）
  await page.evaluate((data) => {
    localStorage.setItem('kanban_token', data.token);
    localStorage.setItem('kanban_user', JSON.stringify(data.user));
  }, { token: loginData.token, user: loginData.user });
  
  console.log('✅ Token 已设置');
  
  // 刷新页面
  await page.reload({ waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(3000);
  
  const results = [];
  
  try {
    const pageText = await page.evaluate(() => document.body.innerText);
    
    if (pageText.includes('自我驱动')) {
      console.log('✅ SDS 页面加载成功');
      results.push({ test: 'SDS页面', status: 'PASS' });
      
      // 获取所有按钮文字
      const buttonTexts = await page.evaluate(() => {
        return Array.from(document.querySelectorAll('button')).map(b => b.innerText.trim());
      });
      
      console.log('📋 按钮:', buttonTexts);
      
      // 点击历史趋势
      const historyIndex = buttonTexts.findIndex(t => t.includes('历史'));
      if (historyIndex >= 0) {
        await page.evaluate((index) => {
          document.querySelectorAll('button')[index].click();
        }, historyIndex);
        
        console.log('🖱️ 点击历史趋势');
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
    } else {
      console.log('❌ 页面未显示自我驱动系统');
      console.log('内容:', pageText.substring(0, 200));
      results.push({ test: 'SDS页面', status: 'FAIL', reason: '未加载' });
    }
    
  } catch (e) {
    console.error('❌ 错误:', e.message);
    results.push({ test: '执行', status: 'FAIL', reason: e.message });
  }
  
  console.log('\n========================================');
  console.log('  KOI QA Final 报告');
  console.log('========================================');
  for (const r of results) {
    const icon = r.status === 'PASS' ? '✅' : '❌';
    console.log();
  }
  console.log('========================================');
  
  await browser.close();
})();
