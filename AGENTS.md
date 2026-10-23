# VigiMarket development

This repository contains the VigiMarket marketplace for private security in Peru.

- Use the existing checkout. Cloud tasks are isolated; do not create a Git worktree unless requested.
- Frontend: `static/index.html`, `static/style.css`, `static/app.js`.
- Backend: `server.py`, Python 3.12 standard library, SQLite.
- Start: `python server.py` (default port 3000).
- Validate: `python -m unittest discover -s tests -v` and `node --check static/app.js`.
- Preserve the SQLite database and its backups. Never commit user data, sessions, passwords or database files.
- Example listings must stay clearly labeled, and must not display invented real providers or contacts.
- Do not simulate successful registrations, publications or contacts.
- Public deployment needs HTTPS and persistent storage. A static host alone does not provide account or publication functionality.
- The source is intended to be retained in `perseo1346-rgb/Proyecto-clc` for continued modifications.

- All example images and fonts are local in `static/assets/` and `static/fonts/`; keep font licenses.
- Use `python scripts/backup_database.py` for a consistent SQLite backup before data migrations. Keep off-host backups as well.
- Publishing requires an actual hosting account. `render.yaml` is a blueprint, not proof of a live deployment. Verify the assigned public URL before reporting publication.
