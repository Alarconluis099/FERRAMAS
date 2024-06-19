import unittest
from unittest.mock import patch, MagicMock
from venv import logger
from flask_testing import TestCase
import sys
import os
import logging

    # Verificar que el directorio del proyecto esté en el path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

class MyTest(TestCase):
    logger.info('Started')
    def create_app(self):
        # Configurar aplicación Flask para los tests
        app.config['TESTING'] = True
        app.config['DEBUG'] = False        
        app.config['MYSQL_USER'] = 'fake_user'
        app.config['MYSQL_PASSWORD'] = 'fake_password'
        app.config['MYSQL_DB'] = 'fake_db'
        app.config['MYSQL_HOST'] = 'localhost'
        return app

    def setUp(self):
        # Parchar el método connect de MySQLdb
        self.patcher = patch('MySQLdb.connect')
        self.mock_connect = self.patcher.start()
        
        # Mock para la conexión y el cursor
        self.mock_connection = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_connect.return_value = self.mock_connection
        self.mock_connection.cursor.return_value = self.mock_cursor
        
        # Configurar el cursor mock para que devuelva datos de prueba
        self.mock_cursor.execute.return_value = None
        self.mock_cursor.fetchall.return_value = [
            (1, 1, "Hammer",  "A tool for hammering nails.",  10),
            (2, 2, "Screwdriver", "A tool for driving screws.", 15)
        ]
        self.mock_cursor.description = [
            ('id_tool',), ('id_tools_type',), ('name',), ('description',), ('stock',)
        ]

    def tearDown(self):
        # Detener el parche
        self.patcher.stop()

        # Test obtener tools
    def test_get_tools(self):
        response = self.client.get('/tools')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json, list)
        self.assertGreater(len(response.json), 0)
        self.assertIn("id_tool", response.json[0])
        self.assertIn("id_tools_type", response.json[0])
        self.assertIn("name", response.json[0])
        self.assertIn("description", response.json[0])
        self.assertIn("stock", response.json[0])
        print("aaa",response.json[0])


        # Test eliminar tools
    @patch('app.routes.delete_tools')
    def test_delete_tool(self, mock_delete_tools):
        # Simular que la herramienta fue eliminada correctamente
        mock_delete_tools.return_value = True
        response = self.client.delete('/tools/1')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json, dict)
        self.assertIn('message', response.json)
        self.assertEqual(response.json['message'], 'Herramienta eliminada correctamente')

        # Simular que la herramienta no fue encontrada
        mock_delete_tools.return_value = False
        response = self.client.delete('/tools/99')
        self.assertEqual(response.status_code, 404)
        self.assertIsInstance(response.json, dict)
        self.assertIn('message', response.json)
        self.assertEqual(response.json['message'], 'Herramienta no encontrada')


        # Test actualizar tools
    @patch('app.routes.update_tools')
    def test_update_tool(self, mock_update_tools):
        # Simular que la herramienta fue actualizada correctamente
        mock_update_tools.return_value = True
        tool_data = {
            "id_tools_type": 1,
            "name": "Updated Hammer",
            "description": "An updated tool for hammering nails.",
            "stock": 12,
            "precio": 22.0
        }
        response = self.client.put('/tools/1', json = tool_data)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json, dict)
        self.assertIn('message', response.json)
        self.assertEqual(response.json['message'], 'Herramienta actualizada correctamente')

        # # Simular que la herramienta no fue actualizada
        # mock_update_tools.return_value = False
        # response = self.client.put('/tools/99', json = tool_data)
        # self.assertEqual(response.status_code, 404)
        # self.assertIsInstance(response.json, dict)
        # self.assertIn('message', response.json)
        # self.assertEqual(response.json['message'], 'Herramienta no actualizada')
    
    
       
if __name__ == '__main__':
    unittest.main()