// ------------------ CLIMA ------------------
// Fuente primaria: weather
https://weather.com
wait 2
if (present('//span[@data-testid="TemperatureValue"]'))
    type //*[@id="headerSearch_LocationSearch_input"] as Concepcion del Uruguay
    wait 2
    click (//button[contains(@data-testid,'ctaButton')])[1]
    wait 2
    read (//span[@data-testid="TemperatureValue"]) to temperatura
    read (//div[@data-testid="wxPhrase"]) to condicion
    fuenteClima = "Weather"
else
    // Fuente secundaria: Meteored
    https://www.meteored.com.ar
    wait 2
    if (present('(//h1)[1]'))
        type //input[@id='search_pc'] as Concepcion del Uruguay
        click //input[@id='search_pc']
        wait 2s
        // Hacer click en la primera sugerencia del listado
        click //*[@id="resultados"]/ul/li[1]
        wait 2
        read //*[@id="d_hub_1"]/div[1]/div/div/div/div/span[1] to temperatura
        read //*[@id="d_hub_1"]/div[1]/span to condicion
        fuenteClima = "Meteored"
    else
        temperatura = "N/D"
        condicion = "No disponible"
        fuenteClima = "No disponible"

// ------------------ NOTICIAS ------------------
// Fuente primaria: BBC Mundo
https://www.bbc.com/mundo
wait 2
if (present('(//h3)[1]'))
    read (//h3)[1] to noticia1
    read (//h3)[2] to noticia2
    read (//h3)[3] to noticia3
    fuenteNoticias = "BBC Mundo"
else
    // Fuente secundaria: La Nación
    https://www.lanacion.com.ar
    wait 2
    if (present('(//h2)[1]'))
        read (//h2)[1] to noticia1
        read (//h2)[2] to noticia2
        read (//h2)[3] to noticia3
        fuenteNoticias = "La Nación"
    else
        noticia1 = "No disponible"
        noticia2 = "No disponible"
        noticia3 = "No disponible"
        fuenteNoticias = "No disponible"

// ------------------ DÓLAR ------------------
// Fuente primaria: dolarhoy
https://dolarhoy.com
wait 2
if (present('(//div[@class="val"])[1]'))
    read (//div[@class="val"])[1] to dolar_blue_compra
    read (//div[@class="val"])[2] to dolar_blue_venta
    fuenteDolar = "Dolar Hoy"
else
    // Fuente secundaria: ámbito
    https://www.ambito.com/contenidos/dolar-informal.html
    wait 2
    if (present('/html/body/main/div/div[1]/div[1]/div/div[2]/div[1]/div/div/div[2]/span[1]'))
        read /html/body/main/div/div[1]/div[1]/div/div[2]/div[1]/div/div/div[2]/span[1] to dolar_blue_compra
        read /html/body/main/div/div[1]/div[1]/div/div[2]/div[1]/div/div/div[3]/span[1] to dolar_blue_venta
        fuenteDolar = "Ámbito"
    else
        dolar_blue_compra = "No disponible"
        dolar_blue_venta = "No disponible"
        fuenteDolar = "No disponible"

// ------------------ ESCRIBIR ARCHIVO ------------------
write Resumen Diario  to resumen.txt
write Fuente `fuenteClima` to resumen.txt
write Clima: `temperatura` - `condicion` to resumen.txt
write ---------------------------------------------------------------------------------------  to resumen.txt
write Noticias: to resumen.txt
write Fuente `fuenteNoticias` to resumen.txt
write - `noticia1` to resumen.txt
write - `noticia2` to resumen.txt
write - `noticia3` to resumen.txt
write ---------------------------------------------------------------------------------------  to resumen.txt
write Dólar Blue: to resumen.txt
write Fuente `fuenteDolar` to resumen.txt
write Valor Compra: `dolar_blue_compra` to resumen.txt
write Valor Venta: `dolar_blue_venta` to resumen.txt

