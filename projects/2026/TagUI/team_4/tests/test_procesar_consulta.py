import os
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from cursos import cargar_cursos
from procesar_consulta import CSV_PATH, procesar

AHORA = datetime(2026, 10, 27, 18, 0, 0)


class Conversacion:

    def __init__(self, inscriptos=None, cupo=None):
        self.cursos = cargar_cursos(CSV_PATH)
        if cupo is not None:
            for curso in self.cursos:
                curso["cupo"] = cupo
        self.inscriptos = list(inscriptos or [])
        self.sesion = {}
        self.ahora = AHORA
        self.lecturas_de_planilla = 0

    def enviar(self, mensaje):
        entrada = {"evento": "mensaje", "chat_id": "123", "mensaje": mensaje, "inscriptos": None}
        salida, sesion = procesar(entrada, self.sesion, self.cursos, self.ahora)
        if salida["accion"] == "leer_planilla":
            self.lecturas_de_planilla += 1
            entrada["inscriptos"] = list(self.inscriptos)
            salida, sesion = procesar(entrada, self.sesion, self.cursos, self.ahora)
        self.sesion = sesion
        if salida["accion"] == "registrar":
            registro = salida["registro"]
            numero = len(self.inscriptos) + 1
            self.inscriptos.append({"codigo": registro["codigo"], "dni": registro["dni"], "numero": numero})
            evento = {"evento": "registro_ok", "chat_id": "123", "mensaje": "", "numero": numero, "inscriptos": None}
            salida_registro, self.sesion = procesar(evento, self.sesion, self.cursos, self.ahora)
            salida_registro["registro"] = registro
            return salida_registro
        return salida


def completar_datos(chat):
    chat.enviar("Juan Pérez")
    chat.enviar("40.123.456")
    chat.enviar("juan@gmail.com")
    return chat.enviar("3442 123456")


class ConsultasTest(unittest.TestCase):
    def test_menu_se_arma_desde_el_csv(self):
        respuesta = Conversacion().enviar("hola")["respuesta"]
        for curso in cargar_cursos(CSV_PATH):
            self.assertIn(curso["curso"], respuesta)

    def test_curso_con_palabra_curso_no_devuelve_menu(self):
        respuesta = Conversacion().enviar("quiero el curso de yoga")["respuesta"]
        self.assertIn("Curso: Yoga y Relajación", respuesta)

    def test_saludo_con_curso_responde_el_curso(self):
        self.assertIn("Curso: Cocina Profesional", Conversacion().enviar("Hola, info de cocina")["respuesta"])

    def test_agradecimiento_con_curso_responde_el_curso(self):
        self.assertIn("Curso: Yoga", Conversacion().enviar("gracias, y el de yoga?")["respuesta"])

    def test_acentos_no_generan_inferencia(self):
        salida = Conversacion().enviar("Programación")
        self.assertEqual(salida["tipo"], "EXITO_DIRECTO")
        self.assertNotIn("Inferí", salida["respuesta"])

    def test_error_de_tipeo_se_infiere(self):
        salida = Conversacion().enviar("peluqeria")
        self.assertTrue(salida["tipo"].startswith("EXITO_FUZZY"))
        self.assertIn("Peluquería y Estilismo", salida["respuesta"])

    def test_diseno_con_enie(self):
        self.assertIn("Diseño Gráfico", Conversacion().enviar("diseño")["respuesta"])

    def test_otras_palabras_del_nombre_del_curso(self):
        self.assertIn("Curso: Dibujo y Pintura", Conversacion().enviar("clases de pintura")["respuesta"])
        self.assertIn("Curso: Guitarra y Música", Conversacion().enviar("algo de música")["respuesta"])
        self.assertIn("Curso: Robótica para Niños", Conversacion().enviar("cursos para niños")["respuesta"])

    def test_frase_sin_curso_no_sugiere_cualquier_cosa(self):
        self.assertEqual(Conversacion().enviar("y que onda con eso")["tipo"], "NO_RECONOCIDO")

    def test_menu_con_error_de_tipeo(self):
        self.assertEqual(Conversacion().enviar("mnu")["tipo"], "INFO_MENU")

    def test_despedida(self):
        self.assertEqual(Conversacion().enviar("muchas gracias")["tipo"], "INFO_DESPEDIDA")

    def test_audio_no_se_toma_como_consulta(self):
        self.assertEqual(Conversacion().enviar("0:12")["tipo"], "CONTENIDO_NO_SOPORTADO")

    def test_no_responde_su_propio_mensaje(self):
        chat = Conversacion()
        menu = chat.enviar("hola")["respuesta"]
        self.assertEqual(chat.enviar(menu)["tipo"], "IGNORADO_PROPIO")

    def test_info_del_curso_muestra_cupos_desde_la_planilla(self):
        chat = Conversacion(inscriptos=[{"codigo": "yoga", "dni": "30111222", "numero": 1}])
        respuesta = chat.enviar("yoga")["respuesta"]
        self.assertIn("Cupos disponibles: 19 de 20", respuesta)
        self.assertIn("INSCRIBIRME", respuesta)
        self.assertEqual(chat.lecturas_de_planilla, 1)

    def test_menu_no_lee_la_planilla(self):
        chat = Conversacion()
        chat.enviar("hola")
        self.assertEqual(chat.lecturas_de_planilla, 0)

    def test_curso_sin_cupo_no_ofrece_inscripcion(self):
        chat = Conversacion(inscriptos=[{"codigo": "yoga", "dni": "30111222", "numero": 1}], cupo=1)
        respuesta = chat.enviar("yoga")["respuesta"]
        self.assertIn("Cupos disponibles: 0 de 1", respuesta)
        self.assertIn("no tiene cupos disponibles", respuesta)
        self.assertNotIn("INSCRIBIRME", respuesta)


