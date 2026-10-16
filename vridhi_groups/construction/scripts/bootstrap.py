"""Cross-platform local startup; needs Python and a manually installed PostgreSQL."""

import argparse
import contextlib
import getpass
import hashlib
import json
import logging
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen
import webbrowser
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / ".run"
TOOLS = ROOT / ".tools"
BACKEND = ROOT / "apps" / "backend"
FRONTEND = ROOT / "apps" / "frontend"
LOG = logging.getLogger("bootstrap")


class StartupError(Exception):
    pass


def announce(message):
    print(message, flush=True)
    LOG.info(message)


def digest(paths):
    result = hashlib.sha256()
    for path in paths:
        result.update(path.name.encode())
        result.update(path.read_bytes())
    return result.hexdigest()


def read_json(path):
    try:
        saved = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise StartupError(f"Cannot read {path.name}: {error}") from error
    if not isinstance(saved, dict):
        raise StartupError(f"Invalid startup marker {path}. Move this marker aside and retry.")
    return saved


def run(command, cwd=ROOT, env=None):
    announce(f"Running {Path(str(command[0])).name} {command[1] if len(command) > 1 else ''} ...")
    completed = subprocess.run(command, cwd=cwd, env=env, check=False)
    if completed.returncode:
        raise StartupError(
            f"Command failed (exit {completed.returncode}). Review the output above. "
            "For downloads, check internet access, proxy/certificates and package registry access. "
            "Do not disable TLS verification."
        )


def supported_platform():
    system = platform.system()
    machine = platform.machine().lower()
    arch = {"arm64": "arm64", "aarch64": "arm64", "amd64": "x64", "x86_64": "x64"}.get(machine)
    if system not in {"Darwin", "Windows"} or arch is None:
        raise StartupError("Supported platforms: macOS or Windows, with x64 or ARM64 Python/processor.")
    return ("darwin" if system == "Darwin" else "win"), arch


