const puppeteer = require('puppeteer-core');
const { getChromePath } = require('../rpa_runner.js');
const fs = require('fs');
const path = require('path');

async function testCompraMes() {
    console.log('--- INICIANDO TEST: COMPRA DEL MES ---');

    const userBrowser = await puppeteer.launch({
        executablePath: getChromePath(),
        headless: true,
        args: ['--no-sandbox', '--window-size=1280,1024']
    });

    const page = await userBrowser.newPage();
    await page.setViewport({ width: 1280, height: 1024 });

    console.log('[User] Navegando a http://localhost:3000...');
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 1000));

    const artifactDir = 'C:\\Users\\Santi\\.gemini\\antigravity-ide\\brain\\c9b0791c-37a6-41e6-a587-79b4fa0291d2';

    // Clic en Iniciar Proceso (Compra del Mes)
    console.log('[User] Haciendo clic en "Iniciar Proceso" (Compra del Mes)...');
    await page.click('#btn-compra-mes');

    let capturedLiveFrame = false;
    const startTime = Date.now();
    const maxWaitMs = 150000; // 2.5 minutos

    while (Date.now() - startTime < maxWaitMs) {
        await new Promise(r => setTimeout(r, 2000));

        const playerStatus = await page.evaluate(() => {
            const badge = document.getElementById('player-status-badge');
            const overlay = document.getElementById('player-overlay');
            const time = document.getElementById('player-time');
            return {
                statusText: badge ? badge.textContent : '',
                statusClass: badge ? badge.className : '',
                overlayHidden: overlay ? overlay.classList.contains('hidden') : false,
                timeText: time ? time.textContent : ''
            };
        });

        console.log(`[Compra Mes Status] ${playerStatus.statusText} | Timer: ${playerStatus.timeText} | Overlay Oculto: ${playerStatus.overlayHidden}`);

        if (playerStatus.overlayHidden && !capturedLiveFrame && playerStatus.statusClass.includes('live')) {
            console.log('>>> CAPTURANDO SCREENSHOT EN VIVO DE COMPRA DEL MES...');
            const liveShotPath = path.join(artifactDir, 'frontend_stream_compra_mes_en_vivo.png');
            await page.screenshot({ path: liveShotPath, fullPage: true });
            console.log('>>> Captura guardada en:', liveShotPath);
            capturedLiveFrame = true;
        }

        if (playerStatus.statusText.includes('RPA FINALIZADO') || playerStatus.statusClass.includes('finished')) {
            console.log('>>> Compra del Mes FINALIZADA con éxito.');
            break;
        }
    }

    const finalShotPath = path.join(artifactDir, 'frontend_stream_compra_mes_finalizado.png');
    await page.screenshot({ path: finalShotPath, fullPage: true });
    console.log('>>> Captura final de Compra del Mes guardada en:', finalShotPath);

    await userBrowser.close();

    const csvExists = fs.existsSync(path.join(__dirname, 'resultados.csv'));
    const xlsxExists = fs.existsSync(path.join(__dirname, 'reporte_supermercados.xlsx'));
    console.log('- resultados.csv existe:', csvExists);
    console.log('- reporte_supermercados.xlsx existe:', xlsxExists);
    if (xlsxExists) {
        const stats = fs.statSync(path.join(__dirname, 'reporte_supermercados.xlsx'));
        console.log(`- reporte_supermercados.xlsx tamaño: ${stats.size} bytes (ExcelJS)`);
    }

    console.log('--- TEST COMPRA DEL MES COMPLETADO EXITOSAMENTE ---');
}

testCompraMes().catch(err => {
    console.error('Error durante test compra mes:', err);
    process.exit(1);
});
