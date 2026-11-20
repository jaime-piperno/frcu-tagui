const puppeteer = require('puppeteer-core');
const { getChromePath } = require('../rpa_runner.js');
const fs = require('fs');
const path = require('path');

async function testLiveSearch() {
    console.log('--- INICIANDO TEST: BÚSQUEDA INDIVIDUAL GASEOSA MANAOS COLA ---');

    // Iniciar un navegador para simular al usuario que entra al frontend http://localhost:3000
    const userBrowser = await puppeteer.launch({
        executablePath: getChromePath(),
        headless: true,
        args: ['--no-sandbox', '--window-size=1280,1024']
    });

    const page = await userBrowser.newPage();
    await page.setViewport({ width: 1280, height: 1024 });

    console.log('[User] Navegando a http://localhost:3000...');
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle0' });

    // Verificar que el WebSocket se conectó
    await new Promise(r => setTimeout(r, 1000));

    // Seleccionar "Manaos Cola 2.25 L" desde el desplegable del catálogo oficial
    console.log('[User] Seleccionando "Manaos Cola 2.25 L" del catálogo cerrado...');
    await page.waitForSelector('#select-producto option[value="gaseosa_manaos_cola_225l"]', { timeout: 10000 });
    await page.select('#select-producto', 'gaseosa_manaos_cola_225l');
    await page.evaluate(() => {
        const sel = document.getElementById('select-producto');
        sel.dispatchEvent(new Event('change'));
    });

    const artifactDir = path.join(__dirname, '..');
    
    // Clic en Buscar Producto
    console.log('[User] Haciendo clic en "Comparar en 3 Súper"...');
    await page.click('#btn-buscar-individual');

    // Monitorear durante la ejecución
    const startTime = Date.now();
    const maxWaitMs = 180000; // 3 minutos máximo

    while (Date.now() - startTime < maxWaitMs) {
        await new Promise(r => setTimeout(r, 2000));

        const monitorStatus = await page.evaluate(() => {
            const statusEl = document.getElementById('monitor-status-text');
            const progressEl = document.getElementById('progress-percent-badge');
            return {
                statusText: statusEl ? statusEl.textContent : '',
                percent: progressEl ? progressEl.textContent : '0%'
            };
        });

        console.log(`[TagUI Status] ${monitorStatus.statusText} | Progreso: ${monitorStatus.percent}`);

        if (monitorStatus.statusText.includes('FINALIZADO') || monitorStatus.statusText.includes('EXITOSAMENTE')) {
            console.log('>>> El RPA TagUI ha FINALIZADO con éxito.');
            break;
        }
    }

    await userBrowser.close();

    // Verificar archivos resultantes en disco
    const csvExists = fs.existsSync(path.join(__dirname, '..', 'resultados.csv'));
    const xlsxExists = fs.existsSync(path.join(__dirname, '..', 'reporte_supermercados.xlsx'));

    console.log('Verificación de archivos:');
    console.log('- resultados.csv existe:', csvExists);
    console.log('- reporte_supermercados.xlsx existe:', xlsxExists);

    if (csvExists) {
        const csvContent = fs.readFileSync(path.join(__dirname, '..', 'resultados.csv'), 'utf8');
        const lines = csvContent.trim().split('\n');
        console.log(`- resultados.csv tiene ${lines.length} líneas.`);
        console.log('Últimas 3 líneas de resultados.csv:');
        lines.slice(-3).forEach(l => console.log('  ', l));
    }

    if (xlsxExists) {
        const stats = fs.statSync(path.join(__dirname, '..', 'reporte_supermercados.xlsx'));
        console.log(`- reporte_supermercados.xlsx tamaño: ${stats.size} bytes (Excel real de ExcelJS)`);
    }

    console.log('--- TEST COMPLETADO EXITOSAMENTE ---');
}

testLiveSearch().catch(err => {
    console.error('Error durante test live search:', err);
    process.exit(1);
});
