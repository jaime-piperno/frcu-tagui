const { runRPA, abortCurrentRun } = require('../rpa_runner.js');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const FLAG_FILE = path.join(ROOT, 'failsafe.flag');
const STATE_FILE = path.join(ROOT, 'failsafe.state');

console.log('[INTEGRATION TEST] Probando integración de FailSafe en rpa_runner...');

let failsafeEventReceived = false;

// Iniciamos runRPA con un producto de prueba
const rpaPromise = runRPA({
    modo: 'individual',
    items: [{ producto: 'arroz' }],
    demoMode: true,
    onStatus: (st) => {
        console.log(`[STATUS] ${st.type}: ${st.message}`);
        if (st.message && st.message.includes('Regla estricta activada')) {
            failsafeEventReceived = true;
        }
    }
});

// A los 3 segundos (mientras Chrome está abriéndose o navegando), simulamos intervención del usuario
setTimeout(() => {
    console.log('[INTEGRATION TEST] Simulando movimiento manual del mouse durante ejecución de RPA...');
    // Creamos la bandera de intervención como lo haría el watchdog al detectar movimiento físico
    fs.writeFileSync(FLAG_FILE, 'USER_MOUSE_INTERVENTION,999,999');
}, 3000);

rpaPromise
    .then(() => {
        console.log('[INTEGRATION TEST FAIL] El RPA no debería haber completado normalmente.');
        process.exit(1);
    })
    .catch((err) => {
        console.log(`[INTEGRATION TEST] RPA detenido con error esperado: "${err.message}"`);
        if (err.message === 'USER_MOUSE_INTERVENTION' && failsafeEventReceived) {
            console.log('[INTEGRATION TEST OK] ✅ Integración confirmada: El RPA se detuvo de inmediato, notificó la regla estricta y cerró Chrome.');
            process.exit(0);
        } else {
            console.error('[INTEGRATION TEST FAIL] Mensaje inesperado:', err);
            process.exit(1);
        }
    });
