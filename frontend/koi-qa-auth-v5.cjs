const { chromium } = require('playwright');

const LOGIN_URL = 'http://localhost/self-driving';
const CREDENTIALS = { username: 'admin', password: 'dudu2026' };

(async () => {
  console.log('🚀 KOI QA Auth v5');
  
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  const results = [];
  
  try {
    await page.goto(LOGIN_URL, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    const pageText = await page.evaluate(() => document.body.innerText);
    
    if (pageText.includes('请登录')) {
      console.log('🔐 需要登录');
      
      // 使用 evaluate 直接操作 DOM
      await page.evaluate((creds) => {
        const inputs = document.querySelectorAll('input');
        let userInput, passInput, captchaInput;
        
        inputs.forEach(input => {
          if (input.type === 'text') userInput = input;
          if (input.type === 'password') passInput = input;
          if (input.placeholder && input.placeholder.includes('验证码')) captchaInput = input;
        });
        
        if (userInput) userInput.value = creds.username;
        if (passInput) passInput.value = creds.password;
        
        if (captchaInput) {
          const text = document.body.innerText;
          const match = text.match(/(\d+)\s*([\+\-])\s*(\d+)\s*=?/);
          if (match) {
            const num1 = parseInt(match[1]);
            const op = match[2];
            const num2 = parseInt(match[3]);
            const answer = op === '+' ? num1 + num2 : num1 - num2;
            captchaInput.value = answer.toString();
          }
        }
        
        // 触发事件
        [userInput, passInput, captchaInput].forEach(input => {
          if (input) {
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
          }
        });
        
        // 点击登录
        const buttons = document.querySelectorAll('button');
        for (const btn of buttons) {
          if (btn.innerText.includes('登录')) {
            btn.click();
            break;
          }
        }
      }, CREDENTIALS);
      
      console.log('🔄 登录中...');
      await page.waitForTimeout(5000);
      
      // 检查登录结果
      const newText = await page.evaluate(() => document.body.innerText);
      console.log('页面内容:', newText.substring(0, 300));
      
      if (newText.includes('自我驱动')) {
        console.log('✅ 登录成功');
        results.push({ test: '登录', status: 'PASS' });
        
        // 点击历史趋势
        await page.evaluate(() => {
          const buttons = document.querySelectorAll('button');
          for (const btn of buttons) {
            if (btn.innerText.includes('历史')) {
              btn.click();
              break;
            }
          }
        });
        
        await page.waitForTimeout(3000);
        
        // 检查错误
        const errorInfo = await page.evaluate(() => {
          const errorElements = document.querySelectorAll('[class*=error], .text-red-500, [class*=alert-error]');
          if (errorElements.length > 0) {
            return { hasError: true, text: errorElements[0].innerText };
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
        
        await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/sds-auth-success.png', fullPage: true });
      } else {
        console.log('❌ 登录失败');
        results.push({ test: '登录', status: 'FAIL', reason: '仍在登录页面' });
        await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/login-failed.png', fullPage: true });
      }
    }
    
  } catch (e) {
    console.error('❌ 错误:', e.message);
    results.push({ test: '执行', status: 'FAIL', reason: e.message });
  }
  
  console.log('\n========================================');
  console.log('  KOI QA Auth v5 报告');
  console.log('========================================');
  for (const r of results) {
    const icon = r.status === 'PASS' ? '✅' : '❌';
    console.log();
  }
  console.log('========================================');
  
  await browser.close();
})();
