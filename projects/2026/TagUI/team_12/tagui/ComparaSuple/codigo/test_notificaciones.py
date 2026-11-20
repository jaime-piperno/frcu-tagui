"""Suite de pruebas unitarias y de integración para notificaciones.py.

Permite validar el filtrado, formateo y la API de Telegram de forma 100% aislada
sin necesidad de ejecutar TagUI, abrir Chrome ni interactuar con la interfaz gráfica.
"""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch, MagicMock

# Asegurar que el directorio de código esté en el path
CODIGO_DIR = Path(__file__).resolve().parent
if str(CODIGO_DIR) not in sys.path:
    sys.path.insert(0, str(CODIGO_DIR))

from notificaciones import (
    formatear_moneda,
    filtrar_mejores_ofertas,
    construir_mensaje_telegram,
    enviar_alerta_telegram,
    notificar_mejores_ofertas
)


class TestNotificaciones(unittest.TestCase):

    def setUp(self):
        """Genera un payload simulado idéntico al producido por process_run(folder)."""
        self.mock_payload = {
            'run_id': '20261103-180000-abc123',
            'created_at': '2026-11-03T18:00:00',
            'products': [
                {
                    'id': 'P0001',
                    'name': 'Whey Protein 100% 1kg',
                    'brand': 'Star Nutrition',
                    'category': 'Proteínas'
                },
                {
                    'id': 'P0002',
                    'name': 'Creatina Creapure 300g',
                    'brand': 'ENA Sport',
                    'category': 'Creatinas'
                },
                {
                    'id': 'P0003',
                    'name': 'BCAA 2000 120 tabs',
                    'brand': 'Universal',
                    'category': 'Aminoácidos'
                }
            ],
            'providers': [
                {'id': 'proteviking', 'name': 'ProteViking'},
                {'id': 'mercadolibre', 'name': 'Mercado Libre'},
                {'id': 'cbdeportes', 'name': 'CB Deportes'}
            ],
            'results': [
                # P0001: 2 tiendas válidas; proteviking ($35.000) vs mercadolibre ($38.500)
                {
                    'product_id': 'P0001',
                    'provider': 'mercadolibre',
                    'status': 'ok',
                    'price': 38500.0,
                    'method': '1 pago',
                    'title': 'Proteina Star Nutrition Whey 1kg',
                    'url': 'https://articulo.mercadolibre.com.ar/MLA-1111'
                },
                {
                    'product_id': 'P0001',
                    'provider': 'proteviking',
                    'status': 'ok',
                    'price': 35000.0,
                    'method': 'Transferencia bancaria',
                    'title': 'Star Nutrition Platinum Whey 1000g',
                    'url': 'https://proteviking.com.ar/whey-star-1kg'
                },
                # P0002: cbdeportes ($41.000) con stock ok; mercadolibre con status sin_stock
                {
                    'product_id': 'P0002',
                    'provider': 'cbdeportes',
                    'status': 'ok',
                    'price': 41000.0,
                    'method': 'Efectivo',
                    'title': 'Creatina Creapure ENA 300g Polvo',
                    'url': 'https://cbdeportes.com/creatina-ena-300g'
                },
                {
                    'product_id': 'P0002',
                    'provider': 'mercadolibre',
                    'status': 'sin_stock',
                    'price': None,
                    'method': '',
                    'title': 'Creatina ENA',
                    'url': ''
                },
                # P0003: Sin ofertas disponibles (solo status 'revisar')
                {
                    'product_id': 'P0003',
                    'provider': 'cbdeportes',
                    'status': 'revisar',
                    'price': 15000.0,
                    'method': '',
                    'title': 'BCAA Universal',
                    'url': ''
                }
            ]
        }

    def test_formatear_moneda(self):
        """Prueba que el formateo monetario sea consistente en formato argentino."""
        self.assertEqual(formatear_moneda(35000), "$ 35.000")
        self.assertEqual(formatear_moneda(38500.5), "$ 38.500,50")
        self.assertEqual(formatear_moneda(1250.75), "$ 1.250,75")
        self.assertEqual(formatear_moneda(None), "$ 0,00")

    def test_filtrar_mejores_ofertas_min_precio(self):
        """Verifica que elija la oferta con el menor precio y excluya estados sin stock/revisar."""
        ofertas = filtrar_mejores_ofertas(self.mock_payload)
        
        # Debe haber encontrado mejores ofertas para P0001 y P0002, ignorando P0003 (status 'revisar')
        self.assertEqual(len(ofertas), 2)
        
        # P0001 debe haber elegido ProteViking ($35.000) y no Mercado Libre ($38.500)
        p1 = next(o for o in ofertas if o['product_id'] == 'P0001')
        self.assertEqual(p1['provider_id'], 'proteviking')
        self.assertEqual(p1['price'], 35000.0)
        self.assertEqual(p1['price_formatted'], '$ 35.000')
        self.assertEqual(p1['provider_name'], 'ProteViking')
        self.assertEqual(p1['url'], 'https://proteviking.com.ar/whey-star-1kg')

        # P0002 debe haber elegido CB Deportes ($41.000)
        p2 = next(o for o in ofertas if o['product_id'] == 'P0002')
        self.assertEqual(p2['provider_id'], 'cbdeportes')
        self.assertEqual(p2['price'], 41000.0)

    def test_construir_mensaje_html(self):
        """Verifica que el mensaje HTML contenga los tags correctos y links sin errores."""
        ofertas = filtrar_mejores_ofertas(self.mock_payload)
        mensajes = construir_mensaje_telegram(ofertas, timestamp="03/11/2026 18:30")
        
        self.assertIsInstance(mensajes, list)
        self.assertEqual(len(mensajes), 1)
        
        texto = mensajes[0]
        self.assertIn("<b>MEJORES OFERTAS DETECTADAS | GRUPO 12</b>", texto)
        self.assertIn("Whey Protein 100% 1kg", texto)
        self.assertIn("Star Nutrition", texto)
        self.assertIn("$ 35.000", texto)
        self.assertIn('href="https://proteviking.com.ar/whey-star-1kg"', texto)
        self.assertIn("Total de ofertas óptimas:</b> 2", texto)

    def test_construir_mensaje_sin_ofertas(self):
        """Verifica el mensaje informativo cuando no hay ofertas confirmadas."""
        mensajes = construir_mensaje_telegram([])
        self.assertEqual(len(mensajes), 1)
        self.assertIn("No se encontraron ofertas con coincidencia exacta", mensajes[0])

    @patch('requests.post')
    def test_enviar_alerta_telegram_mock_ok(self, mock_post):
        """Valida que la función envíe correctamente el payload HTTP al endpoint de Telegram."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        resultado = enviar_alerta_telegram(
            mensaje="<b>Test</b>",
            token="123456:FAKE_TOKEN",
            chat_id="987654321"
        )
        self.assertTrue(resultado)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("123456:FAKE_TOKEN/sendMessage", args[0])
        self.assertEqual(kwargs['json']['parse_mode'], 'HTML')
        self.assertEqual(kwargs['json']['chat_id'], '987654321')

    @patch('requests.post')
    def test_resiliencia_fallo_red_silencioso(self, mock_post):
        """Valida que los fallos de red en Telegram se capturen limpiamente sin romper nada."""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectTimeout("Timeout simulado")

        # No debe lanzar excepción
        resultado = notificar_mejores_ofertas(
            self.mock_payload,
            token="123456:FAKE_TOKEN",
            chat_id="987654321"
        )
        self.assertFalse(resultado)


if __name__ == '__main__':
    print("======================================================================")
    print(" Ejecutando Suite de Pruebas Unitarias de Notificaciones Telegram")
    print("======================================================================")
    unittest.main(verbosity=2)
