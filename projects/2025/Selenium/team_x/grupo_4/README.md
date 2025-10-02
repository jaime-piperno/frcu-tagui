# 📌 UTN FRCU – Tecnologías para la Automatización 2025

## 👥 Grupo

- **Número de Grupo: 4**
- **Miembros:**
  - Aguirre, Genaro
  - Blanc, Alejandro
  - Cárcamo, Lucía
  - Ponce Perez, Agustín

---

## 🤖 Descripción del Bot

- **Descripción:**
  Automatizar la búsqueda del precio de un producto en Amazon y Mercado Libre, calcular promedios de los primeros resultados y compararlos en un reporte único (CSV/JSON).

- **Tecnología utilizada:**
  - Lenguaje: Python 3.10+
  - Automatización Web: Selenium 4.35

- **Selenium:**
  Es una herramienta que se utiliza para automatizar navegadores web con el propósito de realizar pruebas funcionales y de regresión en aplicaciones web. Si bien se utiliza principalmente para testing, su uso no está limitado sólo a eso.

---

## 🛠️ Usage Instructions

Step 1: Instalación

1. Instalar Python: https://www.python.org/downloads/
2. Instalar Selenium para Python: https://selenium-python.readthedocs.io/installation.html  
   2.2. Si lo anterior no funciona, solo se debe poner el siguiente comando en CMD: "python -m pip install selenium".
3. Instalar el modulo de python "Pyperclip", ingresando el siguiente comando en CMD: "pip install pyperclip"
   3.2. Si lo anterior no funciona, solo se debe poner el siguiente comando en CMD: "python -m pip install pyperclip".

Step 2: Instrucciones de Uso

1. Descargar el código del bot.
2. Escribir en consola "py ./[nombre del archivo] [producto a buscar]".
3. Ejecutar.
4. Esperar **varios** segundos.

Step 3: Salidas esperadas

1. Se devolverá una pantalla con los N productos de menor precio, con N=1..5.
2. Cada producto tendrá su respectivo link a la página.

---

## 📝 Additional Notes

- Desafíos enfrentados:
  - Reconocer los Path de los productos (principalmente de amazon).
  - A veces, Amazon se abre con otra interfaz (y no se usan los mismos selectores)
  - A veces, Amazon se abre en pesos Argentinos y otras veces en dólares.
- Limitaciones del bot:
  - Solo utiliza Mercado Libre y Amazon (Amazon debe estar en dólares).
  - Si se busca algo que no existe devuelve una sugerencia aproximada del producto.
- Mejoras para el futuro:
  - Implementar más tiendas virtuales.
