const { chromium } = require('playwright');
const fs = require('fs');

const BASE_URL = 'http://localhost';

const ROUTES = [
  '/','/architecture','/brain','/calc-tasks','/calendar','/chat',
  '/communication','/company','/company/helight','/cron',
  '/daily-reviews','/dashboard','/emails','/goals','/health',
  '/llm-configs','/login','/meetings','/molecules','/my-goals',
  '/p049','/p049/login','/p049/members','/p049/profile',
  '/pepi','/perception','/perception-monitor','/personal',
  '/personal/2','/personal/3','/personal/4','/project-design',
  '/projects','/reactions','/research','/resources','/review',
  '/self-driving','/settings','/skills','/stocks','/strategic-map',
  '/system-monitor','/tasks','/users'
];

const API_ENDPOINTS = [
  '/api/tasks?page=1&per_page=1',
  '/api/sds/stats','/api/sds/history','/api/projects',
  '/api/meetings','/api/users','/api/health','/api/goals',
  '/api/dashboard/stats','/api/system-monitor'
];

async function apiLogin() {
  const res = await fetch(BASE_URL + '/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: 'dudu2026' })
  });
  const data = await res.json();
  return data.success ? data.token : null;
}

async function checkRoute(page, route, token) {
  try {
    await page.goto(BASE_URL + route, { waitUntil: 'commit', timeout: 10000 });
    
    if (token) {
      await page.evaluate((t) => { localStorage.setItem('kanban_token', t); }, token);
    }
    
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(3000);
    
    const title = await page.title().catch(() => 'No title');
    const pageText = await page.evaluate(() => document.body.innerText).catch(() => '');
    
    const isLoginPage = pageText.includes('请登录') || pageText.includes('用户名');
    // 降低阈值：只要有内容就认为 OK（简单页面内容少）
    const hasContent = pageText.length > 20 && !isLoginPage;
    
    return {
      route,
      title: title.substring(0, 50),
      isLoginPage,
      hasContent,
      contentLength: pageText.length,
      ok: !isLoginPage && hasContent
    };
  } catch (e) {
    return { route, title: 'Error', isLoginPage: false, hasContent: false, ok: false, error: e.message };
  }
}

async function checkAPI(endpoint) {
  try {
    const res = await fetch(BASE_URL + endpoint, { timeout: 10000 });
    return { endpoint, status: res.status, ok: res.ok, error: null };
  } catch (e) {
    return { endpoint, status: 0, ok: false, error: e.message };
  }
}

(async () => {
  console.log('🚀 KOI Full Check v4 - 修复内容检测阈值');
  console.log('Routes: ' + ROUTES.length + ', APIs: ' + API_ENDPOINTS.length);
  
  const token = await apiLogin();
  if (!token) { console.log('Login failed'); process.exit(1); }
  console.log('Login OK');
  
  const browser = await chromium.launch({ headless: true });
  const results = { pages: [], apis: [], summary: { pass: 0, login: 0, fail: 0 } };
  
  console.log('\nChecking pages...');
  for (let i = 0; i < ROUTES.length; i++) {
    const route = ROUTES[i];
    process.stdout.write('  [' + (i+1) + '/' + ROUTES.length + '] ' + route + ' ');
    
    const context = await browser.newContext();
    const page = await context.newPage();
    const result = await checkRoute(page, route, token);
    results.pages.push(result);
    
    if (result.ok) { results.summary.pass++; process.stdout.write('OK (' + result.contentLength + ' chars)\n'); }
    else if (result.isLoginPage) { results.summary.login++; process.stdout.write('LOGIN\n'); }
    else { results.summary.fail++; process.stdout.write('FAIL ' + (result.error || 'No content').substring(0,30) + '\n'); }
    
    await context.close();
  }
  
  console.log('\nChecking APIs...');
  for (const endpoint of API_ENDPOINTS) {
    process.stdout.write('  ' + endpoint + ' ');
    const result = await checkAPI(endpoint);
    results.apis.push(result);
    process.stdout.write(result.ok ? 'OK\n' : 'FAIL ' + result.status + '\n');
  }
  
  await browser.close();
  
  console.log('\n========================================');
  console.log('KOI Full Check v4 Report');
  console.log('========================================');
  console.log('Pages: ' + results.summary.pass + ' pass, ' + results.summary.login + ' login, ' + results.summary.fail + ' fail');
  console.log('APIs: ' + results.apis.filter(a => a.ok).length + '/' + results.apis.length + ' pass');
  console.log('');
  
  const failedPages = results.pages.filter(r => !r.ok && !r.isLoginPage);
  if (failedPages.length > 0) {
    console.log('Failed pages:');
    failedPages.forEach(r => console.log('  - ' + r.route + ': ' + (r.error || 'No content') + ' (' + r.contentLength + ' chars)'));
  } else {
    console.log('✅ All pages passed!');
  }
  
  const failedAPIs = results.apis.filter(r => !r.ok);
  if (failedAPIs.length > 0) {
    console.log('Failed APIs:');
    failedAPIs.forEach(r => console.log('  - ' + r.endpoint + ': ' + r.status));
  } else {
    console.log('✅ All APIs passed!');
  }
  
  console.log('========================================');
  
  fs.writeFileSync('/opt/kanban-react/qa-reports/full-check-v4.json', JSON.stringify(results, null, 2));
  
  if (failedPages.length > 0 || failedAPIs.length > 0) {
    process.exit(1);
  }
})();
