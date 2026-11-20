const puppeteer = require('puppeteer-core');
const { getChromePath } = require('../rpa_runner.js');
const path = require('path');

async function capture() {
    const browser = await puppeteer.launch({
        executablePath: getChromePath(),
        headless: true,
        args: ['--no-sandbox', '--window-size=1280,1024']
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 1024 });
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle0' });

    const screenshotPath = path.join('C:\\Users\\Santi\\.gemini\\antigravity-ide\\brain\\c711ad64-5987-4da0-b4a1-f2753f839e4b', 'ui_after_cleanup.png');
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log('Captura guardada en:', screenshotPath);

    await browser.close();
}

capture().catch(err => {
    console.error('Error al capturar:', err);
    process.exit(1);
});
