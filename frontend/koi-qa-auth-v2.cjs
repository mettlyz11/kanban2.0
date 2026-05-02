const { chromium } = require('playwright');

const LOGIN_URL = 'http://localhost/self-driving';
const USERNAME = 'admin';
const PASSWORD = 'dudu2026';

(async () => {
  console.log('🚀 KOI QA with Auth v2');
  
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  const results = [];
  const errors = [];
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push({ type: 'console', text: msg.text() });
      console.log('❌ Console Error:', msg.text());
    }
  });
  
  page.on('pageerror', err => {
    errors.push({ type: 'pageerror', message: err.message });
    console.log('❌ Page Error:', err.message);
  });

  try {
    // Step 1: 访问页面
    console.log('Step 1: 访问页面...');
    await page.goto(LOGIN_URL, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    // Step 2: 检查是否需要登录
    const pageText = await page.evaluate(() => document.body.innerText);
    const needsLogin = pageText.includes('请登录') || pageText.includes('用户名');
    
    if (needsLogin) {
      console.log('🔐 需要登录...');
      
      // 填写用户名
      await page.locator('input[type="text"]').first().fill(USERNAME);
      console.log('✅ 用户名');
      
      // 填写密码
      await page.locator('input[type="password"]').first().fill(PASSWORD);
      console.log('✅ 密码');
      
      // 处理验证码
      const captchaInput = await page.locator('input[placeholder*="验证码"]').first();
      if (await captchaInput.isVisible().catch(() => false)) {
        const captchaText = await page.locator('text=/[0-9]+\s*[-+]\s*[0-9]+/').first().textContent().catch(() => '');
        console.log('🧮 验证码:', captchaText);
        
        const match = captchaText.match(/(\d+)\s*([-+])\s*(\d+)/);
        if (match) {
          const answer = match[2] === '+' ? parseInt(match[1]) + parseInt(match[3]) : parseInt(match[1]) - parseInt(match[3]);
          await captchaInput.fill(answer.toString());
          console.log('✅ 验证码答案:', answer);
        }
      }
      
      // 点击登录按钮（使用更通用的选择器）
      const buttons = await page.locator('button').all();
      for (const btn of buttons) {
        const text = await btn.textContent().catch(() => '');
        if (text.includes('登录')) {
          await btn.click();
          console.log('🔄 点击登录...');
          break;
        }
      }
      
      await page.waitForTimeout(3000);
      
      // 检查登录结果
      const newText = await page.evaluate(() => document.body.innerText);
      if (newText.includes('自我驱动') || newText.includes('SDS')) {
        console.log('✅ 登录成功！');
        results.push({ test: '登录', status: 'PASS' });
      } else {
        console.log('⚠️ 登录后内容:', newText.substring(0, 300));
        results.push({ test: '登录', status: 'FAIL', reason: '未显示SDS' });
      }
    }
    
    // Step 3: 测试历史趋势
    const currentText = await page.evaluate(() => document.body.innerText);
    
    if (currentText.includes('自我驱动')) {
      results.push({ test: 'SDS页面', status: 'PASS' });
      
      // 获取所有按钮
      const buttons = await page.locator('button').all();
      const buttonTexts = [];
      for (const btn of buttons) {
        const text = await btn.textContent().catch(() => '');
        buttonTexts.push(text.trim());
      }
      
      console.log('📋 按钮列表:', buttonTexts);
      
      // 点击历史趋势
      const historyIndex = buttonTexts.findIndex(t => t.includes('历史'));
      if (historyIndex >= 0) {
        console.log('🖱️ 点击:', buttonTexts[historyIndex]);
        await buttons[historyIndex].click();
        await page.waitForTimeout(3000);
        
        // 检查错误
        const errorCount = await page.locator('[class*="error"], .text-red-500').count();
        if (errorCount > 0) {
          const errorText = await page.locator('[class*="error"], .text-red-500').first().textContent();
          console.log('❌ 错误:', errorText);
          results.push({ test: '历史趋势', status: 'FAIL', reason: errorText });
        } else {
          results.push({ test: '历史趋势', status: 'PASS' });
        }
      } else {
        results.push({ test: '历史趋势', status: 'FAIL', reason: '未找到按钮' });
      }
      
      await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/sds-auth.png', fullPage: true });
    }
    
  } catch (e) {
    console.error('❌ 错误:', e.message);
    results.push({ test: '执行', status: 'FAIL', reason: e.message });
  }
  
  // 输出报告
  console.log('\n========================================');
  console.log('  KOI QA with Auth v2 报告');
  console.log('========================================');
  for (const r of results) {
    const icon = r.status === 'PASS' ? '✅' : '❌';
    console.log();
  }
  if (errors.length > 0) {
    console.log('\n❌ JavaScript 错误:');
    errors.forEach(e => console.log('  ', e.text || e.message));
  }
  console.log('========================================');
  
  await browser.close();
})();
