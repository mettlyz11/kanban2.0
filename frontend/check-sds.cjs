const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  await page.goto('http://localhost/self-driving', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(5000);
  
  // 获取完整文本
  const text = await page.evaluate(() => document.body.innerText);
  console.log('=== 页面完整文本 ===');
  console.log(text);
  console.log('=== 结束 ===');
  
  await browser.close();
})();