def compatible_node(executable):
    try:
        version = subprocess.check_output([str(executable), "--version"], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return False
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", version)
    return bool(match and (int(match[1]) == 24 or int(match[1]) == 22 and int(match[2]) >= 12))


def npm_cli(node):
    candidates = [
        node.parent / "node_modules/npm/bin/npm-cli.js",
        node.parent.parent / "lib/node_modules/npm/bin/npm-cli.js",
    ]
    existing = shutil.which("npm")
    if existing:
        candidates.append(Path(existing).resolve())
    for candidate in candidates:
        if candidate.is_file() and candidate.name == "npm-cli.js":
            return candidate
    return None


def fetch(url, destination):
    try:
        with urlopen(url, timeout=120) as source, destination.open("wb") as target:
            shutil.copyfileobj(source, target)
    except (OSError, URLError) as error:
        raise StartupError(
            f"Download from nodejs.org failed: {type(error).__name__}. "
            "Check network access and trusted certificates; or install Node.js 24 LTS manually."
        ) from error


def extract_node(archive, target):
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                name = member.filename.replace("\\", "/")
                if name.startswith("/") or ".." in Path(name).parts or ":" in name:
                    raise StartupError("Unsafe path in Node.js ZIP archive.")
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise StartupError("Unexpected symlink in Node.js ZIP archive.")
            source.extractall(target)
    else:
        with tarfile.open(archive) as source:
            source.extractall(target, filter="data")


def ensure_node():
    system, arch = supported_platform()
    existing = shutil.which("node")
    if existing and compatible_node(existing) and npm_cli(Path(existing)):
        announce("Using installed compatible Node.js.")
        return Path(existing), npm_cli(Path(existing))
    marker = TOOLS / "node.json"
    if marker.exists():
        saved = read_json(marker)
        executable = saved.get("executable")
        if not isinstance(executable, str) or not executable or Path(executable).is_absolute() or ".." in Path(executable).parts:
            raise StartupError("Invalid .tools/node.json executable. Move that marker aside and retry.")
        node = TOOLS / executable
        if compatible_node(node) and npm_cli(node):
            announce("Using private Node.js runtime.")
            return node, npm_cli(node)
    TOOLS.mkdir(exist_ok=True)
    announce("Preparing private Node.js 24 LTS from nodejs.org (first run only)...")
    with tempfile.TemporaryDirectory(prefix="node-download-", dir=TOOLS) as folder:
        folder = Path(folder)
        checksums = folder / "SHASUMS256.txt"
        base = "https://nodejs.org/dist/latest-v24.x/"
        fetch(base + checksums.name, checksums)
        suffix = f"-{system}-{arch}.{'zip' if system == 'win' else 'tar.gz'}"
        matches = []
        for line in checksums.read_text().splitlines():
            parts = line.split()
            if len(parts) == 2 and re.fullmatch(r"[a-f0-9]{64}", parts[0]):
                filename = parts[1].lstrip("*")
                if re.fullmatch(r"node-v24\.\d+\.\d+" + re.escape(suffix), filename):
                    matches.append((parts[0], filename))
        if len(matches) != 1:
            raise StartupError("Official Node.js checksums did not contain the expected platform archive.")
        expected, filename = matches[0]
        archive = folder / filename
        fetch(base + filename, archive)
        with archive.open("rb") as source:
            actual = hashlib.file_digest(source, "sha256").hexdigest()
        if actual != expected:
            raise StartupError("Node.js checksum mismatch. Download rejected; retry on a trusted connection.")
        staging = folder / "unpacked"
        staging.mkdir()
        extract_node(archive, staging)
        name = filename.removesuffix(".zip").removesuffix(".tar.gz")
        unpacked = staging / name
        node = unpacked / ("node.exe" if system == "win" else "bin/node")
        if not compatible_node(node) or not npm_cli(node):
            raise StartupError("Downloaded Node.js cannot run on this OS. Install a compatible Node.js manually.")
        destination = TOOLS / name
        if destination.exists():
            raise StartupError(f"An incomplete runtime exists at {destination}. Move it aside and retry.")
        shutil.move(str(unpacked), destination)
        node = destination / node.relative_to(unpacked)
        marker.write_text(json.dumps({"executable": str(node.relative_to(TOOLS))}))
        return node, npm_cli(node)


def ensure_backend():
    venv = BACKEND / ".venv"
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        announce("Creating isolated backend Python environment...")
        run([sys.executable, "-m", "venv", str(venv)])
    probe = subprocess.run([str(python), "-c", "import sys; sys.exit(not ((3,12)<=sys.version_info[:2]<(3,15)))"], check=False)
    if probe.returncode:
        raise StartupError("Backend .venv is incompatible. Move only apps/backend/.venv aside and relaunch.")
    expected = digest([BACKEND / "requirements-runtime.txt"]) + subprocess.check_output(
        [str(python), "-c", "import sys; print(sys.version)"], text=True).strip()
    marker = venv / ".vridhi-requirements"
    imports = "import fastapi,uvicorn,alembic,sqlalchemy,asyncpg,argon2,multipart,pydantic,pydantic_settings,email_validator,itsdangerous,dotenv"
    installed = subprocess.run([str(python), "-c", imports], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not marker.exists() or marker.read_text() != expected or installed.returncode:
        announce("Installing backend runtime dependencies (test packages excluded)...")
        run([str(python), "-m", "ensurepip", "--upgrade"])
        run([str(python), "-m", "pip", "install", "--upgrade", "pip"])
        run([str(python), "-m", "pip", "install", "-r", "requirements-runtime.txt"], cwd=BACKEND)
        run([str(python), "-m", "pip", "check"])
        marker.write_text(expected)
    return python


def prompt_value(label, default):
    return input(f"{label} [{default}]: ").strip() or default


def ensure_config():
    if (ROOT / ".env").exists():
        announce("Preserving existing .env configuration.")
        return
    announce("First-run PostgreSQL setup. Install/start PostgreSQL manually before continuing.")
    host = prompt_value("Database host", "127.0.0.1")
    port = prompt_value("Database port", "5432")
    if not port.isdigit() or not 1 <= int(port) <= 65535:
        raise StartupError("Database port must be between 1 and 65535.")
    user = prompt_value("Database username", "postgres" if os.name == "nt" else getpass.getuser())
    password = getpass.getpass("Database password (hidden; leave empty for local trust authentication): ")
    database = prompt_value("Application database", "vridhi_dev")
    if any("\n" in value or "\r" in value for value in (host, user, password, database)):
        raise StartupError("Database fields must be single-line values.")
    if not re.fullmatch(r"[a-zA-Z0-9.:\[\]_-]+", host):
        raise StartupError("Enter a hostname or IP address, without a URL, spaces or quotes.")
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]{0,62}", database):
        raise StartupError("For first-run setup, use a database name of at most 63 ASCII letters, digits or underscores, starting with a letter or underscore.")
    host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    credentials = quote(user, safe="") + (":" + quote(password, safe="") if password else "")
    url = f"postgresql+asyncpg://{credentials}@{host}:{port}/{quote(database, safe='')}"
    values = {
        "DATABASE_MODE": "local", "DATABASE_URL": url, "SESSION_SECRET": secrets.token_hex(32),
        "UPLOAD_DIRECTORY": "data/uploads", "COOKIE_SECURE": "false",
    }
    with (ROOT / ".env").open("x", encoding="utf-8") as output:
        os.chmod(ROOT / ".env", 0o600)
        for key, value in values.items():
            # Single quotes preserve URL characters and dollar signs for dotenv.
            output.write(f"{key}='{value}'\n")
    announce("Created private .env. Credentials are not printed or added to startup logs.")


def ensure_frontend(node, npm, env):
    marker = FRONTEND / "node_modules/.vridhi-dependencies"
    expected = digest([FRONTEND / "package.json", FRONTEND / "package-lock.json"])
    expected += subprocess.check_output(
        [str(node), "-p", "process.version + ':' + process.platform + ':' + process.arch"],
        text=True,
    ).strip()
    binaries = [
        FRONTEND / "node_modules/vite/bin/vite.js",
        FRONTEND / "node_modules/typescript/bin/tsc",
    ]
    if not marker.exists() or marker.read_text() != expected or not all(p.exists() for p in binaries):
        announce("Installing locked frontend dependencies with npm ci...")
        run([str(node), str(npm), "ci", "--include=dev", "--no-audit", "--no-fund"], cwd=FRONTEND, env=env)
        marker.write_text(expected)


def listening(port):
    with socket.socket() as connection:
        connection.settimeout(.5)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def healthy(port, api=False):
    try:
        with urlopen(f"http://127.0.0.1:{port}/" + ("api/v1/ready" if api else ""), timeout=2) as response:
            body = response.read().decode()
            if api:
                result = json.loads(body)
                return isinstance(result, dict) and result.get("status") == "ready"
            return "Vridhi Constructions" in body
    except (OSError, URLError, ValueError):
        return False


def service(name, ports, command, cwd, env, fingerprint):
    marker = RUN / f"{name}.json"
    if marker.exists():
        saved = read_json(marker)
        port = saved.get("port")
        if port in ports and listening(port):
            if saved.get("root") != str(ROOT) or saved.get("fingerprint") != fingerprint:
                raise StartupError(
                    f"{name} has changed since startup. Stop the previously launched process "
                    f"(PID {saved.get('pid')}) before relaunching; no process was stopped automatically."
                )
            if healthy(port, name == "api"):
                announce(f"Reusing healthy {name} on port {port}.")
                return port
            raise StartupError(f"Tracked {name} is not ready. Review .run/{name}.log and restart it.")
    port = next((p for p in ports if not listening(p)), None)
    if port is None:
        raise StartupError(f"Required {name} port(s) {ports} are occupied by untracked services. No process was stopped.")
    command = [*command, "--host", "127.0.0.1", "--port", str(port)]
    if name != "api":
        command.append("--strictPort")
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS} if os.name == "nt" else {"start_new_session": True}
    with (RUN / f"{name}.log").open("ab") as output:
        child = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                 stdout=output, stderr=subprocess.STDOUT, **options)
    marker.write_text(json.dumps({"pid": child.pid, "port": port, "root": str(ROOT), "fingerprint": fingerprint}))
    (RUN / f"{name}.pid").write_text(str(child.pid))
    for _ in range(60):
        if child.poll() is not None:
            raise StartupError(f"{name} exited during startup. See .run/{name}.log.")
        if healthy(port, name == "api"):
            announce(f"{name} ready on port {port}.")
            return port
        time.sleep(1)
    raise StartupError(f"{name} is still not ready after 60 seconds. See .run/{name}.log (PID {child.pid}).")


