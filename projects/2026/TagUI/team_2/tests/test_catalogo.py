import os
import unittest
import pandas as pd

from catalogo import (
    normalizar_texto,
    extraer_tokens_relevantes,
    generar_palabras_clave_automaticas,
    evaluar_item_contra_catalogo,
    enriquecer_reporte_excel,
    ITEMS_CATALOGO_POR_DEFECTO,
    COLUMNAS_CATALOGO,
)


class TestCatalogoYMatching(unittest.TestCase):

    def setUp(self):
        self.df_catalogo = pd.DataFrame(ITEMS_CATALOGO_POR_DEFECTO, columns=COLUMNAS_CATALOGO)

    def test_normalizar_texto(self):
        texto = "¡PAPELES P/FOTOCOPIADORA; Resma A4 de 80g!"
        norm = normalizar_texto(texto)
        self.assertNotIn("¡", norm)
        self.assertNotIn("!", norm)
        self.assertNotIn(";", norm)
        self.assertIn("papeles", norm)
        self.assertIn("resma", norm)

    def test_extraer_tokens_relevantes(self):
        texto = "Papel para fotocopiadora con impresion laser"
        tokens = extraer_tokens_relevantes(texto)
        self.assertIn("papel", tokens)
        self.assertIn("fotocopiadora", tokens)
        self.assertIn("impresion", tokens)
        # 'para' y 'con' deben filtrarse por stopwords
        self.assertNotIn("para", tokens)
        self.assertNotIn("con", tokens)

    def test_generar_palabras_clave_automaticas(self):
        desc = "PAPELES P/FOTOCOPIADORA; ANCHO: 210 mm, LARGO: 297 mm, PRESENTACION: RESMA X 500"
        keywords = generar_palabras_clave_automaticas(desc)
        self.assertTrue(len(keywords) > 0)
        self.assertIn("papeles", keywords.lower())

    def test_match_codigo_exacto(self):
        item_pliego = {
            'renglon': '1',
            'codigo_item': '2.3.2-1571.23',
            'descripcion': 'Item de prueba con código oficial',
            'cantidad': '10',
            'unidad_medida': 'RESMA',
        }
        res = evaluar_item_contra_catalogo(item_pliego, self.df_catalogo)
        self.assertTrue(res['coincide'])
        self.assertEqual(res['score'], 100.0)
        self.assertIn("Código exacto", res['criterio'])

    def test_match_misma_clase_codigo(self):
        item_pliego = {
            'renglon': '2',
            'codigo_item': '2.3.2-1571.99',  # Misma clase '2.3.2-1571'
            'descripcion': 'Otro tipo de papel de la misma clase',
            'cantidad': '5',
            'unidad_medida': 'RESMA',
        }
        res = evaluar_item_contra_catalogo(item_pliego, self.df_catalogo)
        self.assertTrue(res['coincide'])
        self.assertEqual(res['score'], 88.0)
        self.assertIn("Misma clase", res['criterio'])

    def test_match_por_palabras_clave(self):
        item_pliego = {
            'renglon': '3',
            'codigo_item': '9.9.9-9999.99',  # Código no coincidente
            'descripcion': 'Adquisición de resma de papel a4 para fotocopiadora e impresión de expedientes',
            'cantidad': '20',
            'unidad_medida': 'UNIDAD',
        }
        res = evaluar_item_contra_catalogo(item_pliego, self.df_catalogo)
        self.assertTrue(res['coincide'])
        self.assertGreaterEqual(res['score'], 65.0)
        self.assertIn("Palabras clave", res['criterio'])

    def test_sin_coincidencia_item_irrelevante(self):
        item_pliego = {
            'renglon': '4',
            'codigo_item': '8.1.1-1234.56',
            'descripcion': 'Neumáticos radiales para camiones de carga pesada rodado 22.5',
            'cantidad': '8',
            'unidad_medida': 'UNIDAD',
        }
        res = evaluar_item_contra_catalogo(item_pliego, self.df_catalogo)
        self.assertFalse(res['coincide'])
        self.assertEqual(res['score'], 0.0)
        self.assertEqual(res['criterio'], 'Sin coincidencia')

    def test_enriquecer_reporte_excel(self):
        ruta_origen = os.path.join(os.path.dirname(__file__), 'mock_procesos.xlsx')

        # Crear un DataFrame mock simulando la salida de COMPR.AR
        df_procesos = pd.DataFrame([
            {
                'Número de Proceso': '38-0001-LPU26',
                'Nombre del Proceso': 'Compra de insumos de librería y computación',
                'Fecha de Apertura': '10/04/2026 10:00',
                'Unidad Ejecutora': 'Facultad Regional Concepción del Uruguay',
            }
        ])
        df_procesos.to_excel(ruta_origen, index=False, engine='openpyxl')

        items_mock = {
            '38-0001-LPU26': [
                {
                    'renglon': '1',
                    'objeto_gasto': '2.3.2',
                    'codigo_item': '2.3.2-1571.23',
                    'descripcion': 'Resma de papel A4',
                    'cantidad': '50',
                    'unidad_medida': 'RESMA',
                },
                {
                    'renglon': '2',
                    'objeto_gasto': '8.1.1',
                    'codigo_item': '8.1.1-9999.1',
                    'descripcion': 'Neumático de tractor',
                    'cantidad': '2',
                    'unidad_medida': 'UNIDAD',
                }
            ]
        }

        try:
            ruta_xlsx, resumen = enriquecer_reporte_excel(ruta_origen, items_mock)
            self.assertTrue(os.path.isfile(ruta_xlsx))
            self.assertTrue(ruta_xlsx.endswith('.xlsx'))

            # Leer las dos hojas generadas
            df_hoja_procesos = pd.read_excel(ruta_xlsx, sheet_name='Procesos')
            df_hoja_items = pd.read_excel(ruta_xlsx, sheet_name='Items_Licitados')

            self.assertIn('Coincide con Catálogo', df_hoja_procesos.columns)
            self.assertEqual(df_hoja_procesos['Coincide con Catálogo'].iloc[0], 'SÍ')
            self.assertEqual(df_hoja_procesos['Ítems Coincidentes'].iloc[0], '1 de 2')

            self.assertEqual(len(df_hoja_items), 2)
            self.assertIn('Puntaje Match (%)', df_hoja_items.columns)
            self.assertEqual(df_hoja_items['Coincide con Catálogo'].iloc[0], 'SÍ')
            self.assertEqual(df_hoja_items['Coincide con Catálogo'].iloc[1], 'NO')

            # Limpiar archivo generado
            if os.path.exists(ruta_xlsx):
                os.remove(ruta_xlsx)
        finally:
            if os.path.exists(ruta_origen):
                os.remove(ruta_origen)


if __name__ == '__main__':
    unittest.main()
