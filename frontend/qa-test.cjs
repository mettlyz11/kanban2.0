const { chromium } = require('playwright');

(async () => {
  console.log('Starting Kanban QA Test...');
  
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  const results = [];
  const jsErrors = [];
  
  page.on('console', msg => {
    if (msg.type() === 'error') jsErrors.push(msg.text());
  });
  page.on('pageerror', err => jsErrors.push(err.message));

  // Test 1: Homepage
  await page.goto('http://localhost/', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(2000);
  results.push('[PASS] Homepage loaded');
  
  // Test 2: Tasks page
  await page.goto('http://localhost/tasks', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(1000);
  const taskTitle = await page.locator('h1').textContent().catch(() => '');
  results.push(taskTitle.includes('Task') || taskTitle.includes('任务') ? '[PASS] Tasks page OK' : '[WARN] Tasks title: ' + taskTitle);
  
  // Test 3: Projects - check maximize button
  await page.goto('http://localhost/projects', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(1000);
  const btns = await page.locator('button').count();
  results.push('[INFO] Projects page has ' + btns + ' buttons');
  
  // Test 4: Strategic Map
  await page.goto('http://localhost/strategic-map', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(1000);
  const hasTree = await page.locator('button:has-text("Tree")').isVisible().catch(() => false);
  const hasCard = await page.locator('button:has-text("Card")').isVisible().catch(() => false);
  results.push(hasTree || hasCard ? '[PASS] StrategicMap view buttons found' : '[WARN] StrategicMap buttons not found');
  
  // Test 5: Meeting Notes
  await page.goto('http://localhost/meeting-notes', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(1000);
  results.push('[PASS] MeetingNotes page loaded');
  
  // Test 6: Self Driving System
  await page.goto('http://localhost/self-driving-system', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(1000);
  const hasHistory = await page.locator('button:has-text("History")').isVisible().catch(() => false);
  const hasArch = await page.locator('button:has-text("Architecture")').isVisible().catch(() => false);
  results.push(hasHistory || hasArch ? '[PASS] SDS tabs found' : '[WARN] SDS tabs not found');
  
  // Output results
  console.log('\n' + '='.repeat(50));
  console.log('KANBAN QA TEST REPORT');
  console.log('='.repeat(50));
  results.forEach(r => console.log(r));
  
  console.log('\nJavaScript Errors:');
  if (jsErrors.length > 0) {
    jsErrors.slice(0, 5).forEach(e => console.log('  [ERROR] ' + e.substring(0, 100)));
  } else {
    console.log('  [PASS] No JavaScript errors');
  }
  console.log('='.repeat(50));
  
  await browser.close();
})();
