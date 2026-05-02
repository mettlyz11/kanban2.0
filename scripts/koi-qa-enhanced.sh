#!/bin/bash
# KOI QA 增强版 - 带登录验证

KANBAN_URL="http://localhost/self-driving"
USERNAME="admin"
PASSWORD="dudu2026"

echo "🚀 KOI QA Enhanced - 带认证"
echo "账号: $USERNAME"
echo "" 

# 创建 Node.js 测试脚本
cat > /tmp/koi-qa-test.cjs << 'EOF'
const { chromium } = require('playwright');

(async () => {
  console.log('🔐 Step 1: API 登录...');
  
  const loginRes = await fetch('http://localhost/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: 'dudu2026' })
  });
  const loginData = await loginRes.json();
  
  if (!loginData.success) {
    console.log('❌ 登录失败');
    process.exit(1);
  }
  
  console.log('✅ 登录成功');
  
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  await page.goto('http://localhost/self-driving', { waitUntil: 'domcontentloaded', timeout: 15000 });
  
  await page.evaluate((data) => {
    localStorage.setItem('kanban_token', data.token);
    localStorage.setItem('kanban_user', JSON.stringify(data.user));
  }, { token: loginData.token, user: loginData.user });
  
  await page.reload({ waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(3000);
  
  const results = [];
  
  try {
    const pageText = await page.evaluate(() => document.body.innerText);
    
    if (pageText.includes('自我驱动')) {
      results.push({ test: 'SDS页面', status: 'PASS' });
      
      // 测试历史趋势
      const buttons = await page.evaluate(() => 
        Array.from(document.querySelectorAll('button')).map(b => b.innerText.trim())
      );
      
      const historyIndex = buttons.findIndex(t => t.includes('历史'));
      if (historyIndex >= 0) {
        await page.evaluate((idx) => document.querySelectorAll('button')[idx].click(), historyIndex);
        await page.waitForTimeout(3000);
        
        const errorInfo = await page.evaluate(() => {
          const errors = document.querySelectorAll('[class*="error"], .text-red-500');
          return errors.length > 0 ? { hasError: true, text: errors[0].innerText } : { hasError: false };
        });
        
        if (errorInfo.hasError) {
          results.push({ test: '历史趋势', status: 'FAIL', reason: errorInfo.text });
        } else {
          results.push({ test: '历史趋势', status: 'PASS' });
        }
      }
      
      await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/sds-enhanced.png', fullPage: true });
    }
  } catch (e) {
    results.push({ test: '执行', status: 'FAIL', reason: e.message });
  }
  
  console.log('\n========================================');
  console.log('  KOI QA Enhanced 报告');
  console.log('========================================');
  results.forEach(r => {
    const icon = r.status === 'PASS' ? '✅' : '❌';
    console.log(`${icon} ${r.test}: ${r.status}${r.reason ? ' - ' + r.reason : ''}`);
  });
  console.log('========================================');
  
  await browser.close();
})();
EOF

cd /opt/kanban-react/frontend && node /tmp/koi-qa-test.cjs 2>&1
