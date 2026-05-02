const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  const consoleErrors = [];
  page.on('console', msg => {
    console.log('Console:', msg.type(), msg.text());
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', err => console.log('PageError:', err.message));
  page.on('response', response => {
    if (!response.ok() && response.url().includes('p049')) {
      console.log('Failed:', response.status(), response.url());
    }
  });
  
  await page.goto('http://localhost/p049', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(5000);
  
  const text = await page.evaluate(() => document.body.innerText);
  console.log('');
  console.log('Body text:', text.substring(0, 500));
  console.log('Text length:', text.length);
  console.log('Console errors:', consoleErrors.length);
  
  await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/p049-v3.png', fullPage: true });
  
  await browser.close();
})();
