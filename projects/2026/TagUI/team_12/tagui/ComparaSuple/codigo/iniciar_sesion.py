"""Comprueba y conserva la sesión personal de MercadoLibre entre ejecuciones."""
import os
import sys
import time

from engine import BrowserDisconnected, Engine, session_profile

HOME = 'https://www.mercadolibre.com.ar/'

# La opción de cerrar sesión confirma la cuenta; el script devuelve sólo un estado.
SESSION_SCRIPT = r"""(() => {
    if (location.hostname !== 'www.mercadolibre.com.ar' || location.protocol !== 'https:') return 'desconocida';
    if (/\/no-feasible-authenticators(\/|$)/i.test(location.pathname) ||
        /alcanzaste.{0,30}l[ií]mite de intentos/i.test(document.title)) return 'acceso_limitado';
    if (/captcha|account-verification|\/login|\/registration|\/gz\//i.test(location.pathname)) return 'verificacion';
    if (document.readyState !== 'complete') return 'cargando';
    const visible = element => {
        const style = getComputedStyle(element);
        return element.getClientRects().length > 0 && style.visibility !== 'hidden' && style.display !== 'none';
    };
    if (Array.from(document.querySelectorAll('iframe[src*="recaptcha"][src*="/anchor"], iframe[src*="recaptcha"][src*="/bframe"], iframe[src*="hcaptcha"], .g-recaptcha, .h-captcha'))
        .some(element => visible(element) && !element.closest('.grecaptcha-badge, [data-size="invisible"]') &&
              element.getBoundingClientRect().width > 1 && element.getBoundingClientRect().height > 1)) return 'verificacion';
    if (Array.from(document.querySelectorAll('form[action*="/login"] input[type="password"]'))
        .some(visible)) return 'sin_sesion';
    if (Array.from(document.querySelectorAll('h1, h2, [role="dialog"]')).some(element =>
        visible(element) && /por seguridad.{0,80}(complet|verific)|verific[aá].{0,30}(identidad|cuenta)|no soy un robot/i.test(element.textContent))) return 'verificacion';
    const header = document.querySelector('header, .nav-header');
    if (!header) return 'desconocida';
    const links = Array.from(header.querySelectorAll('a[href]'));
    const localPath = link => {
        try {
            const url = new URL(link.href, location.href);
            return url.protocol === 'https:' && /(^|\.)mercadolibre\.com(\.ar)?$/.test(url.hostname) ? url.pathname : '';
        } catch (_) { return ''; }
    };
    // El menú autenticado también contiene un enlace para ingresar con otra
    // cuenta. La opción de salir confirma la sesión, aunque ese enlace exista.
    if (links.some(link => /\/logout(\/|$)/i.test(localPath(link)))) return 'iniciada';
    if (links.some(link => /\/(login|lgz)(\/|$)/i.test(localPath(link)) &&
                          !/\/logout(\/|$)/i.test(localPath(link)))) return 'sin_sesion';
    return 'desconocida';
})()"""


def wait_for_user(seconds, message=None, on_skip=None):
    """Espera limitada, sin mover el mouse mientras la persona usa Chrome."""
    if seconds <= 0 or not sys.stdin.isatty():
        return False
    print(message or 'Resolvé la verificación en Chrome y volvé aquí. Enter: continuar; S: omitir tienda.', flush=True)
    deadline = time.monotonic() + seconds
    if os.name == 'nt':
        import msvcrt
        while time.monotonic() < deadline:
            if msvcrt.kbhit():
                key = msvcrt.getwch()
                if key in ('\r', '\n'):
                    return True
                if key.lower() == 's':
                    if on_skip:
                        on_skip()
                    return False
                if key == '\x1b':
                    return False
                if key == '\x03':
                    raise KeyboardInterrupt
            time.sleep(.1)
    else:
        import select
        if select.select([sys.stdin], [], [], seconds)[0]:
            answer = sys.stdin.readline()
            if answer.strip().lower() == 's' and on_skip:
                on_skip()
            return answer in ('\n', '\r\n')
    return False


def session_state(browser, timeout=20):
    """Espera la cabecera; una página desconocida nunca se da por autenticada."""
    deadline = time.monotonic() + timeout
    while True:
        response = browser.browser_command('Runtime.evaluate',
            {'expression': SESSION_SCRIPT, 'returnByValue': True}, websocket=browser.ws)
        state = response.get('result', {}).get('value', 'desconocida')
        if state in ('iniciada', 'sin_sesion', 'verificacion', 'acceso_limitado'):
            return state
        if time.monotonic() >= deadline:
            return 'desconocida'
        time.sleep(.5)


def request_login(timeout):
    if timeout <= 0:
        return False
    try:
        answer = input('MercadoLibre: no se confirmó una sesión iniciada. ¿Ingresar ahora? [s/N]: ')
    except (EOFError, OSError):
        return False
    return answer.strip().lower() in ('s', 'si', 'sí')


def access_limited(state):
    if state != 'acceso_limitado':
        return False
    print('MercadoLibre limitó el acceso. Se omite la tienda sin volver a intentar el ingreso.', flush=True)
    return True


def complete_login(browser, timeout):
    print('Ingresá manualmente en MercadoLibre desde «Ingresá». La sesión se guarda automáticamente.', flush=True)
    deadline = time.monotonic() + timeout
    while wait_for_user(max(0, deadline - time.monotonic()),
                        'Al terminar el ingreso, volvé aquí y pulsá Enter. S: omitir MercadoLibre.'):
        state = session_state(browser, timeout=min(20, max(0, deadline - time.monotonic())))
        if state == 'iniciada':
            print('MercadoLibre | Sesión confirmada y conservada para próximas ejecuciones.', flush=True)
            browser.resume_human()
            return True
        if access_limited(state):
            return False
        print('No se pudo confirmar el ingreso. Revisá la cuenta o la verificación pendiente.', flush=True)
    return False


def ensure_session(timeout=300, headless=False, browser=None):
    """Sin sesión confirmada se omite la tienda; el resto del sistema continúa."""
    try:
        if browser is None:
            profile = session_profile()
            with Engine(profile, headless=headless, profile_template=profile) as owned:
                return ensure_session(timeout, headless=headless, browser=owned)
        browser.browser_command('Page.navigate', {'url': HOME}, websocket=browser.ws)
        state = session_state(browser)
        if state == 'iniciada':
            print('MercadoLibre | Sesión iniciada confirmada.', flush=True)
            return True
        if access_limited(state):
            return False
        if headless:
            print('MercadoLibre | Sin sesión en el perfil dedicado. Se omite la tienda en segundo plano.', flush=True)
            return False
        if not request_login(timeout):
            return False
        return complete_login(browser, timeout)
    except BrowserDisconnected:
        raise
    except Exception as error:
        # Un error de acceso no confirma que la cuenta esté autenticada.
        print(f'MercadoLibre | No se pudo comprobar la sesión: {error}', flush=True)
        return False


if __name__ == '__main__':
    print('Sesión disponible.' if ensure_session() else 'MercadoLibre omitido: sin sesión confirmada.')
