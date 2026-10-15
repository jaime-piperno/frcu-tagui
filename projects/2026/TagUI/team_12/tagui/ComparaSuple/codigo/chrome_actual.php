<?php
// Una sola conexión aprobada por el usuario. Nunca cierra el Chrome personal.
require 'ws/Base.php';
require 'ws/Client.php';
require 'ws/Exception.php';
require 'ws/BadOpcodeException.php';
require 'ws/BadUriException.php';
require 'ws/ConnectionException.php';

class ComparaSupleIpcError extends RuntimeException {}
class ComparaSupleConfigurationError extends RuntimeException {}
class ComparaSupleReadTimeout extends RuntimeException {}
class ComparaSupleBridgeError extends RuntimeException {
    public $diagnosticCode;
    public function __construct($code) { $this->diagnosticCode = $code; parent::__construct($code); }
}

class ComparaSupleSocket extends WebSocket\Client {
    public $receivedBytes = 0;
    public $readDeadline = null;
    private $fragmentPending = false;
    public function open() { $this->connect(); }
    public function receive() {
        $this->receivedBytes = 0;
        $this->fragmentPending = false;
        return parent::receive();
    }
    protected function receive_fragment() {
        $pending = $this->huge_payload;
        $previousOpcode = $this->last_opcode;
        $result = parent::receive_fragment();
        if ($this->last_opcode === 'ping' || $this->last_opcode === 'pong') {
            // Ping/pong pueden intercalarse con los fragmentos JSON.
            if (!is_string($result)) throw new ComparaSupleBridgeError('protocol_error');
            $payload = $pending ? substr($result, strlen($pending)) : $result;
            if (strlen($payload) > 125) throw new ComparaSupleBridgeError('protocol_error');
            if ($this->last_opcode === 'ping') $this->send_fragment(true, $payload, 'pong', true);
            $this->huge_payload = $pending;
            $this->last_opcode = $previousOpcode;
            if (!$this->fragmentPending) $this->receivedBytes = 0;
            return null;
        }
        $this->fragmentPending = $result === null;
        return $result;
    }
    protected function read($length) {
        $data = '';
        while (strlen($data) < $length) {
            if ($this->readDeadline !== null) {
                $remaining = $this->readDeadline - microtime(true);
                if ($remaining <= 0) {
                    if ($this->receivedBytes === 0) throw new ComparaSupleReadTimeout();
                    throw new ComparaSupleBridgeError('frame_timeout');
                }
                $seconds = (int)floor($remaining);
                stream_set_timeout($this->socket, $seconds, max(1, (int)(($remaining - $seconds) * 1000000)));
            }
            $buffer = @fread($this->socket, $length - strlen($data));
            if ($buffer === false || $buffer === '') {
                $meta = stream_get_meta_data($this->socket);
                // Sólo podemos continuar si la trama todavía no empezó.
                if (!empty($meta['timed_out']) && empty($meta['eof'])) {
                    if ($this->receivedBytes === 0) throw new ComparaSupleReadTimeout();
                    throw new ComparaSupleBridgeError('frame_timeout');
                }
                throw new ComparaSupleBridgeError(!empty($meta['eof']) ? 'connection_lost' : 'protocol_error');
            }
            $this->receivedBytes += strlen($buffer);
            $data .= $buffer;
            $meta = stream_get_meta_data($this->socket);
            if (strlen($data) < $length && !empty($meta['timed_out']))
                throw new ComparaSupleBridgeError('frame_timeout');
        }
        return $data;
    }
    public function diagnostic() {
        $meta = is_resource($this->socket) ? stream_get_meta_data($this->socket) : array();
        return array('bytes_read' => $this->receivedBytes, 'socket_timeout' => !empty($meta['timed_out']),
                     'eof' => !empty($meta['eof']), 'close_status' => $this->getCloseStatus());
    }
    public function connectionDiagnostic($error) {
        // No guardar el mensaje original de la biblioteca.
        $message = $error->getMessage();
        $metadata = is_resource($this->socket) ? stream_get_meta_data($this->socket) : array();
        if (strpos($message, 'Could not open socket to ') === 0) {
            $diagnostic = array('code' => 'connection_lost');
            if (preg_match('/\(([0-9]+)\)\.$/D', $message, $match)) {
                $number = (int)$match[1];
                $diagnostic['socket_errno'] = $number;
                if (in_array($number, array(61, 111, 10061), true)) $diagnostic['code'] = 'connection_refused';
                if (in_array($number, array(60, 110, 10060), true)) $diagnostic['code'] = 'connect_timeout';
            }
            return $diagnostic;
        }
        if (!empty($metadata['timed_out'])) return array('code' => 'handshake_timeout');
        $diagnostic = array('code' => 'handshake_rejected');
        if (preg_match('~HTTP/[0-9.]+ ([1-5][0-9]{2})(?: |\r|\n)~', $message, $match))
            $diagnostic['http_status'] = (int)$match[1];
        if (!empty($metadata['eof']) && !isset($diagnostic['http_status']))
            $diagnostic['code'] = 'connection_lost';
        return $diagnostic;
    }
    public function disconnect() {
        if (is_resource($this->socket)) fclose($this->socket);
        $this->socket = null;
        $this->is_connected = false;
    }
}

