const { chromium } = require('playwright');
const fs = require('fs');

/**
 * KOI Full Check - 检查看板系统所有路由
 * 1. 检查所有页面是否可以加载
 * 2. 检查需要登录的页面
 * 3. 检查 API 端点
 * 4. 检查 JavaScript 错误
 */

const BASE_URL = 'http://localhost';
const USERNAME = 'admin';
const PASSWORD = 'dudu2026';

// 所有路由
const ROUTES = [
  '/',
  '/architecture',
  '/brain',
  '/calc-tasks',
  '/calendar',
  '/chat',
  '/communication',
  '/company',
  '/company/helight',
  '/cron',
  '/daily-reviews',
  '/dashboard',
  '/emails',
  '/goals',
  '/health',
  '/llm-configs',
  '/login',
  '/meetings',
  '/molecules',
  '/my-goals',
  '/p049',
  '/p049/login',
  '/p049/members',
  '/p049/profile',
  '/pepi',
  '/perception',
  '/perception-monitor',
  '/personal',
  '/personal/2',
  '/personal/3',
  '/personal/4',
  '/project-design',
  '/projects',
  '/reactions',
  '/research',
  '/resources',
  '/review',
  '/self-driving',
  '/settings',
  '/skills',
  '/stocks',
  '/strategic-map',
  '/system-monitor',
  '/tasks',
  '/users',
];

// API 端点
const API_ENDPOINTS = [
  '/api/tasks?page=1&per_page=1',
  '/api/sds/stats',
  '/api/sds/history',
  '/api/projects',
  '/api/meetings',
  '/api/users',
  '/api/health',
  '/api/goals',
  '/api/dashboard/stats',
  '/api/system-monitor',
];

