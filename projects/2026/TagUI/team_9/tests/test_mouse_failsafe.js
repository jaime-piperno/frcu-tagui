const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const MOUSE_HELPER = path.join(ROOT, 'mouse_helper.exe');
const FLAG_FILE = path.join(ROOT, 'failsafe.flag');
const STATE_FILE = path.join(ROOT, 'failsafe.state');

console.log('[TEST] Iniciando prueba de regla estricta de failsafe de mouse...');

// Limpiar estados previos
if (fs.existsSync(FLAG_FILE)) fs.unlinkSync(FLAG_FILE);
if (fs.existsSync(STATE_FILE)) fs.unlinkSync(STATE_FILE);

// 1. Obtener posición actual
const posOutput = spawnSync(MOUSE_HELPER, ['pos'], { encoding: 'utf8' }).stdout.trim();
const [initX, initY] = posOutput.split(',').map(Number);
console.log(`[TEST] Posición inicial del cursor: (${initX}, ${initY})`);

// 2. Iniciar watchdog
const watchdog = spawn(MOUSE_HELPER, ['watchdog'], {
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe']
});

let watchdogOutput = '';
watchdog.stdout.on('data', (d) => {
    watchdogOutput += d.toString();
});

let exitCode = null;
watchdog.on('exit', (code) => {
    exitCode = code;
});

// Esperar a que el watchdog inicialice
setTimeout(() => {
    if (!fs.existsSync(STATE_FILE)) {
        console.error('[TEST FAIL] failsafe.state no fue creado por el watchdog.');
        watchdog.kill();
        process.exit(1);
    }

    const stateContent = fs.readFileSync(STATE_FILE, 'utf8').trim();
    console.log(`[TEST] Estado inicial en failsafe.state: "${stateContent}"`);

    // 3. Simular intervención física brusca del usuario (> 260px de desvío sostenido)
    console.log('[TEST] Simulando intervención física brusca del usuario (movimiento manual > 260px)...');
    
    // Simular que la posición física del cursor se aparta más de 300px
    fs.writeFileSync(STATE_FILE, `0,${initX - 350},${initY - 350}`);

    setTimeout(() => {
        const flagExists = fs.existsSync(FLAG_FILE);
        console.log(`[TEST] failsafe.flag existe: ${flagExists}`);
        console.log(`[TEST] Salida del watchdog: "${watchdogOutput.trim()}"`);
        console.log(`[TEST] Código de salida del watchdog: ${exitCode}`);

        // Limpiar
        try { watchdog.kill(); } catch(e) {}
        if (fs.existsSync(FLAG_FILE)) fs.unlinkSync(FLAG_FILE);
        if (fs.existsSync(STATE_FILE)) fs.unlinkSync(STATE_FILE);

        if (flagExists || watchdogOutput.includes('USER_MOUSE_INTERVENTION') || exitCode === 99) {
            console.log('[TEST OK] ✅ Failsafe verificado con éxito: El watchdog detectó el movimiento brusco y disparó la cancelación.');
            process.exit(0);
        } else {
            console.error('[TEST FAIL] ❌ El watchdog no detectó la intervención.');
            process.exit(1);
        }
    }, 350);
}, 150);
