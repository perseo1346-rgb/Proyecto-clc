import unittest, tempfile, shutil, subprocess, socket, time, json, urllib.request, urllib.error, http.cookiejar
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class MarketplaceTest(unittest.TestCase):
    def test_account_listing_and_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(ROOT/'server.py',tmp)
            shutil.copytree(ROOT/'static',Path(tmp)/'static')
            with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
            import os
            def start():
                p=subprocess.Popen(['python',str(Path(tmp)/'server.py')],env={**os.environ,'PORT':str(port),'DATA_DIR':''},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                for _ in range(100):
                    try:urllib.request.urlopen(f'http://127.0.0.1:{port}/api/me');return p
                    except OSError:time.sleep(.03)
                p.terminate();raise RuntimeError('Server not ready')
            p=start();jar=http.cookiejar.CookieJar();client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar));base=f'http://127.0.0.1:{port}'
            def req(path,data=None,opener=client):
                r=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
                with opener.open(r) as result:return json.load(result)
            try:
                self.assertIn('VigiMarket',urllib.request.urlopen(base).read().decode())
                self.assertIsNone(req('/api/me'))
                with self.assertRaises(urllib.error.HTTPError) as e:req('/api/listings',{})
                self.assertEqual(e.exception.code,401)
                account={'name':'Usuario de prueba','email':'test@example.com','password':'secure-password-123'}
                u=req('/api/register',account);self.assertEqual(u['name'],account['name'])
                self.assertTrue(next(iter(jar)).has_nonstandard_attr('HttpOnly'))
                self.assertEqual(req('/api/me')['email'],account['email'])
                with self.assertRaises(urllib.error.HTTPError):req('/api/register',account)
                listing={'title':'Chaleco de prueba','category':'Uniformes y EPP','description':'Prueba de publicación persistente','location':'Lima','image':'https://example.com/image.jpg','phone':'51999999999','price':'120','type':'Producto'}
                self.assertTrue(req('/api/listings',listing)['ok'])
                rows=req('/api/listings');self.assertEqual(len(rows),1);self.assertEqual(rows[0]['user_id'],u['id'])
                req('/api/logout',{});self.assertIsNone(req('/api/me'))
                with self.assertRaises(urllib.error.HTTPError):req('/api/login',{**account,'password':'incorrect'})
                req('/api/login',account)
                p.terminate();p.wait();p=start()
                self.assertEqual(req('/api/me')['email'],account['email'])
                self.assertEqual(req('/api/listings')[0]['title'],listing['title'])
                import sqlite3
                with sqlite3.connect(Path(tmp)/'data/vigimarket.db') as db:
                    stored=db.execute('SELECT password FROM users').fetchone()[0]
                    self.assertNotEqual(stored,account['password']);self.assertIn(':',stored)
            finally:p.terminate();p.wait()
if __name__=='__main__':unittest.main()