async function apiLogin() {
  const res = await fetch(`${BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: USERNAME, password: PASSWORD })
  });
  const data = await res.json();
  return data.success ? data.token : null;
}

async function checkRoute(page, route, token) {
  const errors = [];
  const consoleErrors = [];
  
  const handleConsole = msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  };
  
  const handlePageError = err => {
    errors.push(err.message);
  };
  
  page.on('console', handleConsole);
  page.on('pageerror', handlePageError);
  
  try {
    // 设置 token
    if (token) {
      await page.evaluate((t) => {
        localStorage.setItem('kanban_token', t);
      }, token);
    }
    
    const response = await page.goto(`${BASE_URL}${route}`, { 
      waitUntil: 'domcontentloaded', 
      timeout: 15000 
    });
    
    await page.waitForTimeout(2000);
    
    const status = response.status();
    const title = await page.title().catch(() => 'No title');
    const pageText = await page.evaluate(() => document.body.innerText).catch(() => '');
    
    // 判断是否被重定向到登录页
    const isLoginPage = pageText.includes('请登录') || pageText.includes('用户名');
    
    page.off('console', handleConsole);
    page.off('pageerror', handlePageError);
    
    return {
      route,
      status,
      title,
      isLoginPage,
      hasErrors: errors.length > 0 || consoleErrors.length > 0,
      errors: [...errors, ...consoleErrors].slice(0, 5),
      ok: status === 200 && !isLoginPage
    };
  } catch (e) {
    page.off('console', handleConsole);
    page.off('pageerror', handlePageError);
    
    return {
      route,
      status: 0,
      title: 'Error',
      isLoginPage: false,
      hasErrors: true,
      errors: [e.message],
      ok: false
    };
  }
}

async function checkAPI(endpoint) {
  try {
    const res = await fetch(`${BASE_URL}${endpoint}`, { timeout: 10000 });
    return {
      endpoint,
      status: res.status,
      ok: res.ok,
      error: null
    };
  } catch (e) {
    return {
      endpoint,
      status: 0,
      ok: false,
      error: e.message
    };
  }
}

(async () => {
  console.log('🚀 KOI Full Check - 看板系统完整检查');
  console.log(`📋 检查 ${ROUTES.length} 个路由 + ${API_ENDPOINTS.length} 个 API`);
  console.log('');
  
  // API 登录
  console.log('🔐 登录获取 token...');
  const token = await apiLogin();
  if (!token) {
    console.log('❌ 登录失败');
    process.exit(1);
  }
  console.log('✅ 登录成功');
  console.log('');
  
  const browser = await chromium.launch({ headless: true });
  
  const results = {
    pages: [],
    apis: [],
    summary: { pass: 0, fail: 0, loginRequired: 0, error: 0 }
  };
  
  // 检查所有路由
  console.log('📄 检查页面路由...');
  for (let i = 0; i < ROUTES.length; i++) {
    const route = ROUTES[i];
    process.stdout.write(`  [${i + 1}/${ROUTES.length}] ${route} ... `);
    
    const context = await browser.newContext();
    const page = await context.newPage();
    
    const result = await checkRoute(page, route, token);
    results.pages.push(result);
    
    if (result.ok) {
      results.summary.pass++;
      process.stdout.write('✅\n');
    } else if (result.isLoginPage) {
      results.summary.loginRequired++;
      process.stdout.write('🔐 需要登录\n');
    } else if (result.status === 0) {
      results.summary.error++;
      process.stdout.write(`❌ ${result.errors[0]}\n`);
    } else {
      results.summary.fail++;
      process.stdout.write(`❌ HTTP ${result.status}\n`);
    }
    
    await context.close();
  }
  
  console.log('');
  console.log('🔌 检查 API 端点...');
  
  // 检查所有 API
  for (let i = 0; i < API_ENDPOINTS.length; i++) {
    const endpoint = API_ENDPOINTS[i];
    process.stdout.write(`  [${i + 1}/${API_ENDPOINTS.length}] ${endpoint} ... `);
    
    const result = await checkAPI(endpoint);
    results.apis.push(result);
    
    if (result.ok) {
      process.stdout.write('✅\n');
    } else {
      process.stdout.write(`❌ HTTP ${result.status}${result.error ? ' - ' + result.error : ''}\n`);
    }
  }
  
  await browser.close();
  
  // 生成报告
  console.log('');
  console.log('========================================');
  console.log('  KOI Full Check 报告');
  console.log('========================================');
  console.log(`页面检查: ${results.summary.pass} 通过, ${results.summary.loginRequired} 需登录, ${results.summary.fail} 失败, ${results.summary.error} 错误`);
  console.log('');
  
  // 显示失败的页面
  const failedPages = results.pages.filter(r => !r.ok && !r.isLoginPage);
  if (failedPages.length > 0) {
    console.log('❌ 失败的页面:');
    failedPages.forEach(r => {
      console.log(`  - ${r.route}: HTTP ${r.status}${r.errors.length > 0 ? ' - ' + r.errors[0] : ''}`);
    });
    console.log('');
  }
  
  // 显示需要登录的页面
  const loginPages = results.pages.filter(r => r.isLoginPage);
  if (loginPages.length > 0) {
    console.log('🔐 需要登录的页面:');
    loginPages.forEach(r => {
      console.log(`  - ${r.route}`);
    });
    console.log('');
  }
  
  // 显示失败的 API
  const failedAPIs = results.apis.filter(r => !r.ok);
  if (failedAPIs.length > 0) {
    console.log('❌ 失败的 API:');
    failedAPIs.forEach(r => {
      console.log(`  - ${r.endpoint}: HTTP ${r.status}${r.error ? ' - ' + r.error : ''}`);
    });
    console.log('');
  }
  
  console.log('========================================');
  
  // 保存报告
  fs.writeFileSync('/opt/kanban-react/qa-reports/full-check-report.json', JSON.stringify(results, null, 2));
  console.log('📄 报告已保存: /opt/kanban-react/qa-reports/full-check-report.json');
  
  // 如果有失败，退出码设为 1
  if (failedPages.length > 0 || failedAPIs.length > 0) {
    process.exit(1);
  }
})();
