# 📌 UTN FRCU – Tecnologías para la Automatización 2025

## 👥 Team
- **Team number:** 6
- **Members:**
  - Bernardoni Rosin, Pablo.
  - Fernández, Máximo.
  - Gadea, Estanislao José.
  - Gómez, Mateo Edgardo.
  - Piccart, Nicolás Ezequiel.

---

## 🤖 Bot Description
- **Description:**
Automation tool for creating and updating products for the nursery Guaritay.
- **Technology used:**
TagUI

---

## 🛠️ Usage Instructions
1. Install TagUI following the steps of its [documentation](https://tagui.readthedocs.io/en/latest/setup.html).

2. Create a tagui_local.csv file, as shown in [this example](./tagui_local.csv).
Then create a productos.csv file, indicating the data of the products,
as shown in [the example](./productos.csv).

> ⚠️ **__WARNING:__** none of these files should be uploaded to a repository,
both contain sensible data that must not be exposed.
The ones shown in this repo just serve as examples.

3. Run TagUI with `tagui cargar_productos.tag productos.csv`

4. The products will be added and updated in real time!


---

## 📝 Additional Notes
- The program was made initially with the intention of reading a real .pdf file
with python, and then transformed to a .csv so tagUI can read automate it from
the pdf. This idea was discarded because the example PDF was not well formatted,
which made it impossible to parse properly. One improvement we can make of this
is using a different tool for analazing the PDF as an image for extracting its
text.
- TagUI had some issues when focusing elements that were not visible on screen.
For example, it sometimes tried to click an element that were not visible, and
when it moved the view, it clicked on a different place.
- The bot, as implemented right now, assumes every single piece of data comes
from the same supplier, as indicated in tagui_local.csv
- As its implementation of today, TagUI's "type" does not dispatch a "keyup" 
event, so this had to be coded to imitate this behaviour for searches.