@contextlib.contextmanager
def startup_lock():
    with (RUN / "startup.lock").open("a+b") as lock:
        try:
            if os.name == "nt":
                import msvcrt
                lock.seek(0)
                lock.write(b"0")
                lock.flush()
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise StartupError("Another Vridhi launcher is running. Wait for it to finish.") from error
        yield


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read-only prerequisite check; does not install, configure or start services.")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if not (3, 12) <= sys.version_info[:2] < (3, 15):
        raise StartupError("Python 3.12, 3.13 or 3.14 is required.")
    system, arch = supported_platform()
    if args.check:
        print(f"Platform: {system}-{arch}; Python: {platform.python_version()}")
        node = shutil.which("node")
        print(f"Compatible system Node.js: {bool(node and compatible_node(node) and npm_cli(Path(node)))}")
        print(f"Existing configuration: {(ROOT / '.env').exists()}")
        print("PostgreSQL must be installed and running. Its actual connection is checked during normal startup.")
        return
    RUN.mkdir(exist_ok=True)
    logging.basicConfig(filename=RUN / "startup.log", level=logging.INFO, format="%(asctime)s %(message)s")
    with startup_lock():
        node, npm = ensure_node()
        env = {**os.environ, "PATH": str(node.parent) + os.pathsep + os.environ.get("PATH", ""), "PYTHONUNBUFFERED": "1"}
        python = ensure_backend()
        ensure_config()
        db_command = [str(python), str(ROOT / "scripts/prepare_database.py")]
        result = subprocess.run(db_command, cwd=ROOT, env=env)
        if result.returncode == 3:
            if input("Application database is missing. Create it using the configured PostgreSQL account? [y/N]: ").strip().lower() not in {"y", "yes"}:
                raise StartupError("Database was not created. Ask your DBA to create it, then relaunch.")
            run([*db_command, "--create"], env=env)
        elif result.returncode:
            raise StartupError("PostgreSQL check failed. Correct .env or start your manually installed server.")
        run([str(python), "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env)
        ensure_frontend(node, npm, env)
        backend_files = sorted((BACKEND / "app").rglob("*.py"))
        api_signature = digest([BACKEND / "requirements-runtime.txt", ROOT / ".env", *backend_files])
        frontend_files = sorted(p for directory in ("src", "public") for p in (FRONTEND / directory).rglob("*") if p.is_file())
        frontend_files += sorted(p for p in FRONTEND.iterdir() if p.is_file() and p.suffix in {".html", ".ts", ".js", ".json"})
        web_signature = digest([FRONTEND / "package-lock.json", FRONTEND / "package.json", *frontend_files])
        service("api", [8000], [str(python), "-m", "uvicorn", "app.main:app"], BACKEND, env, api_signature)
        port = service("frontend", [5173, 5174], [str(node), str(FRONTEND / "node_modules/vite/bin/vite.js")], FRONTEND, env, web_signature)
        url = f"http://127.0.0.1:{port}/"
        announce(f"Vridhi is ready: {url}\nAPI docs: http://127.0.0.1:8000/docs\nInitial username on an empty database: administrator")
        announce("PostgreSQL is managed by you. App services remain running; PIDs and logs are in .run/.")
        if not args.no_browser and not webbrowser.open(url):
            announce("Browser could not open automatically. Open the URL above manually.")


if __name__ == "__main__":
    try:
        main()
    except (StartupError, OSError, EOFError, KeyboardInterrupt, tarfile.TarError, zipfile.BadZipFile, subprocess.CalledProcessError) as error:
        message = str(error) or "Startup cancelled."
        LOG.error("Startup stopped: %s", message)
        print(f"\nVridhi startup stopped: {message}\nSee README.md and .run/startup.log.", file=sys.stderr)
        sys.exit(1)
