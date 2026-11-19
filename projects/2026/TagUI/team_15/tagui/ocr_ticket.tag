// Extrae el texto de un ticket o factura usando OCR (SikuliX de TagUI)
// Ejecutado en modo sin navegador: tagui ocr_ticket.tag -nobrowser -quiet

vision begin
# -*- coding: utf-8 -*-
from sikuli import *
import codecs
import java.io.File
import java.lang.Throwable
import javax.imageio.ImageIO

Settings.OcrTextRead = True
Settings.OcrTextSearch = True

texto_limpio = u""
errores = []
ruta_img = "ticket_actual.png"
try:
    img_file = java.io.File(ruta_img)
    bimg = javax.imageio.ImageIO.read(img_file)
    if bimg is None:
        errores.append("ImageIO.read devolvio None para la imagen")
    else:
        texto_ocr = None
        try:
            from org.sikuli.script import Image
            img_obj = Image.create(ruta_img)
            if img_obj is not None:
                texto_ocr = img_obj.text()
        except java.lang.Throwable, e1:
            errores.append("Image.text: " + str(e1))
        except Exception, e1:
            errores.append("Image.text: " + str(e1))

        if not texto_ocr:
            try:
                from org.sikuli.script import TextRecognizer
                tr = TextRecognizer.getInstance()
                if tr is not None:
                    if hasattr(tr, "doOCR"):
                        texto_ocr = tr.doOCR(bimg)
                    elif hasattr(tr, "recognize"):
                        texto_ocr = tr.recognize(bimg)
                else:
                    errores.append("TextRecognizer.getInstance() devolvio None")
            except java.lang.Throwable, e2:
                errores.append("TextRecognizer: " + str(e2))
            except Exception, e2:
                errores.append("TextRecognizer: " + str(e2))

        if not texto_ocr:
            try:
                from org.sikuli.script import OCR
                texto_ocr = OCR.readText(bimg)
            except java.lang.Throwable, e3:
                errores.append("OCR.readText: " + str(e3))
            except Exception, e3:
                errores.append("OCR.readText: " + str(e3))

        if texto_ocr is not None:
            if isinstance(texto_ocr, str):
                texto_ocr = texto_ocr.decode("utf-8", "replace")
            texto_limpio = texto_ocr.strip()
except java.lang.Throwable, e:
    errores.append("Java Error: " + str(e))
except Exception, e:
    errores.append("Python Error: " + str(e))

f_out = codecs.open("ocr_resultado.txt", "w", encoding="utf-8")
f_out.write(texto_limpio)
f_out.close()
if not texto_limpio and errores:
    f_err = codecs.open("ocr_error.txt", "w", encoding="utf-8")
    f_err.write("; ".join(errores))
    f_err.close()
vision finish
