const { chromium } = require('playwright');

const LOGIN_URL = 'http://localhost/self-driving';
const USERNAME = 'admin';
const PASSWORD = 'dudu2026';

(async () => {
  console.log('🚀 KOI QA with Auth v3 - 修复验证码');
  
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  const results = [];
  
  try {
    // 访问页面
    await page.goto(LOGIN_URL, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    // 检查是否需要登录
    const pageText = await page.evaluate(() => document.body.innerText);
    
    if (pageText.includes('请登录')) {
      console.log('🔐 需要登录');
      
      // 填写用户名和密码
      await page.locator('input[type="text"]').first().fill(USERNAME);
      await page.locator('input[type="password"]').first().fill(PASSWORD);
      console.log('✅ 用户名和密码已填写');
      
      // 获取验证码文本
      const pageHTML = await page.content();
      const textMatch = pageHTML.match(/(\d+)\s*([\+\-])\s*(\d+)\s*=?/);
      
      if (textMatch) {
        const num1 = parseInt(textMatch[1]);
        const op = textMatch[2];
        const num2 = parseInt(textMatch[3]);
        const answer = op === '+' ? num1 + num2 : num1 - num2;
        
        console.log('🧮 验证码:', num1, op, num2, '= ?');
        console.log('✅ 答案:', answer);
        
        // 填写验证码
        await page.locator('input[placeholder*="验证码"]').fill(answer.toString());
      } else {
        console.log('⚠️ 未找到验证码算式');
      }
      
      // 截图查看状态
      await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/login-form.png' });
      
      // 点击登录按钮
      const buttons = await page.locator('button').all();
      for (const btn of buttons) {
        const text = await btn.textContent().catch(() => '');
        if (text.trim() === '登录') {
          await btn.click();
          console.log('🔄 点击登录');
          break;
        }
      }
      
      // 等待页面跳转
      await page.waitForTimeout(5000);
      
      // 检查登录结果
      const newText = await page.evaluate(() => document.body.innerText);
      console.log('登录后页面内容 (前200字):', newText.substring(0, 200));
      
      if (newText.includes('自我驱动') || newText.includes('SDS') || newText.includes('系统状态')) {
        console.log('✅ 登录成功！');
        results.push({ test: '登录', status: 'PASS' });
        
        // 测试历史趋势
        const buttons = await page.locator('button').all();
        const buttonTexts = [];
        for (const btn of buttons) {
          const text = await btn.textContent().catch(() => '');
          buttonTexts.push(text.trim());
        }
        
        console.log('📋 按钮:', buttonTexts);
        
        const historyIndex = buttonTexts.findIndex(t => t.includes('历史'));
        if (historyIndex >= 0) {
          await buttons[historyIndex].click();
          console.log('🖱️ 点击历史趋势');
          await page.waitForTimeout(3000);
          
          // 检查错误
          const errorElements = await page.locator('[class*="error"], .text-red-500, [class*="alert"]').count();
          if (errorElements > 0) {
            const errorText = await page.locator('[class*="error"], .text-red-500').first().textContent();
            console.log('❌ 历史趋势错误:', errorText);
            results.push({ test: '历史趋势', status: 'FAIL', reason: errorText });
          } else {
            console.log('✅ 历史趋势正常');
            results.push({ test: '历史趋势', status: 'PASS' });
          }
        } else {
          results.push({ test: '历史趋势', status: 'FAIL', reason: '未找到按钮' });
        }
        
        await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/sds-logged-in.png', fullPage: true });
      } else {
        console.log('❌ 登录失败，仍在登录页面');
        results.push({ test: '登录', status: 'FAIL', reason: '可能验证码错误或账号问题' });
        await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/login-failed.png', fullPage: true });
      }
    } else {
      console.log('✅ 不需要登录');
    }
    
  } catch (e) {
    console.error('❌ 执行错误:', e.message);
    results.push({ test: '执行', status: 'FAIL', reason: e.message });
  }
  
  // 报告
  console.log('\n========================================');
  console.log('  KOI QA Auth v3 报告');
  console.log('========================================');
  for (const r of results) {
    const icon = r.status === 'PASS' ? '✅' : '❌';
    console.log();
  }
  console.log('========================================');
  
  await browser.close();
})();
