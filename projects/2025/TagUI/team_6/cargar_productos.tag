if iteration equals to 1
	https://`sitio`
	if url() contains "login"
		type nombre-usuario as `usuario`
		type contra as `contraseña`
		click //input[@type='submit']

// El wait es necesario porque sino las iteraciones no funcionan.
// No sabemos por qué no espera hasta que cargue la página para realizar
// el resto de pasos.
wait 1

https://`sitio`/producto/buscar
type //input[@type='search'] as `nombre`

// Necesario para lanzar el evento keyup sobre la búsqueda.
// Así está implementado en el sistema. El type por sí solo no funciona
dom begin
search = document.querySelector("input[type='search']")
eventoKeyup = new KeyboardEvent('keyup')
search.dispatchEvent(eventoKeyup)
dom finish

// Cambia el flujo dependiendo de si existe o no el producto
if !exist('//td/a[text() ="' + nombre + '"]')
	https://`sitio`/producto/nuevo
	type nombre as `nombre`
	type codigo as `codigo`
	select categoria as `categoria`
	select proveedor as `proveedor`
	type costo as `costo`
	type ganancia as `ganancia`
	click //button[@type='submit']
else
	click //td/a
	type costo as [clear]`costo`

	// Primero hacemos un hover y un wait en el botón, porque sino
	// selecciona el botón de abajo. Suponemos que es porque tagui lo fija
	// en una posición de pantalla, pero cuando baja con la rueda, cambia de
	// posición.
	hover //button[@type='submit']
	wait 1
	click //button[@type='submit']
