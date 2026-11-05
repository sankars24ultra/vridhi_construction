#!/bin/zsh
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT" || exit 1

PYTHON=""
for candidate in "$ROOT/apps/backend/.venv/bin/python" python3 python3.14 python3.13 python3.12; do
  if command -v "$candidate" >/dev/null 2>&1 &&
     "$candidate" -c 'import fastapi,uvicorn,alembic,sqlalchemy,asyncpg,argon2,multipart,pydantic,pydantic_settings,email_validator,itsdangerous,dotenv' >/dev/null 2>&1; then
    PYTHON="$candidate"
    break
  fi
done

if [[ -z "$PYTHON" ]]; then
  print -u2 "No Python environment with the backend runtime packages was found."
  print -u2 "Install apps/backend/requirements-runtime.txt or use the normal launcher."
  exit 1
fi

"$PYTHON" - "$@" <<'PY'
import argparse
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import webbrowser

sys.path.insert(0, str(Path.cwd() / "scripts"))
import bootstrap as boot

parser = argparse.ArgumentParser(description="Temporary macOS startup using installed packages only; no downloads.")
parser.add_argument("--check", action="store_true")
parser.add_argument("--no-browser", action="store_true")
args = parser.parse_args()

try:
    if sys.platform != "darwin":
        raise boot.StartupError("This temporary launcher is for macOS only.")
    executable = shutil.which("node")
    if not executable:
        raise boot.StartupError("Node.js is not installed/on PATH. This temporary launcher does not download it.")
    node = Path(executable)
    version = subprocess.check_output([str(node), "--version"], text=True).strip()
    vite = boot.FRONTEND / "node_modules/vite/bin/vite.js"
    if not vite.is_file():
        raise boot.StartupError("Frontend packages are missing. Run npm ci in apps/frontend first.")
    print(f"Temporary launcher: Python {sys.version.split()[0]} ({sys.executable}); Node.js {version}", flush=True)
    print("Using existing packages without downloads or dependency updates.", flush=True)
    if not boot.compatible_node(node):
        print("WARNING: this Node.js version is outside the normal launcher's supported versions; temporary local use only.", flush=True)
    if args.check:
        print(f"Existing .env: {(boot.ROOT / '.env').is_file()}")
        print("Installed dependency checks passed. Database connection is checked during normal startup.")
    else:
        boot.RUN.mkdir(exist_ok=True)
        logging.basicConfig(filename=boot.RUN / "startup.log", level=logging.INFO, format="%(asctime)s %(message)s")
        with boot.startup_lock():
            boot.ensure_config()
            env = {**os.environ, "PYTHONUNBUFFERED": "1"}
            database = [sys.executable, str(boot.ROOT / "scripts/prepare_database.py")]
            result = subprocess.run(database, cwd=boot.ROOT, env=env)
            if result.returncode == 3:
                if input("Create the missing application database using the configured account? [y/N]: ").strip().lower() not in {"y", "yes"}:
                    raise boot.StartupError("Database was not created. Ask your DBA to create it.")
                boot.run([*database, "--create"], env=env)
            elif result.returncode:
                raise boot.StartupError("Database check failed. Start PostgreSQL and check .env; no app services were started.")
            boot.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=boot.BACKEND, env=env)
            api_files = sorted((boot.BACKEND / "app").rglob("*.py"))
            api_signature = boot.digest([boot.BACKEND / "requirements-runtime.txt", boot.ROOT / ".env", *api_files])
            web_files = sorted(p for directory in ("src", "public") for p in (boot.FRONTEND / directory).rglob("*") if p.is_file())
            web_files += sorted(p for p in boot.FRONTEND.iterdir() if p.is_file() and p.suffix in {".html", ".ts", ".js", ".json"})
            web_signature = boot.digest([boot.FRONTEND / "package-lock.json", boot.FRONTEND / "package.json", *web_files])
            boot.service("api", [8000], [sys.executable, "-m", "uvicorn", "app.main:app"], boot.BACKEND, env, api_signature)
            port = boot.service("frontend", [5173, 5174], [str(node), str(vite)], boot.FRONTEND, env, web_signature)
            url = f"http://127.0.0.1:{port}/"
            boot.announce(f"Vridhi is ready: {url}\nServices remain running. Logs and PIDs are in .run/.")
            if not args.no_browser and not webbrowser.open(url):
                boot.announce("Browser could not open. Open the URL above manually.")
except (boot.StartupError, OSError, EOFError, KeyboardInterrupt, subprocess.CalledProcessError) as error:
    message = str(error) or "Startup cancelled."
    boot.LOG.error("Temporary startup stopped: %s", message)
    print(f"\nTemporary startup stopped: {message}", file=sys.stderr)
    sys.exit(1)
PY
result=$?
if [[ $# == 0 ]]; then
  read -r "?Press Return to close this window..."
fi
exit "$result"
