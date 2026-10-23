"""Publish the labeled static preview to the existing GitHub Pages branch."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
def git(*args, env=None):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], env=env, text=True).strip()

if git('status', '--porcelain'):
    sys.exit('Guarda primero los cambios del proyecto en Git. El directorio debe estar limpio.')
with tempfile.TemporaryDirectory(prefix='vigimarket-preview-') as temp:
    temp = Path(temp)
    output = temp / 'site'
    subprocess.run([sys.executable, str(ROOT / 'scripts/build_preview.py'), '--output', str(output)], check=True)
    git('fetch', 'origin', 'gh-pages:refs/remotes/origin/gh-pages')
    parent = git('rev-parse', 'refs/remotes/origin/gh-pages')
    env = {**os.environ, 'GIT_INDEX_FILE': str(temp / 'index')}
    def artifact_git(*args):
        return git('--work-tree=' + str(output), *args, env=env)
    artifact_git('read-tree', '--empty')
    artifact_git('add', '--all')
    tree = artifact_git('write-tree')
    if tree == git('rev-parse', parent + '^{tree}'):
        print('La vista previa ya contiene estos cambios.')
    else:
        commit = git('commit-tree', tree, '-p', parent, '-m', 'Update VigiMarket public design preview')
        git('push', 'origin', commit + ':refs/heads/gh-pages')
        print('Vista previa enviada. Comprueba el despliegue de GitHub Pages antes de anunciarla.')
print('Sitio de vista previa: https://perseo1346-rgb.github.io/Proyecto-clc/')
