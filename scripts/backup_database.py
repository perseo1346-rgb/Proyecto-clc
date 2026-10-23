"""Make a consistent SQLite backup without stopping VigiMarket."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--destination', type=Path, help='Backup directory. Keep off-host copies for disaster recovery.')
args = parser.parse_args()
data = Path(os.environ.get('DATA_DIR', ROOT / 'data'))
source = data / 'vigimarket.db'
if not source.is_file():
    parser.error('No existe la base de datos de VigiMarket.')
destination = args.destination or data / 'backups'
destination.mkdir(parents=True, exist_ok=True)
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
target = destination / f'vigimarket-{stamp}.db'
try:
    with sqlite3.connect(f'{source.resolve().as_uri()}?mode=ro', uri=True) as src:
        with sqlite3.connect(target) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('La verificación del respaldo falló.')
except Exception:
    target.unlink(missing_ok=True)
    raise
os.chmod(target, 0o600)
print(f'Respaldo verificado: {target}')
