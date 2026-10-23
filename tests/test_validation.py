import http.cookiejar
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[1]


class DeploymentValidationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.app = self.root / 'app'
        self.app.mkdir()
        shutil.copy(ROOT / 'server.py', self.app)
        self.data = self.root / 'persistent' / 'data'
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            self.port = s.getsockname()[1]
        self.base = f'http://127.0.0.1:{self.port}'
        self.client = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.process = None
        self.addCleanup(self.stop)
        self.start()

    def start(self):
        self.process = subprocess.Popen(
            [sys.executable, str(self.app / 'server.py')],
            env={**os.environ, 'PORT': str(self.port), 'DATA_DIR': str(self.data)},
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                self.get('/api/me')
                return
            except OSError:
                time.sleep(.03)
        self.fail('Server did not become ready')

    def stop(self):
        if self.process is not None:
            self.process.terminate()
            self.process.wait(timeout=5)
            self.process = None

    def get(self, path):
        with self.client.open(self.base + path, timeout=3) as response:
            return json.load(response)

    def post(self, path, body):
        request = urllib.request.Request(
            self.base + path, data=json.dumps(body).encode(), method='POST',
            headers={'Content-Type': 'application/json'})
        with self.client.open(request, timeout=3) as response:
            return json.load(response)

    def register(self):
        return self.post('/api/register', {
            'name': 'Usuario de prueba', 'email': 'test@example.com',
            'password': 'secure-password-123'})

    def listing(self, **overrides):
        return {
            'title': 'Chaleco', 'category': 'Uniformes y EPP',
            'description': 'Descripción de prueba', 'location': 'Lima',
            'image': 'https://example.com/image.jpg', 'phone': '',
            'price': '120', 'type': 'Producto', **overrides}

    def assert_bad_request(self, path, body, message):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.post(path, body)
        self.assertEqual(caught.exception.code, 400)
        self.assertIn(message, json.load(caught.exception)['error'])

    def test_rejects_non_object_json_without_crashing(self):
        for body in [None, [], 'text', 42, True]:
            with self.subTest(body=body):
                self.assert_bad_request('/api/register', body, 'objeto JSON')
        self.assertIsNone(self.get('/api/me'))

    def test_rejects_nonfinite_prices_without_saving(self):
        self.register()
        for price in ['NaN', 'Infinity', '-Infinity']:
            with self.subTest(price=price):
                self.assert_bad_request('/api/listings', self.listing(price=price), 'Precio no válido')
        self.assertEqual(self.get('/api/listings'), [])

    def test_listing_type_is_validated(self):
        self.register()
        for kind in ['', 'Other', 'producto']:
            with self.subTest(kind=kind):
                self.assert_bad_request('/api/listings', self.listing(type=kind), 'Producto o Servicio')
        for kind in ['Producto', 'Servicio']:
            self.assertTrue(self.post('/api/listings', self.listing(type=kind))['ok'])
        self.assertEqual({row['type'] for row in self.get('/api/listings')}, {'Producto', 'Servicio'})

    def test_configured_data_directory_survives_restart(self):
        self.register()
        self.post('/api/listings', self.listing())
        self.stop()
        self.assertFalse((self.app / 'data').exists())
        with sqlite3.connect(self.data / 'vigimarket.db') as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM users').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM listings').fetchone()[0], 1)
        self.start()
        self.assertEqual(self.get('/api/me')['email'], 'test@example.com')
        self.assertEqual(self.get('/api/listings')[0]['title'], 'Chaleco')


if __name__ == '__main__':
    unittest.main()
