const puppeteer = require('puppeteer-core');
const { getChromePath } = require('../rpa_runner.js');
const fs = require('fs');
const path = require('path');

const ARTIFACT_DIR = 'C:\\Users\\alex1\\.gemini\\antigravity-ide\\brain\\c4b222c4-b9da-4105-90f7-26bba5b6ddb1';

async function testCanastaSimple() {
    console.log('--- INICIANDO TEST: LISTA LIMPIA DE CANASTA SIN DECORACIÓN NI MULTIPLICADOR ---');

    // Backup original input.csv
    const originalCsv = fs.readFileSync(path.join(__dirname, '../input.csv'), 'utf8');

    const browser = await puppeteer.launch({
        executablePath: getChromePath(),
        headless: true,
        args: ['--no-sandbox', '--window-size=1366,900']
    });

    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1366, height: 900 });

        console.log('[Test] Navegando a http://localhost:3000...');
        await page.goto('http://localhost:3000', { waitUntil: 'networkidle0' });
        await new Promise(r => setTimeout(r, 1500));

        // 1. Verificar carga inicial de la lista simple
        const infoInicial = await page.evaluate(() => {
            const badge = document.getElementById('count-prods-canasta');
            const items = document.querySelectorAll('.canasta-item-row');
            const quickSelect = document.getElementById('quick-select-canasta');
            const optgroups = quickSelect ? quickSelect.querySelectorAll('optgroup') : [];

            return {
                badgeCount: badge ? badge.textContent.trim() : null,
                itemsCount: items.length,
                optgroupsCount: optgroups.length
            };
        });

        console.log('[Test] Info inicial de la lista simple:', infoInicial);
        if (infoInicial.itemsCount === 0 || infoInicial.optgroupsCount === 0) {
            throw new Error('La lista simple o el desplegable no se poblaron correctamente en el frontend.');
        }

        // 2. Probar agregar producto simplemente seleccionándolo del desplegable (evento change)
        console.log('[Test] Seleccionando Sprite en el desplegable...');
        await page.select('#quick-select-canasta', 'gaseosa_sprite_225l');
        await new Promise(r => setTimeout(r, 1000));

        const infoDespuesAgregar = await page.evaluate(() => {
            const badge = document.getElementById('count-prods-canasta');
            const items = document.querySelectorAll('.canasta-item-row');
            const spriteItem = Array.from(items).find(it => it.textContent.includes('Sprite'));
            return {
                badgeCount: badge ? badge.textContent.trim() : null,
                itemsCount: items.length,
                hasSprite: Boolean(spriteItem),
                spriteText: spriteItem ? spriteItem.textContent.trim() : ''
            };
        });

        console.log('[Test] Info tras seleccionar Sprite:', infoDespuesAgregar);
        if (!infoDespuesAgregar.hasSprite) {
            throw new Error('El producto seleccionado (Sprite) no apareció en la lista simple.');
        }

        // 3. Tomar captura de la vista con la lista limpia
        const shotListaLimpia = path.join(ARTIFACT_DIR, 'canasta_lista_simple_limpia.png');
        await page.screenshot({ path: shotListaLimpia, fullPage: false });
        console.log('[Test] Captura de lista limpia guardada en:', shotListaLimpia);

        // 4. Verificar que input.csv no tiene columna 'unidades' y tiene 'producto,cantidad,unidad'
        const csvContent = fs.readFileSync(path.join(__dirname, '../input.csv'), 'utf8');
        console.log('[Test] Primeras 3 líneas de input.csv:\n' + csvContent.split('\n').slice(0, 3).join('\n'));
        if (csvContent.startsWith('producto,cantidad,unidad,unidades')) {
            throw new Error('input.csv todavía contiene la columna unidades.');
        }

        // 5. Abrir el modal de edición de canasta y verificar que no tiene columna de cantidad
        console.log('[Test] Abriendo modal de gestión...');
        await page.click('#btn-editar-lista');
        await new Promise(r => setTimeout(r, 1000));

        const infoModal = await page.evaluate(() => {
            const modal = document.getElementById('editar-lista-modal');
            const thList = Array.from(document.querySelectorAll('#modal-table-canasta th')).map(th => th.textContent.trim());
            const hasQtyTh = thList.some(t => t.toLowerCase().includes('cantidad'));
            const qtyInputs = document.querySelectorAll('.modal-input-unid-compra');
            const rows = document.querySelectorAll('#modal-tbody-canasta tr');
            return {
                modalActive: modal ? modal.classList.contains('active') : false,
                thList,
                hasQtyTh,
                qtyInputsCount: qtyInputs.length,
                rowsCount: rows.length
            };
        });

        console.log('[Test] Info del modal:', infoModal);
        if (infoModal.hasQtyTh || infoModal.qtyInputsCount > 0) {
            throw new Error('El modal todavía contiene columnas o inputs de cantidad.');
        }

        // Captura del modal sin columna de cantidad
        const shotModal = path.join(ARTIFACT_DIR, 'canasta_modal_sin_cantidad.png');
        await page.screenshot({ path: shotModal, fullPage: false });
        console.log('[Test] Captura del modal guardada en:', shotModal);

        await page.click('#btn-cerrar-x-modal');
        await new Promise(r => setTimeout(r, 500));

        console.log('✓ TEST DE LISTA LIMPIA Y SIN MULTIPLICADOR SUPERADO EXITOSAMENTE');
    } finally {
        await browser.close();
        fs.writeFileSync(path.join(__dirname, '../input.csv'), originalCsv, 'utf8');
        console.log('[Test] input.csv restaurado.');
    }
}

testCanastaSimple().catch(err => {
    console.error('Error durante test:', err);
    process.exit(1);
});
