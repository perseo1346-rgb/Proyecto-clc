"""Build an explicitly labeled, read-only public preview for GitHub Pages."""
import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
if args.output.exists():
    parser.error('El directorio de salida debe ser nuevo para no sobrescribir archivos.')
shutil.copytree(ROOT / 'static', args.output)
(args.output / '.nojekyll').touch()
html = (args.output / 'index.html').read_text()
html = html.replace('href="/fonts/', 'href="./fonts/').replace('href="/style.css"', 'href="./style.css"').replace('src="/app.js"', 'src="./app.js"')
html = html.replace('<main id="inicio">', '<div class="preview-notice" role="note">Vista previa navegable · Las cuentas y publicaciones estarán disponibles en la versión completa.</div><main id="inicio">')
(args.output / 'index.html').write_text(html)
css = (args.output / 'style.css').read_text().replace('url("/assets/', 'url("./assets/')
css += '\n.preview-notice{background:#fff4da;color:#173b3a;text-align:center;padding:12px 5%;font-size:12px;line-height:1.6;border-bottom:1px solid #e9dcbb}\n'
(args.output / 'style.css').write_text(css)
js = (args.output / 'app.js').read_text().replace('"/assets/', '"./assets/').replace("'/placeholder.svg'", "'./placeholder.svg'")
marker = "Promise.all([api('me'),api('listings')])"
if marker not in js:
    raise RuntimeError('Revisa el arranque del frontend antes de generar la vista previa.')
js = js.split(marker)[0]
for function in ["function auth(mode='login',next=null){", 'function publish(){', 'function profile(){']:
    if function not in js:
        raise RuntimeError('No se encontró la función esperada: ' + function)
    js = js.replace(function, function + 'return previewUnavailable();', 1)
js += '''
function previewUnavailable(){modal('<span class="eyebrow muted">VISTA PREVIA</span><h2>Conoce VigiMarket</h2><p>Puedes explorar las categorías, buscar y consultar las publicaciones de ejemplo.</p><p>El registro, el perfil y la publicación de anuncios estarán disponibles al activar la versión completa. Esta vista previa no solicita contraseñas ni guarda datos personales.</p><button class="primary" id="preview-explore">Seguir explorando</button>');document.querySelector('#preview-explore').onclick=()=>{document.querySelector('#modal').close();document.querySelector('#explorar').scrollIntoView()}}
'''
(args.output / 'app.js').write_text(js)
print(args.output)
