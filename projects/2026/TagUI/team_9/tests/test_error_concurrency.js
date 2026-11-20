const http = require('http');

function postJson(urlPath, data) {
    return new Promise((resolve, reject) => {
        const payload = JSON.stringify(data);
        const req = http.request({
            hostname: 'localhost',
            port: 3000,
            path: urlPath,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(payload)
            }
        }, (res) => {
            let body = '';
            res.on('data', chunk => body += chunk);
            res.on('end', () => {
                resolve({ statusCode: res.statusCode, body: JSON.parse(body || '{}') });
            });
        });
        req.on('error', reject);
        req.write(payload);
        req.end();
    });
}

async function testConcurrency() {
    console.log('--- TEST CONCURRENCIA: Lanzar dos RPAs simultáneos ---');
    
    // Iniciar primer RPA en background con producto oficial del catálogo (no esperar a que termine)
    postJson('/api/buscar-individual', { id: 'arroz_gallo_largo_fino_1kg', producto: 'Arroz Gallo Largo Fino 1 kg', cantidad: 1, unidad: 'kg' })
        .then(r => console.log('[RPA 1 terminado]:', r.statusCode))
        .catch(e => console.log('[RPA 1 error]:', e.message));

    // Esperar 400ms para que el primer RPA adquiera el lock isRpaRunning = true
    await new Promise(r => setTimeout(r, 400));

    // Intentar lanzar el segundo RPA mientras el primero sigue ejecutándose
    console.log('[RPA 2] Intentando lanzar segundo RPA concurrente...');
    const res2 = await postJson('/api/buscar-individual', { id: 'leche_la_serenisima_clasica_1l', producto: 'Leche La Serenísima Clásica 1 L', cantidad: 1, unidad: 'L' });
    console.log('[RPA 2 Respuesta]: Status =', res2.statusCode, '| Mensaje =', res2.body.message);

    if (res2.statusCode === 409 && res2.body.message.includes('ya está')) {
        console.log('>>> TEST CONCURRENCIA EXITOSO: El segundo RPA fue rechazado correctamente con HTTP 409.');
    } else {
        console.error('>>> TEST CONCURRENCIA FALLIDO: No se bloqueó la concurrencia.');
    }

    // Abortar RPA 1 para liberar recursos
    await postJson('/api/abort', {}).catch(() => {});
}

testConcurrency().catch(err => {
    console.error('Error:', err);
    process.exit(1);
});
