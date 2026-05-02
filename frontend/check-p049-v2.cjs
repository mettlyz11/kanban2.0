const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('Console:', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('PageError:', err.message));
  
  await page.goto('http://localhost/p049', { waitUntil: 'networkidle', timeout: 20000 });
  await page.waitForTimeout(5000);
  
  const text = await page.evaluate(() => document.body.innerText);
  const html = await page.content();
  
  console.log('Body text length:', text.length);
  console.log('Body text:', text.substring(0, 500));
  console.log('');
  console.log('HTML length:', html.length);
  console.log('Has #root content:', html.includes('P049') || html.includes('p049'));
  
  await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/p049-v2.png', fullPage: true });
  
  await browser.close();
})();
