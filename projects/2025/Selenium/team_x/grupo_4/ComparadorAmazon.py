from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import RecopiladorPrecioDolar as PrecioDolar

def mainAmazon(parametro):
    """
    Función principal que coordina todo el proceso de scraping de Amazon.
    Args:
        parametro (str): Término de búsqueda del producto.
    Returns:
        list: Lista de diccionarios con información de productos.
    """
    driver = inicializarDriver(parametro)
    buscarProductos(driver, parametro)
    productos = extraerProductos(driver)    
    preciosEnDolares(productos)
    #mostrarProductos(productos)
    driver.quit()
    return productos

def inicializarDriver(parametro):
    """
    Inicializa el driver de Chrome y navega a Amazon
    Args:
        parametro (str): Término de búsqueda del producto.
    Returns:
        driver: Instancia del WebDriver de Selenium.
    """
    driver = webdriver.Chrome()    
    driver.get("https://www.amazon.com") #f"https://www.amazon.com/s?k={parametro}")
    time.sleep(3)
    return driver

def buscarProductos(driver, producto):
    """
    Busca en la barra de Amazon un producto específico
    
    Args:
        driver: Instancia del WebDriver de Selenium
        producto (str): Término de búsqueda del producto
    Returns:
        None
    """
    buscador = driver.find_element(By.ID, "twotabsearchtextbox")
    buscador.send_keys(producto)
    buscador.send_keys(Keys.RETURN)
    time.sleep(3)


def extraerProductos(driver):
    """Extrae información de los primeros 10 productos encontrados
    
    Args:
        driver: Instancia del WebDriver de Selenium
        
    Returns:
        list: Lista de diccionarios con información de productos
    """
    time.sleep(3)
    # Extraer las cards de los resultados de búsqueda 
    productos = []
    cards = driver.find_elements( By.CLASS_NAME, "s-card-container" )
    convertirCardsADiccionario(cards, productos)
    return productos

def getPrecios(card):
    # Extraer la parte entera y decimal del precio
    whole_part = card.find_element(By.CLASS_NAME, 'a-price-whole').text
    fractional_part = card.find_element(By.CLASS_NAME, 'a-price-fraction').text
    precio = whole_part + '.' + fractional_part
    return precio

def getLink(card):
    link = card.find_element(By.CSS_SELECTOR, "a.a-link-normal").get_attribute("href")
    return link

def convertirCardsADiccionario(cards, productos):
    """Convierte los elementos HTML de productos en diccionarios estructurados.
    
    Args:
        cards: Lista de elementos WebElement de Selenium.
        productos (list): Lista donde se almacenarán los diccionarios de productos.
    Returns:
        None
    """

    for i, card in enumerate(cards[:5], start=1):    
        try:
            titulo = card.find_element(By.CSS_SELECTOR, ".a-text-normal").text 
            #print(titulo)
            precioUSD = getPrecios(card)
            #precioARS = PrecioDolar.recuperarPrecio(precioUSD)
            link = getLink(card)
            producto = {
                "titulo": titulo,
                "precio": precioUSD,  
                "link": link,
            }            
            productos.append(producto)        
        except Exception as e:
            print(f"Error al procesar la card {i}")


def preciosEnDolares(productos):
    """
    Convierte los precios de los productos de USD a ARS usando la función de RecopiladorPrecioDolar
    
    Args:
        productos (list): Lista de diccionarios con información de productos en USD.
    
    Returns:
        list: Lista de diccionarios con información de productos en ARS.
    """
    listaPreciosUSD = []
    for producto in productos:
        listaPreciosUSD.append(producto['precio'])
    
    listaPreciosARS = PrecioDolar.recuperarPrecio(listaPreciosUSD)

    for i, producto in enumerate(productos):
        producto['precio'] = listaPreciosARS[i]

    return productos

  
def mostrarProductos(productos):
    """
    Muestra el diccionario completo de productos extraídos
    
    Args:
        productos (list): Lista de diccionarios con información de productos
    """
    print("\n--- Diccionario de productos ---")
    for i, producto in enumerate(productos, start=1):
        print(f"Producto {i}: {producto['precio'] } - {producto['titulo'] } - {producto['link'] }")
    

#esta no es la linea 140
