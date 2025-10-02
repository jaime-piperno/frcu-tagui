import ComparadorAmazon as Amazon
import ComparadorMercadoLibre as MercadoLibre
import sys

def compararPrecios(productosAmazon, productosMercadoLibre): 
    """
    Compara los productos de Amazon y MercadoLibre y devuelve los 5 más baratos
    Args:
        productosAmazon (list): Lista de diccionarios con información de productos de Amazon
        productosMercadoLibre (list): Lista de diccionarios con información de productos de MercadoLibre   
    """
    print("\n--- Comparación de productos ---")
    productosGeneral = productosAmazon + productosMercadoLibre
    productosGeneral = sorted(productosGeneral, key=lambda x: int(x['precio']))
    mejoresProductos = productosGeneral[:5]  
    return mejoresProductos


def guardarEnArchivo(lista, archivo):
    """
    Guarda la lista de productos en un archivo de texto.
    Args:
        lista (list): Lista de diccionarios con información de productos.
        archivo (str): Nombre del archivo donde se guardará la lista.
    """
    with open(archivo, "w") as file:
        file.write(f"--- Estos son... los 5 productos más baratos... de Amazon/Mercado Libre ---\n\n")
        for producto in lista:
            file.write(f"Producto: {producto['titulo']}\nPrecio: ${producto['precio']}\nLink: {producto['link']}\n\n")

def main(parametro):
    """
        Llamada a las funciones de scraping y comparación de precios.
    """
    productosAmazon = Amazon.mainAmazon(parametro)
    productosMercadoLibre = MercadoLibre.mainMercadoLibre(parametro)
    lista = compararPrecios(productosAmazon, productosMercadoLibre)
    archivo = "lista_productos.txt"
    guardarEnArchivo(lista, archivo)
    print("se ha creado el archivo 'lista_productos.txt' en el directorio actual.")

if __name__ == "__main__":
    # Verificar si se pasó un parámetro
    if len(sys.argv) > 1:
        producto_buscar = sys.argv[1]
        print(f"Buscando productos relacionados con: {producto_buscar}")
        main(producto_buscar)
    else:
        print("Error: Debes proporcionar un producto a buscar.")
        print("Uso: py buscadorPrincipal.py <producto> o python buscadorPrincipal.py <producto>")
        print("Ejemplo: python buscadorPrincipal.py mouse")    

        


