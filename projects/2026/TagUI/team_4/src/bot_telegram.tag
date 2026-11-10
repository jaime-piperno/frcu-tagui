// ===================================
// BOT RPA TELEGRAM - ETAPA 2
// ===================================

js carpeta_planilla = carpeta_escritorio()
excel_visible = false
js mostrar_planilla_al_registrar = true

js var fs = require('fs'); fs.write('tagui_base.txt', flow_path, 'w');
py import os, subprocess, sys
py ruta_src = open('tagui_base.txt', encoding='utf-8').read().strip()
py ruta_script = os.path.join(ruta_src, 'procesar_consulta.py')
py ruta_salida = os.path.join(ruta_src, '..', 'salida.json')

https://web.telegram.org/a/
wait 8

tagui flujos/preparar_planilla.tag

echo Sesion lista. Monitoreando barra lateral...

for ciclo from 1 to infinity
    echo --- Buscando mensajes pendientes ---

    // 1. Detección del chat con mensaje más ANTIGUO: elige el de menor hora (FIFO por tiempo real)
    dom var elementos = document.querySelectorAll('.chatlist-chat, a.ListItem, .ListItem-button'); function vh(txt) { txt = (txt || '').trim().toLowerCase(); var m = txt.match(/^(\d{1,2}):(\d{2})\s*(am|pm)?$/); if (m) { var h = parseInt(m[1], 10); if (m[3] === 'pm' && h < 12) h += 12; if (m[3] === 'am' && h === 12) h = 0; return { d: 2, m: h * 60 + parseInt(m[2], 10) }; } if (/^(yesterday|ayer|ontem)$/.test(txt)) return { d: 1, m: 0 }; if (/^(lun|mar|mi[eé]|jue|vie|s[aá]b|dom|mon|tue|wed|thu|fri|sat|sun)/.test(txt)) return { d: 0, m: 0 }; if (/^\d{1,2}[\/\-.]\d{1,2}/.test(txt)) return { d: 1, m: 0 }; return null; } var cands = []; for (var i = 0; i < elementos.length; i++) { var lineas = elementos[i].innerText.split('\n'); var ult = lineas[lineas.length - 1].trim(); if (!/^\d+$/.test(ult) || parseInt(ult, 10) <= 0) continue; var textos = []; var et = elementos[i].querySelector('.time, .date, .chat-time, .message-time'); if (et && et.textContent) textos.push(et.textContent); for (var j = 0; j < lineas.length - 1; j++) textos.push(lineas[j]); var t = null; for (var k = 0; k < textos.length; k++) { t = vh(textos[k]); if (t) break; } cands.push({ i: i, el: elementos[i], t: t }); } if (cands.length === 0) return "SIN_MENSAJES"; var conHora = cands.filter(function (c) { return c.t !== null; }); var elegido; if (conHora.length > 0) { conHora.sort(function (a, b) { if (a.t.d !== b.t.d) return a.t.d - b.t.d; if (a.t.m !== b.t.m) return a.t.m - b.t.m; return b.i - a.i; }); elegido = conHora[0]; } else { cands.sort(function (a, b) { return b.i - a.i; }); elegido = cands[0]; } elegido.el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true })); elegido.el.dispatchEvent(new MouseEvent('mouseup', { bubbles: true })); elegido.el.click(); return "CHAT_ABIERTO";
    estado_chat = dom_result

    if estado_chat == "CHAT_ABIERTO"
        echo Chat detectado. Ingresando a la conversacion...
        wait 3

        dom var titulo = document.querySelector('.MiddleHeader .ChatInfo .fullName, .MiddleHeader .ChatInfo .title, .chat-info .peer-title'); return JSON.stringify({ hash: window.location.hash, titulo: titulo ? titulo.textContent.trim() : '' });
        js datos_chat = JSON.parse(dom_result || '{}'); chat_id = identificador_de_chat(datos_chat.hash, datos_chat.titulo);

        // 2. Extraer el texto entrante omitiendo horas y mensajes propios
        dom var nodos = document.querySelectorAll('.message-content, .text-content'); var txt = ''; for (var i = nodos.length - 1; i >= 0; i--) { if (!nodos[i].closest('.own, .is-out')) { var clone = nodos[i].cloneNode(true); var tiempos = clone.querySelectorAll('.time, .message-time, .date'); for (var j = 0; j < tiempos.length; j++) { tiempos[j].remove(); } txt = clone.innerText.replace(/(\r\n|\n|\r)/gm, ' ').trim(); break; } } return txt;
        mensaje_cliente = dom_result

        echo Mensaje recibido en el chat `chat_id`: `mensaje_cliente`

        if mensaje_cliente != ""
            js entrada = { evento: 'mensaje', chat_id: chat_id, mensaje: mensaje_cliente, inscriptos: null };
            tagui flujos/consultar_python.tag

            if accion == "leer_planilla"
                tagui flujos/leer_planilla.tag
                js entrada.inscriptos = inscriptos
                tagui flujos/consultar_python.tag

            if accion == "registrar"
                tagui flujos/registrar_en_planilla.tag
                js entrada = { evento: registro_guardado ? 'registro_ok' : 'registro_fallido', chat_id: chat_id, mensaje: '', numero: numero_preinscripcion, inscriptos: null };
                tagui flujos/consultar_python.tag

            if respuesta_b64 != ""
                js var expr = "(function(){var b=atob(" + JSON.stringify(respuesta_b64) + ");var u=new Uint8Array(b.length);for(var i=0;i<b.length;i++)u[i]=b.charCodeAt(i);var t=new TextDecoder('utf-8').decode(u);var el=document.querySelector('.ProseMirror, .input-message-input[contenteditable=\"true\"], div[contenteditable=\"true\"], textarea');if(!el)return 'NO_INPUT';el.focus();var ok=false;if(document.execCommand){ok=document.execCommand('insertText',false,t);}if(!ok||el.innerText.trim()===''){el.innerText=t;el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:t}));}return 'INSERT:'+ok+':'+t.length;})()";
                js estado_insert = chrome_step('Runtime.evaluate',{expression: expr});
                echo Estado de la insercion: `estado_insert`

                // 3. Enviar con Enter confiable via CDP (evento real del navegador).
                js chrome_step('Input.dispatchKeyEvent', {type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13, text: '\r', unmodifiedText: '\r'});
                js chrome_step('Input.dispatchKeyEvent', {type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13});
                wait 2

                if estado_insert contains "INSERT:true"
                    echo Mensaje despachado al usuario correctamente.
                else
                    echo ALERTA: No se pudo insertar la respuesta en la caja de texto.
            else
                echo Sin respuesta para enviar (mensaje propio del bot o sin texto).
        else
            echo Chat sin contenido valido para responder.

        // 4. Salir del chat: Clic en el fondo neutro para liberar foco y deseleccionar
        dom var fondo = document.querySelector('.messages-container, .bubbles, .chat-background') || document.body; fondo.dispatchEvent(new MouseEvent('click', { bubbles: true })); document.activeElement.blur();
        wait 1
        // Escape via CDP (reemplaza 'keyboard [esc]', que usa SikuliX y se cuelga con Java 32 bits)
        js chrome_step('Input.dispatchKeyEvent', {type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27, nativeVirtualKeyCode: 27});
        js chrome_step('Input.dispatchKeyEvent', {type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27, nativeVirtualKeyCode: 27});

        // Respaldo de navegación hacia atrás en caso de vista fija
        dom if (window.location.hash || document.querySelector('.middle-column-open')) { window.history.back(); }
        wait 2
    else
        echo En espera: Sin mensajes pendientes en la barra lateral.

    wait 4
