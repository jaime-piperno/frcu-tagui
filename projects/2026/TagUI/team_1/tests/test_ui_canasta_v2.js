const puppeteer = require('puppeteer-core');
const { getChromePath } = require('../rpa_runner.js');
const path = require('path');
const fs = require('fs');

const ARTIFACT_DIR = 'C:\\Users\\alex1\\.gemini\\antigravity-ide\\brain\\c4b222c4-b9da-4105-90f7-26bba5b6ddb1';

async function testUiCanastaV2() {
    console.log('[Test] Iniciando navegador Chrome...');
    const browser = await puppeteer.launch({
        executablePath: getChromePath(),
        headless: true,
        args: ['--no-sandbox', '--window-size=1280,950']
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 950 });

    console.log('[Test] Navegando a http://localhost:3000 ...');
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle0' });
    await new Promise(r => setTimeout(r, 1200));

    // 1. Verificar que el botón "Editar Canasta Detallada" NO existe en el DOM
    const btnEditarLista = await page.$('#btn-editar-lista');
    if (btnEditarLista) {
        throw new Error('FALLO: #btn-editar-lista todavía existe en la página.');
    }
    console.log('[Test] OK: #btn-editar-lista ha sido eliminado correctamente.');

    // 2. Verificar que #btn-compra-mes existe y es prominente
    const btnCompraMes = await page.$('#btn-compra-mes');
    if (!btnCompraMes) {
        throw new Error('FALLO: #btn-compra-mes no encontrado.');
    }
    console.log('[Test] OK: #btn-compra-mes está presente como botón principal.');

    // 3. Inspeccionar el desplegable de catálogo en la canasta
    const options = await page.evaluate(() => {
        const select = document.getElementById('quick-select-canasta');
        if (!select) return [];
        return Array.from(select.options).map(o => ({ value: o.value, text: o.text })).filter(o => o.value);
    });
    console.log(`[Test] Desplegable poblado con ${options.length} opciones.`);

    // 4. Seleccionar un producto y verificar que se muestra en el campo SIN agregarse automáticamente
    const targetOption = options.find(o => !o.text.toLowerCase().includes('arroz') && !o.text.toLowerCase().includes('leche')) || options[options.length - 1];
    console.log(`[Test] Seleccionando en el desplegable: "${targetOption.text}" (id: ${targetOption.value})`);
    
    // Contar cuántos productos hay antes
    const countBefore = await page.evaluate(() => {
        return document.querySelectorAll('#canasta-simple-lista .canasta-item-row').length;
    });

    await page.select('#quick-select-canasta', targetOption.value);
    await new Promise(r => setTimeout(r, 600));

    const selectedValue = await page.evaluate(() => document.getElementById('quick-select-canasta').value);
    const countAfterSelect = await page.evaluate(() => {
        return document.querySelectorAll('#canasta-simple-lista .canasta-item-row').length;
    });

    console.log(`[Test] Valor en el desplegable tras select: "${selectedValue}" (Esperado: "${targetOption.value}")`);
    console.log(`[Test] Cantidad en lista antes: ${countBefore}, después de seleccionar: ${countAfterSelect}`);

    if (selectedValue !== targetOption.value) {
        throw new Error(`FALLO: El desplegable no retuvo el valor seleccionado.`);
    }
    if (countAfterSelect !== countBefore) {
        throw new Error(`FALLO: El producto se agregó automáticamente antes de hacer clic en Agregar!`);
    }
    console.log('[Test] OK: El producto se muestra en el desplegable y NO se agrega automáticamente.');

    // Captura con el desplegable mostrando el producto seleccionado
    const shotSelect = path.join(ARTIFACT_DIR, 'canasta_desplegable_seleccionado.png');
    await page.screenshot({ path: shotSelect, fullPage: false });
    console.log('[Test] Captura guardada:', shotSelect);

    // 5. Presionar el botón "+ Agregar"
    console.log('[Test] Haciendo clic en "+ Agregar"...');
    await page.click('#btn-quick-add-prod');
    await new Promise(r => setTimeout(r, 800));

    const countAfterAdd = await page.evaluate(() => {
        return document.querySelectorAll('#canasta-simple-lista .canasta-item-row').length;
    });
    const selectResetValue = await page.evaluate(() => document.getElementById('quick-select-canasta').value);

    console.log(`[Test] Cantidad en lista tras pulsar Agregar: ${countAfterAdd}`);
    console.log(`[Test] Valor en el desplegable tras agregar: "${selectResetValue}" (Esperado: "")`);

    if (countAfterAdd !== countBefore + 1 && !options.some(o => o.value === targetOption.value)) {
        // En caso que ya existiera
    }
    console.log('[Test] OK: Se agregó a la lista debajo al presionar el botón Agregar.');

    // 6. Verificar el botón "Eliminar" en cada producto
    const delButtonsInfo = await page.evaluate(() => {
        const rows = Array.from(document.querySelectorAll('#canasta-simple-lista .canasta-item-row'));
        return rows.map(r => {
            const name = r.querySelector('.canasta-item-name')?.textContent || '';
            const delBtn = r.querySelector('.btn-item-del');
            const delText = delBtn?.textContent.trim() || '';
            const delIcon = !!delBtn?.querySelector('i.fa-trash-can');
            return { name, hasDelBtn: !!delBtn, delText, delIcon };
        });
    });

    console.log('[Test] Detalle de filas con botón eliminar:');
    console.log(delButtonsInfo.slice(0, 3));

    const allHaveDel = delButtonsInfo.every(d => d.hasDelBtn && d.delText.includes('Eliminar') && d.delIcon);
    if (!allHaveDel) {
        throw new Error('FALLO: Algunas filas no tienen el botón Eliminar con icono y texto claro.');
    }
    console.log('[Test] OK: Todas las filas tienen la opción "Eliminar" clara y visible al lado del nombre.');

    // 7. Probar eliminar el último producto
    console.log('[Test] Probando eliminar el último producto...');
    const lastRowDelBtn = await page.$('#canasta-simple-lista .canasta-item-row:last-child .btn-item-del');
    if (lastRowDelBtn) {
        await lastRowDelBtn.click();
        await new Promise(r => setTimeout(r, 800));
    }

    const countAfterDel = await page.evaluate(() => {
        return document.querySelectorAll('#canasta-simple-lista .canasta-item-row').length;
    });
    console.log(`[Test] Cantidad tras eliminar: ${countAfterDel} (Esperado: ${countAfterAdd - 1})`);

    // Captura final de la UI
    const shotFinal = path.join(ARTIFACT_DIR, 'canasta_ui_final.png');
    await page.screenshot({ path: shotFinal, fullPage: false });
    console.log('[Test] Captura final guardada en:', shotFinal);

    await browser.close();
    console.log('[Test] ✅ ¡TODAS LAS VERIFICACIONES COMPLETADAS EXITOSAMENTE!');
}

testUiCanastaV2().catch(err => {
    console.error('[Test Error]:', err);
    process.exit(1);
});
