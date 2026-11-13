js entrada_json = JSON.stringify(entrada)
dump `entrada_json` to ../entrada.json
py os.path.exists(ruta_salida) and os.remove(ruta_salida)
py subprocess.run([sys.executable, ruta_script], check=False)
py print(open(ruta_salida, encoding='utf-8').read() if os.path.exists(ruta_salida) else '{}')
js salida = JSON.parse(py_result || '{}'); accion = salida.accion || ''; respuesta_b64 = salida.respuesta_b64 || ''; registro = salida.registro || null;
if salida.tipo == undefined
    echo ALERTA: Python no genero una respuesta (revisar bot.log y la ventana "Python Engine")
