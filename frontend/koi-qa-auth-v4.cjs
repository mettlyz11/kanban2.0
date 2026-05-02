const { chromium } = require('playwright');

const LOGIN_URL = 'http://localhost/self-driving';
const USERNAME = 'admin';
const PASSWORD = 'dudu2026';

(async () => {
  console.log('🚀 KOI QA Auth v4 - 简化版');
  
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  const results = [];
  
  try {
    // 访问页面
    await page.goto(LOGIN_URL, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    const pageText = await page.evaluate(() => document.body.innerText);
    
    if (pageText.includes('请登录')) {
      console.log('🔐 需要登录');
      
      // 使用 evaluate 直接操作 DOM（更可靠）
      await page.evaluate((user, pass) => {
        // 找到所有 input
        const inputs = document.querySelectorAll('input');
        let userInput, passInput, captchaInput;
        
        inputs.forEach(input => {
          const type = input.type;
          const placeholder = input.placeholder || '';
          
          if (type === 'text') userInput = input;
          if (type === 'password') passInput = input;
          if (placeholder.includes('验证码') || placeholder.includes('captcha')) captchaInput = input;
        });
        
        // 填写用户名和密码
        if (userInput) userInput.value = user;
        if (passInput) passInput.value = pass;
        
        // 计算验证码
        if (captchaInput) {
          // 查找包含算式的文本
          const text = document.body.innerText;
          const match = text.match(/(\d+)\s*([\+\-])\s*(\d+)\s*=?/);
          if (match) {
            const num1 = parseInt(match[1]);
            const op = match[2];
            const num2 = parseInt(match[3]);
            const answer = op === '+' ? num1 + num2 : num1 - num2;
            captchaInput.value = answer.toString();
            console.log('验证码答案:', answer);
          }
        }
        
        // 触发 input 事件
        [userInput, passInput, captchaInput].forEach(input => {
          if (input) {
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
          }
        });
        
        // 点击登录按钮
        const buttons = document.querySelectorAll('button');
        for (const btn of buttons) {
          if (btn.innerText.includes('登录')) {
            btn.click();
            break;
          }
        }
      }, USERNAME, PASSWORD);
      
      console.log('🔄 登录中...');
      await page.waitForTimeout(5000);
      
      // 检查结果
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
        const hasError = await page.evaluate(() => {
          const errorElements = document.querySelectorAll('[class*=error], .text-red-500, [class*=alert]');
          return errorElements.length > 0;
        });
        
        if (hasError) {
          const errorText = await page.evaluate(() => {
            const el = document.querySelector('[class*=error], .text-red-500');
            return el ? el.innerText : 'Unknown error';
          });
          console.log('❌ 历史趋势错误:', errorText);
          results.push({ test: '历史趋势', status: 'FAIL', reason: errorText });
        } else {
          console.log('✅ 历史趋势正常');
          results.push({ test: '历史趋势', status: 'PASS' });
        }
        
        await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/sds-final.png', fullPage: true });
      } else {
        console.log('❌ 登录失败');
        results.push({ test: '登录', status: 'FAIL', reason: '仍在登录页面' });
        await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/login-fail.png', fullPage: true });
      }
    }
    
  } catch (e) {
    console.error('❌ 错误:', e.message);
    results.push({ test: '执行', status: 'FAIL', reason: e.message });
  }
  
  console.log('\n========================================');
  console.log('  KOI QA Auth v4 报告');
  console.log('========================================');
  for (const r of results) {
    const icon = r.status === 'PASS' ? '✅' : '❌';
    console.log();
  }
  console.log('========================================');
  
  await browser.close();
})();
