import json
import os
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath


REQUIRED = {"pyproject.toml", "requirements.txt", "install.sh", "fitsearch/main.py"}
COPY_ITEMS = ("fitsearch", "pyproject.toml", "requirements.txt", "README.md",
              "fitsearch.service.example", "install.sh")


def version_tuple(value: str) -> tuple[int, ...]:
    match = re.fullmatch(r"\d+(?:\.\d+){1,3}", value.strip())
    if not match:
        raise ValueError("Numéro de version invalide")
    return tuple(int(part) for part in value.split("."))


def project_version(project_file: Path) -> str:
    content = project_file.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*["\']([^"\']+)', content, re.MULTILINE)
    if not match:
        raise ValueError("Version FitSearch introuvable")
    version_tuple(match.group(1))
    return match.group(1)


def inspect_archive(archive: Path) -> dict:
    if not zipfile.is_zipfile(archive):
        raise ValueError("Le fichier sélectionné n’est pas une archive ZIP valide")
    with zipfile.ZipFile(archive) as bundle:
        files = [item for item in bundle.infolist() if not item.is_dir()]
        if len(files) > 500 or sum(item.file_size for item in files) > 30_000_000:
            raise ValueError("L’archive est trop volumineuse")
        names = set()
        for item in files:
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Chemin dangereux détecté dans l’archive")
            mode = item.external_attr >> 16
            if mode and stat.S_ISLNK(mode):
                raise ValueError("Les liens symboliques ne sont pas autorisés")
            names.add(item.filename.rstrip("/"))
        roots = []
        for name in names:
            if name.endswith("/pyproject.toml") or name == "pyproject.toml":
                root = name.removesuffix("pyproject.toml").rstrip("/")
                prefix = f"{root}/" if root else ""
                if all(f"{prefix}{required}" in names for required in REQUIRED):
                    roots.append(root)
        if len(roots) != 1:
            raise ValueError("Structure FitSearch absente ou ambiguë")
        root = roots[0]
        prefix = f"{root}/" if root else ""
        project = bundle.read(f"{prefix}pyproject.toml").decode("utf-8")
        if not re.search(r'^name\s*=\s*["\']fitsearch["\']', project, re.MULTILINE | re.IGNORECASE):
            raise ValueError("Cette archive ne contient pas FitSearch")
        match = re.search(r'^version\s*=\s*["\']([^"\']+)', project, re.MULTILINE)
        if not match:
            raise ValueError("Version FitSearch introuvable")
        version = match.group(1)
        version_tuple(version)
        return {"root": root, "version": version, "files": len(files)}


def extract_project(archive: Path, destination: Path, root: str):
    prefix = f"{root}/" if root else ""
    with zipfile.ZipFile(archive) as bundle:
        for item in bundle.infolist():
            if item.is_dir() or not item.filename.startswith(prefix):
                continue
            relative = PurePosixPath(item.filename[len(prefix):])
            if not relative.parts:
                continue
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(item) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)


def write_status(data_dir: Path, phase: str, message: str, **extra):
    target = data_dir / "update-status.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps({"phase": phase, "message": message,
                                     "updated_at": datetime.now().isoformat(), **extra},
                                    ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, target)


def copy_application(source: Path, destination: Path):
    for name in COPY_ITEMS:
        item = source / name
        if not item.exists():
            continue
        target = destination / name
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)


def perform_update(archive: Path, data_dir: Path):
    app_dir = data_dir / "app"
    pip = app_dir / ".venv/bin/pip"
    if not app_dir.is_dir() or not pip.is_file():
        raise ValueError("Installation locale FitSearch introuvable")
    info = inspect_archive(archive)
    if version_tuple(info["version"]) < version_tuple(project_version(app_dir / "pyproject.toml")):
        raise ValueError("Cette archive contient une version plus ancienne")
    backups = data_dir / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    database = data_dir / "fitsearch.db"
    if database.exists():
        backup_database = backups / f"fitsearch-avant-{info['version']}-{stamp}.db"
        with sqlite3.connect(database) as source_db, sqlite3.connect(backup_database) as backup_db:
            source_db.backup(backup_db)
    old_sources = Path(tempfile.mkdtemp(prefix="fitsearch-rollback-"))
    extracted = Path(tempfile.mkdtemp(prefix="fitsearch-update-"))
    try:
        copy_application(app_dir, old_sources)
        extract_project(archive, extracted, info["root"])
        write_status(data_dir, "installing", f"Installation de FitSearch {info['version']}…",
                     version=info["version"])
        copy_application(extracted, app_dir)
        subprocess.run([str(pip), "install", "--disable-pip-version-check", "--upgrade", str(app_dir)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=300)
        archives = sorted(backups.glob("fitsearch-avant-*.db"), key=lambda path: path.stat().st_mtime, reverse=True)
        for old in archives[5:]:
            old.unlink(missing_ok=True)
        service_active = subprocess.run(["systemctl", "--user", "is-active", "--quiet", "fitsearch"],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        message = (f"FitSearch {info['version']} est installé. Redémarrage en cours…" if service_active
                   else f"FitSearch {info['version']} est installé. Redémarrez le lancement manuel.")
        write_status(data_dir, "complete", message, version=info["version"],
                     restart_required=not service_active)
        if service_active:
            time.sleep(1.5)
            subprocess.Popen(["systemctl", "--user", "restart", "fitsearch"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except Exception as exc:
        try:
            copy_application(old_sources, app_dir)
            subprocess.run([str(pip), "install", "--disable-pip-version-check", "--no-deps",
                            "--force-reinstall", str(app_dir)], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        finally:
            write_status(data_dir, "error", f"Mise à jour annulée : {str(exc)[:180]}")
        raise
    finally:
        shutil.rmtree(old_sources, ignore_errors=True)
        shutil.rmtree(extracted, ignore_errors=True)
        archive.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        perform_update(Path(sys.argv[1]), Path(sys.argv[2]))
    except Exception:
        sys.exit(1)
