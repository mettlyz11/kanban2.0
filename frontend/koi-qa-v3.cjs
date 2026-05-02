const { chromium } = require('playwright');

(async () => {
  console.log('🚀 KOI QA v3 - 调试版');
  
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  page.on('console', msg => {
    console.log('Console:', msg.type(), msg.text());
  });
  
  page.on('pageerror', err => {
    console.log('PageError:', err.message);
  });

  await page.goto('http://localhost/self-driving-system', { 
    waitUntil: 'networkidle', 
    timeout: 20000 
  });
  
  // 等待更长时间确保 React 渲染完成
  await page.waitForTimeout(5000);
  
  // 获取页面所有文本
  const pageText = await page.evaluate(() => document.body.innerText);
  console.log('\n页面文本内容 (前500字):');
  console.log(pageText.substring(0, 500));
  
  // 检查是否包含历史趋势
  if (pageText.includes('历史趋势')) {
    console.log('\n✅ 页面包含历史趋势文字');
  } else {
    console.log('\n❌ 页面不包含历史趋势文字');
  }
  
  // 查找所有可点击元素
  const clickableElements = await page.evaluate(() => {
    const elements = document.querySelectorAll('button, [role=tab], a');
    return Array.from(elements).map(el => ({
      tag: el.tagName,
      text: el.innerText.trim().substring(0, 50),
      class: el.className
    }));
  });
  
  console.log('\n可点击元素:');
  clickableElements.forEach(el => console.log('  -', el.tag, ':', el.text));
  
  await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/sds-debug.png' });
  
  await browser.close();
})();
