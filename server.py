import os, json, sqlite3, secrets, hashlib, hmac, re, math
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from http.cookies import SimpleCookie
ROOT=Path(__file__).parent
DB=Path(os.environ.get('DATA_DIR') or ROOT/'data')/'vigimarket.db'
DB.parent.mkdir(parents=True,exist_ok=True)
def connect():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
with connect() as c:
    c.executescript('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,email TEXT UNIQUE,password TEXT); CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER,expires INTEGER); CREATE TABLE IF NOT EXISTS listings(id INTEGER PRIMARY KEY,user_id INTEGER,title TEXT,category TEXT,description TEXT,location TEXT,image TEXT,phone TEXT,price REAL,type TEXT);')
def password(value,salt=None):
    salt=salt or secrets.token_hex(16)
    return salt+':'+hashlib.scrypt(value.encode(),salt=salt.encode(),n=16384,r=8,p=1).hex()
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=str(ROOT/'static'),**kw)
    def reply(self,data,status=200,cookie=None):
        body=json.dumps(data).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
        if cookie:self.send_header('Set-Cookie',cookie)
        self.end_headers();self.wfile.write(body)
    def user(self,c):
        try:
            ck=SimpleCookie(self.headers.get('Cookie','')); token=ck['session'].value
            return c.execute("SELECT users.id,name,email FROM users JOIN sessions ON users.id=sessions.user_id WHERE token=? AND expires>strftime('%s','now')",(token,)).fetchone()
        except (KeyError,ValueError):return None
    def do_GET(self):
        if self.path=='/api/me':
            with connect() as c:
                u=self.user(c);return self.reply(dict(u) if u else None)
        if self.path=='/api/listings':
            with connect() as c:return self.reply([dict(r) for r in c.execute('SELECT listings.*,users.name AS provider FROM listings JOIN users ON users.id=listings.user_id ORDER BY listings.id DESC')])
        if self.path.startswith('/api/'):return self.reply({'error':'No encontrado'},404)
        return super().do_GET()
    def do_POST(self):
        origin=self.headers.get('Origin')
        if origin:
            from urllib.parse import urlsplit
            if urlsplit(origin).netloc!=self.headers.get('Host'):return self.reply({'error':'Origen no permitido'},403)
        try:
            size=int(self.headers.get('Content-Length',0))
            if size>2000000:raise ValueError('La imagen debe pesar menos de 1 MB.')
            data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict):raise ValueError('La solicitud debe ser un objeto JSON.')
            with connect() as c:
                if self.path in ['/api/register','/api/login']:
                    email=str(data.get('email','')).strip().lower(); pw=str(data.get('password',''))
                    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):raise ValueError('Ingresa un correo válido.')
                    if self.path=='/api/register':
                        name=str(data.get('name','')).strip()
                        if len(name)<2 or len(pw)<8:raise ValueError('Ingresa tu nombre y una contraseña de al menos 8 caracteres.')
                        try:c.execute('INSERT INTO users(name,email,password) VALUES(?,?,?)',(name[:120],email,password(pw)))
                        except sqlite3.IntegrityError:raise ValueError('Este correo ya tiene una cuenta.')
                    u=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
                    if not u or not hmac.compare_digest(u['password'],password(pw,u['password'].split(':')[0])):return self.reply({'error':'Correo o contraseña incorrectos.'},401)
                    token=secrets.token_urlsafe(32); c.execute("INSERT INTO sessions VALUES(?,?,strftime('%s','now')+2592000)",(token,u['id']))
                    secure='; Secure' if os.getenv('COOKIE_SECURE')=='1' else ''
                    return self.reply({'id':u['id'],'name':u['name'],'email':u['email']},cookie=f'session={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=2592000{secure}')
                if self.path=='/api/logout':
                    ck=SimpleCookie(self.headers.get('Cookie',''))
                    if 'session' in ck:c.execute('DELETE FROM sessions WHERE token=?',(ck['session'].value,))
                    return self.reply({'ok':True},cookie='session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0')
                if self.path=='/api/listings':
                    u=self.user(c)
                    if not u:return self.reply({'error':'Inicia sesión para publicar.'},401)
                    fields=['title','category','description','location','image','phone','type']; v={k:str(data.get(k,'')).strip() for k in fields}
                    if not all(v[k] for k in ['title','description','location','image']):raise ValueError('Completa los campos obligatorios.')
                    if v['category'] not in ['Uniformes y EPP','Equipamiento de seguridad','Profesionales de vigilancia','Capacitación y formación']:raise ValueError('Selecciona una categoría válida.')
                    if v['type'] not in ['Producto','Servicio']:raise ValueError('Selecciona Producto o Servicio como tipo de publicación.')
                    if not (v['image'].startswith('https://') or re.match(r'^data:image/(jpeg|png|webp);base64,',v['image'])):raise ValueError('Usa una imagen JPG, PNG, WebP o una URL HTTPS.')
                    if v['phone'] and not re.fullmatch(r'\d{9,15}',v['phone']):raise ValueError('Ingresa el teléfono con código de país, solo números.')
                    price=float(data['price']) if data.get('price') not in ('',None) else None
                    if price is not None and (not math.isfinite(price) or price<0 or price>1e9):raise ValueError('Precio no válido.')
                    c.execute('INSERT INTO listings(user_id,title,category,description,location,image,phone,price,type) VALUES(?,?,?,?,?,?,?,?,?)',(u['id'],v['title'][:160],v['category'],v['description'][:5000],v['location'][:100],v['image'],v['phone'],price,v['type']))
                    return self.reply({'ok':True},201)
                return self.reply({'error':'No encontrado'},404)
        except (ValueError,TypeError) as e:return self.reply({'error':str(e)},400)
if __name__=='__main__':
    print('VigiMarket en puerto '+os.getenv('PORT','3000'),flush=True)
    ThreadingHTTPServer(('0.0.0.0',int(os.getenv('PORT','3000'))),Handler).serve_forever()