function comparasuple_write($path, $contents) {
    // El reemplazo evita que el lector encuentre un JSON incompleto.
    $temporary = $path . '.tmp';
    if (@file_put_contents($temporary, $contents, LOCK_EX) === false)
        throw new ComparaSupleIpcError('No se pudo escribir la respuesta del puente.');
    for ($attempt = 0; $attempt < 5; $attempt++) {
        if (@rename($temporary, $path)) return;
        usleep(20000);
    }
    throw new ComparaSupleIpcError('No se pudo reemplazar la respuesta del puente.');
}

function comparasuple_status($phase, $code = 'ok', $extra = array()) {
    global $started, $activeCommand;
    $status = array('phase' => $phase, 'code' => $code,
                    'elapsed_ms' => (int)round((microtime(true) - $started) * 1000));
    if (isset($activeCommand)) {
        $status['method'] = $activeCommand['method'];
        $status['scope'] = $activeCommand['scope'];
        $status['command_ms'] = (int)round((microtime(true) - $activeCommand['started']) * 1000);
    }
    foreach (array('socket_errno', 'http_status', 'bytes_read', 'close_status') as $key) {
        if (isset($extra[$key]) && is_int($extra[$key])) $status[$key] = $extra[$key];
    }
    foreach (array('socket_timeout', 'eof') as $key) {
        if (isset($extra[$key]) && is_bool($extra[$key])) $status[$key] = $extra[$key];
    }
    try { comparasuple_write('chrome-actual-status.json', json_encode($status)); }
    catch (Exception $ignored) {} // El diagnóstico no debe cambiar la operación.
}

function comparasuple_error($id, $message, $code = -32000) {
    return array('id' => $id, 'error' => array('code' => $code, 'message' => $message));
}

