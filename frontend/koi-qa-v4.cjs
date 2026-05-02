const { chromium } = require('playwright');

(async () => {
  console.log('🚀 KOI QA v4 - 使用 domcontentloaded');
  
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  try {
    await page.goto('http://localhost/self-driving-system', { 
      waitUntil: 'domcontentloaded', 
      timeout: 15000 
    });
    
    await page.waitForTimeout(3000);
    
    // 获取页面文本
    const pageText = await page.evaluate(() => document.body.innerText);
    
    console.log('页面是否包含历史趋势:', pageText.includes('历史趋势'));
    console.log('页面是否包含自我驱动:', pageText.includes('自我驱动'));
    
    // 查找按钮
    const buttons = await page.locator('button').all();
    console.log('找到', buttons.length, '个按钮');
    
    for (let i = 0; i < Math.min(buttons.length, 10); i++) {
      const text = await buttons[i].textContent().catch(() => '');
      console.log('  按钮', i, ':', text.trim());
    }
    
    await page.screenshot({ path: '/opt/kanban-react/qa-reports/screenshots/sds-v4.png' });
    
  } catch (e) {
    console.error('错误:', e.message);
  }
  
  await browser.close();
})();
