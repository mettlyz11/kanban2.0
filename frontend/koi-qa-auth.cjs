const { chromium } = require('playwright');

/**
 * KOI QA - 带登录验证（使用 admin/dudu2026）
 */

const LOGIN_URL = 'http://localhost/self-driving';
const USERNAME = 'admin';
const PASSWORD = 'dudu2026';

(async () => {
  console.log('🚀 KOI QA with Authentication');
  console.log('账号:', USERNAME);
  
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  
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
    // Step 1: 访问页面（会自动跳转到登录页）
    console.log('📝 Step 1: 访问页面...');
    await page.goto(LOGIN_URL, { 
      waitUntil: 'domcontentloaded', 
      timeout: 15000 
    });
    await page.waitForTimeout(2000);
    
    // Step 2: 检测是否需要登录
    const pageText = await page.evaluate(() => document.body.innerText);
    const needsLogin = pageText.includes('请登录') || pageText.includes('用户名');
    
    if (needsLogin) {
      console.log('🔐 需要登录，执行登录...');
      
      // 填写用户名
      const usernameInput = await page.locator('input[type=text]').first();
      await usernameInput.fill(USERNAME);
      console.log('✅ 用户名已填写');
      
      // 填写密码
      const passwordInput = await page.locator('input[type=password]').first();
      await passwordInput.fill(PASSWORD);
      console.log('✅ 密码已填写');
      
      // 处理验证码
      const captchaInput = await page.locator('input[placeholder*=验证码]').first();
      if (await captchaInput.isVisible().catch(() => false)) {
        // 获取验证码算式
        const captchaText = await page.locator('text=/[0-9]+\s*[-+]\s*[0-9]+/').first().textContent().catch(() => '');
        console.log('🧮 验证码:', captchaText);
        
        const match = captchaText.match(/(\d+)\s*([-+])\s*(\d+)/);
        if (match) {
          const num1 = parseInt(match[1]);
          const operator = match[2];
          const num2 = parseInt(match[3]);
          const answer = operator === '+' ? num1 + num2 : num1 - num2;
          await captchaInput.fill(answer.toString());
          console.log('✅ 验证码答案:', answer);
        }
      }
      
      // 点击登录
      const loginBtn = await page.locator('button:has-text(登录)').first();
      await loginBtn.click();
      console.log('🔄 登录中...');
      
      // 等待页面加载（跳转后）
      await page.waitForTimeout(3000);
      
      // 检查登录是否成功
      const newText = await page.evaluate(() => document.body.innerText);
      if (newText.includes('自我驱动') || newText.includes('SDS')) {
        console.log('✅ 登录成功！');
        results.push({ test: '登录流程', status: 'PASS' });
      } else {
        console.log('⚠️ 登录后未找到自我驱动系统内容');
        console.log('页面内容:', newText.substring(0, 200));
        results.push({ test: '登录流程', status: 'FAIL', reason: '登录后未显示SDS' });
      }
    } else {
      console.log('ℹ️ 不需要登录');
    }
    
    // Step 3: 验证 SDS 页面内容
    const currentText = await page.evaluate(() => document.body.innerText);
    
    if (currentText.includes('自我驱动')) {
      results.push({ test: 'SDS-页面加载', status: 'PASS' });
      
      // 获取所有按钮
      const buttons = await page.locator('button').all();
      const buttonTexts = [];
      for (const btn of buttons) {
        const text = await btn.textContent().catch(() => '');
        buttonTexts.push(text.trim());
      }
      
      console.log('📋 所有按钮:', buttonTexts);
      
      // 点击历史趋势（包含历史文字的按钮）
      const historyIndex = buttonTexts.findIndex(t => t.includes('历史'));
      if (historyIndex >= 0) {
        console.log('🖱️ 点击历史趋势按钮:', buttonTexts[historyIndex]);
        await buttons[historyIndex].click();
        await page.waitForTimeout(3000);
        
        // 检查是否有错误提示
        const errorElements = await page.locator('[class*=error], .text-red-500, .ant-alert-error').count();
        
        if (errorElements > 0) {
          const errorText = await page.locator('[class*=error], .text-red-500').first().textContent().catch(() => 'Error');
          console.log('❌ 发现错误:', errorText);
          results.push({ test: 'SDS-历史趋势', status: 'FAIL', reason: errorText });
        } else {
          // 检查内容是否渲染
          const hasChart = await page.locator('canvas, [class*=chart], svg').count() > 0;
          const hasTable = await page.locator('table, [class*=table]').count() > 0;
          const hasContent = await page.locator('h2').filter({ hasText: /趋势/ }).count() > 0;
          
          if (hasContent || hasChart || hasTable) {
            console.log('✅ 历史趋势内容已渲染');
            results.push({ test: 'SDS-历史趋势', status: 'PASS', detail: hasChart ? '图表' : '表格' });
          } else {
            console.log('⚠️ 历史趋势无内容');
            results.push({ test: 'SDS-历史趋势', status: 'WARN', reason: '无图表或表格数据' });
          }
        }
      } else {
        console.log('❌ 未找到历史按钮');
        results.push({ test: 'SDS-历史趋势', status: 'FAIL', reason: '未找到历史趋势按钮' });
      }
      
      // 截图保存
      await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/sds-history-auth.png', fullPage: true });
      
    } else {
      results.push({ test: 'SDS-页面加载', status: 'FAIL', reason: '未找到自我驱动系统内容' });
    }
    
  } catch (e) {
    console.error('❌ 执行错误:', e.message);
    results.push({ test: '执行', status: 'FAIL', reason: e.message });
  }
  
  // 报告输出
  console.log('\n========================================');
  console.log('  KOI QA with Auth 报告');
  console.log('========================================');
  
  let pass = 0, fail = 0, warn = 0;
  for (const r of results) {
    const icon = r.status === 'PASS' ? '✅' : r.status === 'FAIL' ? '❌' : '⚠️';
    console.log();
    if (r.status === 'PASS') pass++;
    else if (r.status === 'FAIL') fail++;
    else warn++;
  }
  
  console.log('----------------------------------------');
  console.log();
  
  if (errors.length > 0) {
    console.log('\n📋 JavaScript 错误:');
    errors.forEach(e => console.log('  ❌', e.text || e.message));
  } else {
    console.log('\n✅ 无 JavaScript 错误');
  }
  
  console.log('========================================');
  
  await browser.close();
})();