function comparasuple_reply($path, $response, $count = null) {
    $encoded = json_encode($response, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($encoded === false) throw new ComparaSupleIpcError('Respuesta JSON inválida.');
    comparasuple_write($path, ($count === null ? '' : '[' . $count . '] ') . $encoded);
}

function comparasuple_command($client, $request, $scope, &$session, &$sequence, &$running, &$capture) {
    global $activeCommand;
    $id = isset($request->id) ? $request->id : null;
    if (!is_object($request) || !isset($request->method) || !is_string($request->method)
            || !(is_int($id) || is_string($id))
            || (isset($request->params) && !is_object($request->params)))
        return comparasuple_error($id, 'Comando inválido.', -32600);
    $method = $request->method;
    $activeCommand = array('method' => preg_match('/^[A-Za-z0-9_.]{1,80}$/D', $method) ? $method : 'invalid',
                           'scope' => $scope === 'page' ? 'page' : 'browser', 'started' => microtime(true));
    $params = isset($request->params) ? $request->params : new stdClass();
    if ($method === 'ComparaSuple.disconnect') {
        if ($scope !== 'browser') return comparasuple_error($id, 'Comando de control requerido.');
        $running = false;
        return array('id' => $id, 'result' => new stdClass());
    }
    if ($method === 'ComparaSuple.setSession') {
        if ($scope !== 'browser' || !isset($params->sessionId)
                || !is_string($params->sessionId) || $params->sessionId === '')
            return comparasuple_error($id, 'Falta la sesión de la pestaña propia.');
        $session = $params->sessionId;
        return array('id' => $id, 'result' => new stdClass());
    }
    if ($method === 'ComparaSuple.startCapture') {
        if ($scope !== 'browser') return comparasuple_error($id, 'Comando de control requerido.');
        comparasuple_write('tagui_chrome.in', '');
        comparasuple_write('tagui_chrome.out', '[0] START');
        $capture = array('last' => null, 'state' => 'START');
        return array('id' => $id, 'result' => new stdClass());
    }
    // No aceptar cierre global ni comandos que alcancen otras pestañas.
    if ($method === 'Browser.close' || $method === 'Browser.crash'
            || $method === 'Target.sendMessageToTarget' || strpos($method, 'ComparaSuple.') === 0)
        return comparasuple_error($id, 'Este comando no está permitido en Chrome personal.', -32601);
    if ($scope !== 'browser' && $scope !== 'page')
        return comparasuple_error($id, 'Ámbito CDP inválido.');
    if ($scope === 'page' && $session === null)
        return comparasuple_error($id, 'Todavía no se adjuntó la pestaña propia.');
    if (!$client->isConnected()) throw new RuntimeException('Chrome desconectó el puente.');
    $upstream = ++$sequence;
    $message = array('id' => $upstream, 'method' => $method, 'params' => $params);
    if ($scope === 'page') $message['sessionId'] = $session;
    $client->send(json_encode($message, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
    $deadline = microtime(true) + 30;
    $client->readDeadline = $deadline;
    do {
        $remaining = $deadline - microtime(true);
        if ($remaining <= 0) break;
        $client->setTimeout(max(1, (int)ceil($remaining)));
        try { $response = json_decode($client->receive()); }
        catch (ComparaSupleReadTimeout $error) { break; }
        if (!$client->isConnected()) throw new RuntimeException('Chrome desconectó el puente.');
        // Los eventos y respuestas ajenas no pueden reemplazar la respuesta pedida.
        if (is_object($response) && isset($response->id) && $response->id === $upstream) {
            if ($scope === 'page' && (!isset($response->sessionId) || $response->sessionId !== $session))
                throw new ComparaSupleBridgeError('session_mismatch');
            $response->id = $id;
            unset($response->sessionId);
            return $response;
        }
    } while (true);
    // Una respuesta tardía se descarta por ID; el comando no se repite.
    comparasuple_status('ready', 'cdp_timeout', $client->diagnostic());
    fwrite(STDERR, 'Chrome demoró la respuesta a ' . $activeCommand['method'] . '; conexión conservada.' . "\n");
    return comparasuple_error($id, 'Chrome no respondió al comando dentro del plazo.', -32002);
}

$started = microtime(true);
$phase = 'starting';
$client = null;
$running = true;
$session = null;
$sequence = 0;
$lastControl = null;
$capture = array('last' => null, 'state' => 'START');
$activePath = null;
$activeId = null;
$activeCount = null;
try {
    comparasuple_status($phase);
    $endpoint = isset($argv[1]) ? $argv[1] : '';
    if (!preg_match('~^ws://127\.0\.0\.1:([0-9]{1,5})/devtools/browser/[^\s?#]+$~D', $endpoint, $match)
            || (int)$match[1] < 1 || (int)$match[1] > 65535)
        throw new ComparaSupleConfigurationError('La conexión debe ser el WebSocket local de Chrome.');
    comparasuple_write('tagui_chrome.in', '');
    comparasuple_write('tagui_chrome.out', '[0] START');
    comparasuple_write('control.out', '');
    $phase = 'connecting';
    comparasuple_status($phase);
    $client = new ComparaSupleSocket($endpoint, array('timeout' => 120));
    $client->open(); // Chrome puede esperar la autorización manual antes de aceptar.
    $phase = 'ready';
    comparasuple_status($phase);
    while ($running) {
        $activePath = null;
        $activeId = null;
        $activeCount = null;
        $controlText = is_file('control.in') ? trim(file_get_contents('control.in')) : '';
        if ($controlText !== '') {
            $request = json_decode($controlText);
            if (is_object($request) && isset($request->id) && $request->id !== $lastControl) {
                $activePath = 'control.out';
                $activeId = $request->id;
                $lastControl = $request->id;
                $scope = isset($request->scope) ? $request->scope : '';
                $phase = 'cdp';
                comparasuple_reply($activePath, comparasuple_command($client, $request, $scope, $session, $sequence, $running, $capture));
                $phase = 'ready';
            }
        }
        if (!$running) break;
        $activePath = null;
        $activeId = null;
        $intent = trim(file_get_contents('tagui_chrome.in'));
        if ($intent === '') {
            if ($capture['state'] !== 'START') comparasuple_write('tagui_chrome.out', '[0] START');
            $capture['last'] = null;
            $capture['state'] = 'START';
        } elseif ($intent === 'finish') {
            if ($capture['state'] !== 'FINISH') comparasuple_write('tagui_chrome.out', '[0] FINISH');
            $capture['last'] = null;
            $capture['state'] = 'FINISH';
        } elseif (preg_match('/^\[([0-9]+)\] (.+)$/sD', $intent, $match) && $match[1] !== $capture['last']) {
            $request = json_decode($match[2]);
            if (is_object($request) && isset($request->id)) {
                $activePath = 'tagui_chrome.out';
                $activeId = $request->id;
                $activeCount = $match[1];
                $capture['last'] = $match[1];
                $capture['state'] = 'COMMAND';
                $phase = 'cdp';
                comparasuple_reply($activePath, comparasuple_command($client, $request, 'page', $session, $sequence, $running, $capture), $activeCount);
                $phase = 'ready';
            }
        }
        usleep(20000);
    }
    comparasuple_status('stopped');
} catch (Exception $error) {
    // No registrar mensajes de Chrome: podrían contener datos de la cuenta.
    $diagnostic = $client !== null ? $client->diagnostic() : array();
    $diagnostic['code'] = 'connection_lost';
    if ($error instanceof ComparaSupleIpcError) $diagnostic['code'] = 'ipc_error';
    elseif ($error instanceof ComparaSupleConfigurationError) $diagnostic['code'] = 'config_error';
    elseif ($phase === 'connecting' && $client !== null) $diagnostic = $client->connectionDiagnostic($error);
    elseif ($error instanceof ComparaSupleBridgeError) $diagnostic['code'] = $error->diagnosticCode;
    elseif ($error instanceof WebSocket\ConnectionException || $error instanceof WebSocket\BadOpcodeException)
        $diagnostic['code'] = !empty($diagnostic['socket_timeout']) ? 'socket_timeout' : 'protocol_error';
    comparasuple_status('failed', $diagnostic['code'], $diagnostic);
    if ($activePath !== null) {
        try { comparasuple_reply($activePath, comparasuple_error($activeId, 'Se perdió la conexión con Chrome.'), $activeCount); }
        catch (Exception $ignored) {}
    }
    fwrite(STDERR, 'El puente de Chrome terminó: ' . $diagnostic['code'] . ".\n");
    $failed = true;
} finally {
    if ($client !== null) $client->disconnect();
}
exit(isset($failed) ? 1 : 0);
