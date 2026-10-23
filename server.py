"""VigiMarket HTTP application with SQLite-backed accounts and listings."""

import base64
from collections import defaultdict, deque
from contextlib import contextmanager
import hashlib
import hmac
from http.cookies import CookieError, SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).parent
DB = Path(os.environ.get('DATA_DIR') or ROOT / 'data') / 'vigimarket.db'
DB.parent.mkdir(parents=True, exist_ok=True)
CATEGORIES = {
    'Uniformes y EPP', 'Equipamiento de seguridad',
    'Profesionales de vigilancia', 'Capacitación y formación',
}
MAX_IMAGE_BYTES = 1024 * 1024


@contextmanager
def connect():
    connection = sqlite3.connect(DB, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


with connect() as connection:
    connection.executescript('''
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password TEXT);
        CREATE TABLE IF NOT EXISTS sessions(
            token TEXT PRIMARY KEY, user_id INTEGER, expires INTEGER);
        CREATE TABLE IF NOT EXISTS listings(
            id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, category TEXT,
            description TEXT, location TEXT, image TEXT, phone TEXT,
            price REAL, type TEXT);
        CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires);
    ''')


def password(value, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + ':' + hashlib.scrypt(
        value.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()


# An unknown account performs the same password work as an existing account.
DUMMY_PASSWORD = password(secrets.token_urlsafe(24))


class RequestError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class AuthLimiter:
    """Short-lived, process-local limits on expensive authentication requests."""
    def __init__(self):
        self.attempts = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, ip, email):
        now = time.monotonic()
        # Account limits work even behind a reverse proxy sharing one IP.
        keys = [('ip:' + ip, 120), ('email:' + email, 10)]
        with self.lock:
            for key in list(self.attempts):
                queue = self.attempts[key]
                while queue and queue[0] <= now - 60:
                    queue.popleft()
                if not queue:
                    del self.attempts[key]
            if any(len(self.attempts.get(key, ())) >= limit for key, limit in keys):
                return False
            # Bound memory when many distinct addresses/accounts are submitted.
            if len(self.attempts) >= 10000:
                return False
            for key, _ in keys:
                self.attempts[key].append(now)
            return True


AUTH_LIMITER = AuthLimiter()


def text_field(data, name, maximum, required=False):
    value = data.get(name, '')
    if not isinstance(value, str):
        raise RequestError('Los campos de texto deben contener texto válido.')
    value = value.strip()
    if len(value) > maximum:
        raise RequestError(f'El campo {name} supera el máximo de {maximum} caracteres.')
    if required and not value:
        raise RequestError('Completa los campos obligatorios.')
    return value


def validate_image(value):
    if value.startswith('https://'):
        parsed = urlsplit(value)
        if (len(value) > 2048 or not parsed.hostname or parsed.username
                or parsed.password or any(ch.isspace() for ch in value)):
            raise RequestError('Ingresa una URL HTTPS válida para la imagen.')
        return
    match = re.fullmatch(r'data:image/(jpeg|png|webp);base64,([A-Za-z0-9+/=]+)', value)
    if not match:
        raise RequestError('Usa una imagen JPG, PNG, WebP o una URL HTTPS.')
    try:
        image = base64.b64decode(match[2], validate=True)
    except ValueError:
        raise RequestError('La imagen no tiene un formato válido.')
    if len(image) > MAX_IMAGE_BYTES:
        raise RequestError('La imagen debe pesar como máximo 1 MB.')
    signatures = {
        'jpeg': image.startswith(b'\xff\xd8\xff'),
        'png': image.startswith(b'\x89PNG\r\n\x1a\n'),
        'webp': image.startswith(b'RIFF') and image[8:12] == b'WEBP',
    }
    if not signatures[match[1]]:
        raise RequestError('La imagen no corresponde al formato indicado.')


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'static'), **kwargs)

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('X-Frame-Options', 'DENY')
        super().end_headers()

    def reply(self, data, status=200, cookie=None):
        body = json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        if status == 429:
            self.send_header('Retry-After', '60')
        self.end_headers()
        self.wfile.write(body)

    def cookie_token(self):
        try:
            cookie = SimpleCookie(self.headers.get('Cookie', ''))
            return cookie['session'].value if 'session' in cookie else None
        except (CookieError, ValueError):
            return None

    def user(self, connection):
        token = self.cookie_token()
        if not token or len(token) > 128:
            return None
        return connection.execute('''
            SELECT users.id, name, email FROM users
            JOIN sessions ON users.id = sessions.user_id
            WHERE token = ? AND expires > strftime('%s', 'now')
        ''', (token,)).fetchone()

    def do_GET(self):
        try:
            if self.path == '/api/me':
                with connect() as connection:
                    user = self.user(connection)
                    result = dict(user) if user else None
                return self.reply(result)
            if self.path == '/api/listings':
                with connect() as connection:
                    result = [dict(row) for row in connection.execute('''
                        SELECT listings.*, users.name AS provider FROM listings
                        JOIN users ON users.id = listings.user_id
                        ORDER BY listings.id DESC
                    ''')]
                return self.reply(result)
            if self.path.startswith('/api/'):
                return self.reply({'error': 'No encontrado'}, 404)
            return super().do_GET()
        except sqlite3.Error:
            return self.reply({'error': 'No se pudo consultar la información. Reintenta en un momento.'}, 503)

    def read_request(self):
        origin = self.headers.get('Origin')
        if origin:
            parsed = urlsplit(origin)
            if (parsed.scheme not in ('http', 'https') or
                    parsed.netloc.lower() != self.headers.get('Host', '').lower()):
                raise RequestError('Origen no permitido', 403)
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            raise RequestError('Origen no permitido', 403)
        if self.headers.get_content_type() != 'application/json':
            raise RequestError('Envía la solicitud como JSON.', 415)
        size_text = self.headers.get('Content-Length', '')
        if not re.fullmatch(r'[0-9]+', size_text):
            raise RequestError('Tamaño de solicitud no válido.')
        size = int(size_text)
        limit = 1500000 if self.path == '/api/listings' else 16384
        if size > limit:
            raise RequestError('La solicitud es demasiado grande; la imagen debe pesar como máximo 1 MB.', 413)
        raw = self.rfile.read(size)
        if len(raw) != size:
            raise RequestError('La solicitud está incompleta.')
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeError):
            raise RequestError('La solicitud contiene JSON no válido.')
        if not isinstance(data, dict):
            raise RequestError('La solicitud debe ser un objeto JSON.')
        return data

    def authenticate(self, connection, data):
        email = text_field(data, 'email', 254, required=True).lower()
        value = data.get('password', '')
        if not isinstance(value, str) or not 1 <= len(value) <= 128:
            raise RequestError('La contraseña debe tener entre 1 y 128 caracteres.')
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            raise RequestError('Ingresa un correo válido.')
        if not AUTH_LIMITER.allow(self.client_address[0], email):
            raise RequestError('Demasiados intentos. Espera un minuto y vuelve a intentarlo.', 429)
        if self.path == '/api/register':
            name = text_field(data, 'name', 120, required=True)
            if len(name) < 2 or len(value) < 8:
                raise RequestError('Ingresa tu nombre y una contraseña de al menos 8 caracteres.')
            try:
                connection.execute('INSERT INTO users(name,email,password) VALUES(?,?,?)',
                                   (name, email, password(value)))
            except sqlite3.IntegrityError:
                raise RequestError('Este correo ya tiene una cuenta.')
        user = connection.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        expected = user['password'] if user else DUMMY_PASSWORD
        matches = hmac.compare_digest(expected, password(value, expected.split(':')[0]))
        if not user or not matches:
            raise RequestError('Correo o contraseña incorrectos.', 401)
        connection.execute("DELETE FROM sessions WHERE expires <= strftime('%s','now')")
        previous_token = self.cookie_token()
        if previous_token:
            connection.execute('DELETE FROM sessions WHERE token=?', (previous_token,))
        token = secrets.token_urlsafe(32)
        connection.execute("INSERT INTO sessions VALUES(?,?,strftime('%s','now')+2592000)",
                           (token, user['id']))
        secure = '; Secure' if os.getenv('COOKIE_SECURE') == '1' else ''
        return ({'id': user['id'], 'name': user['name'], 'email': user['email']}, 200,
                f'session={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=2592000{secure}')

    def create_listing(self, connection, data):
        user = self.user(connection)
        if not user:
            raise RequestError('Inicia sesión para publicar.', 401)
        values = {key: text_field(data, key, maximum, key in ('title', 'description', 'location', 'image'))
                  for key, maximum in [('title', 160), ('category', 100), ('description', 5000),
                                       ('location', 100), ('image', 1450000), ('phone', 15), ('type', 20)]}
        if values['category'] not in CATEGORIES:
            raise RequestError('Selecciona una categoría válida.')
        if values['type'] not in ('Producto', 'Servicio'):
            raise RequestError('Selecciona Producto o Servicio como tipo de publicación.')
        validate_image(values['image'])
        if values['phone'] and not re.fullmatch(r'[0-9]{9,15}', values['phone']):
            raise RequestError('Ingresa el teléfono con código de país, solo números.')
        raw_price = data.get('price')
        price = None
        if raw_price not in ('', None):
            try:
                if isinstance(raw_price, bool):
                    raise ValueError()
                price = float(raw_price)
            except (ValueError, TypeError):
                raise RequestError('Precio no válido.')
            if not math.isfinite(price) or not 0 <= price <= 1e9:
                raise RequestError('Precio no válido.')
        connection.execute('''
            INSERT INTO listings(user_id,title,category,description,location,image,phone,price,type)
            VALUES(?,?,?,?,?,?,?,?,?)
        ''', (user['id'], values['title'], values['category'], values['description'],
              values['location'], values['image'], values['phone'], price, values['type']))
        return {'ok': True}, 201, None

    def do_POST(self):
        try:
            data = self.read_request()
            with connect() as connection:
                if self.path in ('/api/register', '/api/login'):
                    result = self.authenticate(connection, data)
                elif self.path == '/api/logout':
                    token = self.cookie_token()
                    if token:
                        connection.execute('DELETE FROM sessions WHERE token=?', (token,))
                    secure = '; Secure' if os.getenv('COOKIE_SECURE') == '1' else ''
                    result = ({'ok': True}, 200,
                              f'session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0{secure}')
                elif self.path == '/api/listings':
                    result = self.create_listing(connection, data)
                else:
                    raise RequestError('No encontrado', 404)
            # The transaction has committed and the connection has closed here.
            return self.reply(*result)
        except RequestError as error:
            return self.reply({'error': str(error)}, error.status)
        except (ValueError, TypeError):
            return self.reply({'error': 'La solicitud contiene datos no válidos.'}, 400)
        except sqlite3.Error:
            return self.reply({'error': 'No se pudo guardar la información. Reintenta en un momento.'}, 503)


if __name__ == '__main__':
    port = int(os.getenv('PORT', '3000'))
    print(f'VigiMarket en puerto {port}', flush=True)
    ThreadingHTTPServer(('0.0.0.0', port), Handler).serve_forever()
