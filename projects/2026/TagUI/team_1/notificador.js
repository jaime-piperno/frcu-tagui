const TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const CHAT_ID = process.env.TELEGRAM_CHAT_ID;

async function enviar(texto) {
    if (!TOKEN || !CHAT_ID) {
        console.warn('[TELEGRAM] Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID. Alerta omitida.');
        return false;
    }
    try {
        const res = await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: CHAT_ID, text: texto }),
            signal: AbortSignal.timeout(10000)
        });
        const respuesta = await res.json().catch(() => null);
        if (!res.ok || !respuesta || !respuesta.ok) {
            console.warn('[TELEGRAM] No se pudo enviar el mensaje:', res.status, respuesta && respuesta.description ? respuesta.description : 'respuesta inválida');
            return false;
        }
        return true;
    } catch (e) {
        console.warn('[TELEGRAM] No se pudo enviar la alerta:', e.message);
        return false;
    }
}

async function enviarBienvenida() {
    const mensaje = [
        '🤖 ¡El Bot Comparador de Precios está en línea!',
        '',
        '🛒 Compara tu canasta y 🔎 busca productos en Carrefour, COTO y Día %.',
        '',
        '📊 Inicia una búsqueda desde el dashboard. Te enviaré por aquí los resultados y las alertas de precios.'
    ].join('\n');
    return enviar(mensaje);
}

module.exports = { enviar, enviarBienvenida };
