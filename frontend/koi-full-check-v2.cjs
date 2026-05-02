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
  const res = await fetch(, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: 'dudu2026' })
  });
  const data = await res.json();
  return data.success ? data.token : null;
}

async function checkRoute(page, route, token) {
  try {
    // 先访问页面（不等待资源加载）
    await page.goto(, { 
      waitUntil: 'commit', 
      timeout: 10000 
    });
    
    // 然后设置 token
    if (token) {
      await page.evaluate((t) => {
        localStorage.setItem('kanban_token', t);
      }, token);
    }
    
    // 刷新页面使用 token
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 15000 });
    await page.waitForTimeout(2000);
    
    const status = 200;
    const title = await page.title().catch(() => 'No title');
    const pageText = await page.evaluate(() => document.body.innerText).catch(() => '');
    
    const isLoginPage = pageText.includes('请登录') || pageText.includes('用户名');
    const hasContent = pageText.length > 100;
    
    return {
      route,
      status,
      title: title.substring(0, 50),
      isLoginPage,
      hasContent,
      ok: !isLoginPage && hasContent
    };
  } catch (e) {
    return {
      route,
      status: 0,
      title: 'Error',
      isLoginPage: false,
      hasContent: false,
      ok: false,
      error: e.message
    };
  }
}

async function checkAPI(endpoint) {
  try {
    const res = await fetch(, { timeout: 10000 });
    return { endpoint, status: res.status, ok: res.ok, error: null };
  } catch (e) {
    return { endpoint, status: 0, ok: false, error: e.message };
  }
}

(async () => {
  console.log('🚀 KOI Full Check v2');
  console.log();
  
  const token = await apiLogin();
  if (!token) { console.log('❌ 登录失败'); process.exit(1); }
  console.log('✅ 登录成功');
  console.log('');
  
  const browser = await chromium.launch({ headless: true });
  
  const results = { pages: [], apis: [], summary: { pass: 0, login: 0, fail: 0 } };
  
  console.log('📄 检查页面...');
  for (let i = 0; i < ROUTES.length; i++) {
    const route = ROUTES[i];
    process.stdout.write();
    
    const context = await browser.newContext();
    const page = await context.newPage();
    const result = await checkRoute(page, route, token);
    results.pages.push(result);
    
    if (result.ok) {
      results.summary.pass++;
      process.stdout.write('✅\n');
    } else if (result.isLoginPage) {
      results.summary.login++;
      process.stdout.write('🔐 登录页\n');
    } else {
      results.summary.fail++;
      process.stdout.write();
    }
    
    await context.close();
  }
  
  console.log('');
  console.log('🔌 检查 API...');
  for (const endpoint of API_ENDPOINTS) {
    process.stdout.write();
    const result = await checkAPI(endpoint);
    results.apis.push(result);
    process.stdout.write(result.ok ? '✅\n' : );
  }
  
  await browser.close();
  
  console.log('');
  console.log('========================================');
  console.log('  KOI Full Check v2 报告');
  console.log('========================================');
  console.log();
  console.log();
  console.log('');
  
  const failedPages = results.pages.filter(r => !r.ok && !r.isLoginPage);
  if (failedPages.length > 0) {
    console.log('❌ 失败页面:');
    failedPages.forEach(r => console.log());
  }
  
  const failedAPIs = results.apis.filter(r => !r.ok);
  if (failedAPIs.length > 0) {
    console.log('❌ 失败 API:');
    failedAPIs.forEach(r => console.log());
  }
  
  console.log('========================================');
  
  fs.writeFileSync('/opt/kanban-react/qa-reports/full-check-v2.json', JSON.stringify(results, null, 2));
  
  if (failedPages.length > 0 || failedAPIs.length > 0) {
    process.exit(1);
  }
})();
