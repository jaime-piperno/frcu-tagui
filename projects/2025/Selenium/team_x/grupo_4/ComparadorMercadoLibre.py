import time
from selenium import webdriver
from selenium.webdriver.common.by import By

def mainMercadoLibre(parametro):
    """Función principal que coordina todo el proceso de scraping de MercadoLibre"""
    driver = inicializarDriver()
    buscarProductos(driver, parametro)
    productos = extraerProductos(driver)
    #mostrarProductos(productos)
    driver.quit()
    return productos

def inicializarDriver():
    """
    Inicializa el driver de Chrome y navega a MercadoLibre Argentina.
    
    """
    driver = webdriver.Chrome()
    driver.get("https://www.mercadolibre.com.ar/")
    time.sleep(3)
    return driver

def buscarProductos(driver, producto):
    """Busca en la barra de mercado libre un producto específico
    
    Args:
        driver: Instancia del WebDriver de Selenium.
        producto (str): Término de búsqueda del producto.
    """
    buscador = driver.find_element(By.NAME, "as_word")
    buscador.send_keys(producto)
    buscador.submit()

def extraerProductos(driver):
    """Extrae información de los primeros 10 productos encontrados
    
    Args:
        driver: Instancia del WebDriver de Selenium
        
    Returns:
        list: Lista de diccionarios con información de productos
    """
    time.sleep(3)
    # Extraer las cards de los primeros 10 artículos
    cards = driver.find_elements(By.CLASS_NAME, "ui-search-layout__item")
    productos = []
    convertirCardsADiccionario(cards, productos)
    return productos

def getLink(card):
    link = card.find_element(By.CLASS_NAME, "poly-component__title").get_attribute("href")
    return link

def convertirCardsADiccionario(cards, productos):
    """
    Convierte los elementos HTML de productos en diccionarios estructurados.
    Args:
        cards

    Returns:
    """
    for i, card in enumerate(cards[:5], start=1):    
        try:
            titulo = card.find_element(By.CLASS_NAME, "poly-component__title").text
            precio = card.find_element(By.CLASS_NAME, "andes-money-amount__fraction").text
            precio = precio.replace('.', '')  # quitar el punto en el precio
            link = getLink(card)
            producto = {
                "titulo": titulo,
                "precio": precio,
                "link": link,
            }            
            productos.append(producto)
            
        except Exception as e:
            print(f"Error al procesar producto {i}: {e}")

def mostrarProductos(productos):
    """
    Muestra el diccionario completo de productos extraídos.
    Args:
        productos (list): Lista de diccionarios con información de productos.
    Returns:
        None
    """
    print("\n--- Diccionario de productos ---")
    for i, producto in enumerate(productos, start=1):
        print(f"Producto {i}: {producto['precio'] } - {producto['titulo'] } - {producto['link'] }")
