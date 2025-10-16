import unittest
from app import app
from app import models
from flask import current_app

class TestProductos(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_fetch_all_tools(self):
        tools = models.fetch_all_tools()
        self.assertIsInstance(tools, list)

    def test_insert_and_delete_tool(self):
        tool_data = {
            'id_tool': 9999,
            'name': 'TestTool',
            'description': 'Herramienta de prueba',
            'stock': 10,
            'precio': 1234
        }
        inserted = models.insert_tools(tool_data)
        self.assertTrue(inserted)
        deleted = models.delete_tools(9999)
        self.assertTrue(deleted)

    def test_fetch_tools_filtered(self):
        items, total = models.fetch_tools_filtered(q='Test', per_page=5)
        self.assertTrue(isinstance(items, list) or isinstance(items, tuple))
        self.assertIsInstance(total, int)

    def test_fetch_tool_suggestions(self):
        suggestions = models.fetch_tool_suggestions('Test', limit=3)
        self.assertTrue(isinstance(suggestions, list) or isinstance(suggestions, tuple))

    def test_update_tools(self):
        tool_data = {
            'id_tool': 9998,
            'name': 'UpdateTool',
            'description': 'Actualizar',
            'stock': 5,
            'precio': 500
        }
        models.insert_tools(tool_data)
        updated = models.update_tools(9998, {
            'name': 'UpdateTool2',
            'description': 'Actualizado',
            'stock': 7,
            'precio': 700
        })
        self.assertTrue(updated)
        models.delete_tools(9998)

    def test_fetch_top_products(self):
        top = models.fetch_top_products(limit=2)
        self.assertTrue(isinstance(top, list) or isinstance(top, tuple))

if __name__ == '__main__':
    unittest.main()
