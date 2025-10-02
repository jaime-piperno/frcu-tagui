from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import pyperclip
import time

#Cambio a que recibe una lista de precios, en lugar de uno en particular
def recuperarPrecio(listaPreciosOriginal):
    """
    Función que recibe una lista de precios en dólares y devuelve una lista de precios en pesos argentinos
    Args:
        listaPreciosOriginal (list): Lista de precios en dólares.
    Returns:
        list: Lista de precios en pesos argentinos.
    """
    driver = inicializarDriver()
    listaPreciosFinal = []
    for precio in listaPreciosOriginal:
        listaPreciosFinal.append(obtenerPrecio(driver, precio))    
    driver.quit()
    return listaPreciosFinal 

def obtenerPrecio(driver, precio):
    """
    Función que recibe un precio en dólares y devuelve el precio en pesos argentinos
    Args:
        precio (float): Precio en dólares.
    Returns:
        precioFinal (string): Precio en pesos argentinos.
    """
    IngresarPrecio(driver, precio)
    precioFinal = ExtraerPrecioFinal(driver)
    return precioFinal

def IngresarPrecio(driver, precio):
    """
    Ingresa el precio en dólares en el campo correspondiente y envía el formulario
    Args:
        driver: Instancia del WebDriver de Selenium.
        precio (float): Precio en dólares.
    Returns:
        None
    """
    buscador = driver.find_element(By.CSS_SELECTOR, "input[data-slot='input']")
    buscador.send_keys(Keys.CONTROL + "a")  # Seleccionar todo
    buscador.send_keys(Keys.DELETE)  
    time.sleep(1)  # Esperar un momento para asegurarse de que el campo esté listo
    buscador.send_keys(precio)
    buscador.send_keys(Keys.ENTER)

def inicializarDriver():
    """
    Inicializa el driver de Chrome y navega a la calculadora de Amazon Argentina
    Returns:
        driver: Instancia del WebDriver de Selenium.
    """
    driver = webdriver.Chrome()
    driver.get("https://www.impuestito.org/calculadora-amazon-argentina")
    time.sleep(3)
    return driver

def ExtraerPrecioFinal(driver):
    """
    Extrae el precio final en pesos argentinos de la página
    Args:
        driver: Instancia del WebDriver de Selenium.
    Returns:
        precioFinal (string): Precio en pesos argentinos.
    """
    # Extraer precio en pesos argentinos
    time.sleep(3)
    #clickear en el elemento del path indicado
    precioFinal = driver.find_element(By.XPATH, "//div[contains(@class,'transition-transform')]/span")
    precioFinal.click()
    precioFinal = pyperclip.paste()
    return precioFinal