class PreinscripcionTest(unittest.TestCase):
    def test_flujo_completo(self):
        chat = Conversacion()
        chat.enviar("yoga")
        self.assertIn("nombre y apellido", chat.enviar("inscribirme")["respuesta"])
        resumen = completar_datos(chat)["respuesta"]
        for dato in ("Yoga y Relajación", "Juan Pérez", "40123456", "juan@gmail.com", "3442123456"):
            self.assertIn(dato, resumen)
        salida = chat.enviar("sí")
        self.assertEqual(salida["tipo"], "PREINSCRIPCION_REGISTRADA")
        self.assertIn("N° 1", salida["respuesta"])
        self.assertEqual(salida["registro"], {"codigo": "yoga", "curso": "Yoga y Relajación", "nombre": "Juan Pérez",
                                              "dni": "40123456", "email": "juan@gmail.com", "telefono": "3442123456"})
        self.assertNotIn("paso", chat.sesion)

    def test_pedido_con_curso_en_el_mismo_mensaje(self):
        respuesta = Conversacion().enviar("quiero inscribirme a cocina")["respuesta"]
        self.assertIn("Vamos a inscribirte en Cocina Profesional", respuesta)

    def test_pedido_sin_curso_pregunta_cual(self):
        chat = Conversacion()
        self.assertIn("¿A qué curso", chat.enviar("me quiero anotar")["respuesta"])
        self.assertIn("Programación", chat.enviar("programacion")["respuesta"])

    def test_datos_invalidos_se_vuelven_a_pedir(self):
        chat = Conversacion()
        chat.enviar("inscribirme a yoga")
        self.assertIn("⚠️", chat.enviar("Juan")["respuesta"])
        chat.enviar("Juan Pérez")
        self.assertIn("⚠️", chat.enviar("12.34")["respuesta"])
        chat.enviar("40123456")
        self.assertIn("⚠️", chat.enviar("juan@mail")["respuesta"])
        chat.enviar("juan@gmail.com")
        self.assertIn("⚠️", chat.enviar("123")["respuesta"])
        self.assertIn("Revisá tus datos", chat.enviar("+54 9 3442 123456")["respuesta"])

    def test_no_vuelve_a_cargar_todos_los_datos(self):
        chat = Conversacion()
        chat.enviar("inscribirme a yoga")
        completar_datos(chat)
        self.assertIn("nombre y apellido", chat.enviar("no")["respuesta"])
        self.assertEqual(chat.sesion["datos"], {})
        chat.enviar("Ana Gómez")
        chat.enviar("41222333")
        chat.enviar("ana@gmail.com")
        self.assertIn("Ana Gómez", chat.enviar("3442 654321")["respuesta"])

    def test_respuesta_ambigua_en_la_confirmacion(self):
        chat = Conversacion()
        chat.enviar("inscribirme a yoga")
        completar_datos(chat)
        self.assertEqual(chat.enviar("mmm")["tipo"], "PREINSCRIPCION_CONFIRMACION_PENDIENTE")
        self.assertEqual(chat.inscriptos, [])

    def test_cancelar(self):
        chat = Conversacion()
        chat.enviar("inscribirme a yoga")
        chat.enviar("Juan Pérez")
        self.assertEqual(chat.enviar("cancelar")["tipo"], "PREINSCRIPCION_CANCELADA")
        self.assertNotIn("paso", chat.sesion)

    def test_sin_cupo_no_se_ofrece_el_formulario(self):
        chat = Conversacion(inscriptos=[{"codigo": "yoga", "dni": "30111222", "numero": 1}], cupo=1)
        self.assertEqual(chat.enviar("inscribirme a yoga")["tipo"], "PREINSCRIPCION_SIN_CUPO")
        self.assertNotIn("paso", chat.sesion)

    def test_cupo_ocupado_antes_de_confirmar(self):
        chat = Conversacion(cupo=1)
        chat.enviar("inscribirme a yoga")
        completar_datos(chat)
        chat.inscriptos.append({"codigo": "yoga", "dni": "30111222", "numero": 1})
        salida = chat.enviar("si")
        self.assertEqual(salida["tipo"], "PREINSCRIPCION_SIN_CUPO")
        self.assertEqual(len(chat.inscriptos), 1)

    def test_dni_duplicado_en_el_paso_del_dni(self):
        chat = Conversacion(inscriptos=[{"codigo": "yoga", "dni": "40123456", "numero": 1}])
        chat.enviar("inscribirme a yoga")
        chat.enviar("Juan Pérez")
        self.assertEqual(chat.enviar("40123456")["tipo"], "PREINSCRIPCION_DUPLICADA")

    def test_mismo_dni_en_otro_curso_esta_permitido(self):
        chat = Conversacion(inscriptos=[{"codigo": "cocina", "dni": "40123456", "numero": 1}])
        chat.enviar("inscribirme a yoga")
        completar_datos(chat)
        self.assertEqual(chat.enviar("si")["tipo"], "PREINSCRIPCION_REGISTRADA")

    def test_dni_duplicado_al_confirmar(self):
        chat = Conversacion()
        chat.enviar("inscribirme a yoga")
        completar_datos(chat)
        chat.inscriptos.append({"codigo": "yoga", "dni": "40123456", "numero": 1})
        self.assertEqual(chat.enviar("si")["tipo"], "PREINSCRIPCION_DUPLICADA")

    def test_error_al_escribir_la_planilla_permite_reintentar(self):
        chat = Conversacion()
        chat.enviar("inscribirme a yoga")
        completar_datos(chat)
        entrada = {"evento": "mensaje", "chat_id": "123", "mensaje": "si", "inscriptos": []}
        salida, chat.sesion = procesar(entrada, chat.sesion, chat.cursos, chat.ahora)
        self.assertEqual(salida["accion"], "registrar")
        fallo = {"evento": "registro_fallido", "chat_id": "123", "mensaje": "", "inscriptos": None}
        salida, chat.sesion = procesar(fallo, chat.sesion, chat.cursos, chat.ahora)
        self.assertEqual(salida["tipo"], "PREINSCRIPCION_ERROR_PLANILLA")
        self.assertEqual(chat.enviar("si")["tipo"], "PREINSCRIPCION_REGISTRADA")

    def test_comillas_se_quitan_del_nombre(self):
        chat = Conversacion()
        chat.enviar("inscribirme a yoga")
        chat.enviar('Juan "Pepe" Pérez')
        self.assertNotIn('"', chat.sesion["datos"]["nombre"])

    def test_conversacion_vencida_empieza_de_cero(self):
        chat = Conversacion()
        chat.enviar("inscribirme a yoga")
        chat.enviar("Juan Pérez")
        chat.ahora = AHORA + timedelta(minutes=31)
        self.assertEqual(chat.enviar("40123456")["tipo"], "NO_RECONOCIDO")
        self.assertNotIn("paso", chat.sesion)

    def test_audio_durante_la_preinscripcion_repite_la_pregunta(self):
        chat = Conversacion()
        chat.enviar("inscribirme a yoga")
        respuesta = chat.enviar("0:05")["respuesta"]
        self.assertIn("nombre y apellido", respuesta)
        self.assertEqual(chat.sesion["paso"], "nombre")


if __name__ == "__main__":
    unittest.main()
