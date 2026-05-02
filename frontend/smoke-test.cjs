const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    const results = [];
    const errors = [];
    
    page.on('console', msg => {
        if (msg.type() === 'error') errors.push(msg.text());
    });
    page.on('pageerror', err => errors.push(err.message));
    
    // 测试所有页面
    const pages = [
        { url: '/', name: '首页' },
        { url: '/tasks', name: '任务' },
        { url: '/projects', name: '项目' },
        { url: '/strategic-map', name: '战略全景' },
        { url: '/meeting-notes', name: '会议纪要' },
        { url: '/self-driving-system', name: '自我驱动系统' }
    ];
    
    for (const p of pages) {
        try {
            await page.goto('http://localhost' + p.url, { 
                waitUntil: 'domcontentloaded', 
                timeout: 15000 
            });
            await page.waitForTimeout(1000);
            
            const title = await page.title().catch(() => '无标题');
            results.push({ page: p.name, status: 'OK', title });
            
            // 截图
            await page.screenshot({ 
                path: `/opt/kanban-react/qa-reports/screenshots/${p.name.replace(/\//g, '-')}.png`,
                fullPage: true 
            });
        } catch (e) {
            results.push({ page: p.name, status: 'FAIL', error: e.message });
        }
    }
    
    console.log(JSON.stringify({ results, errors }, null, 2));
    await browser.close();
})();
