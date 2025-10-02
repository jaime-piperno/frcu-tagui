//Este .tag unicamente se ejecuta cuando la pagina del vuelo tiene un div extra mostrando el ahorro en dolares

// Create a timestamp for the screenshot filename
tablaPrecioMeses='//*[@id="priceBarChart"]'
//xpath para agrandar el vuelo y del detalle del vuelo
expandirvuelo='//*[@id="flights"]/div[9]/ul[2]/li/div[2]/div/div[1]/div[2]/div/div/div[4]/a'
detallevuelo='//*[@id="flights"]/div[9]/ul[2]'
//xpath de los 3 vuelos mas baratos
//xpath del vuelo mas barato
vuelo1= '//*[@id="VuelosBaratos"]/div[2]/div[2]/div[5]/div/div[2]/div[2]/div/table/tbody/tr[1]/td[6]/div/a/@href'
//xpath del segundo vuelo mas barato
vuelo2='//*[@id="VuelosBaratos"]/div[2]/div[2]/div[5]/div/div[2]/div[2]/div/table/tbody/tr[2]/td[6]/div/a/@href'
//xpath del tercer vuelo mas barato
vuelo3='//*[@id="VuelosBaratos"]/div[2]/div[2]/div[5]/div/div[2]/div[2]/div/table/tbody/tr[3]/td[6]/div/a/@href'

//Toma captura de la tabla de precios segun los meses y de los 3 vuelos mas baratos
snap `tablaPrecioMeses` to out/`output folder`/TablaPrecios.png
wait 2

read `vuelo1` to linkvuelo1
//Tomar como referencia el link de la pagina anterior
dom return window.location.href
https://www.turismocity.com.ar`linkvuelo1`
wait 3
click `expandirvuelo`
snap `detallevuelo` to out/`output folder`/Vuelo1.png
//Volver a la pagina anterior
https://`dom_result.split('https://')[1]`
wait 3

read `vuelo2` to linkvuelo2
dom return window.location.href
https://www.turismocity.com.ar`linkvuelo2`
wait 3
click `expandirvuelo`
snap `detallevuelo` to out/`output folder`/Vuelo2.png
https://`dom_result.split('https://')[1]`
wait 3

read `vuelo3` to linkvuelo3
https://www.turismocity.com.ar`linkvuelo3`
wait 3
click `expandirvuelo`
snap `detallevuelo` to out/`output folder`/Vuelo3.png
