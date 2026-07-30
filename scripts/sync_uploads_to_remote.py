"""Sube app/static/uploads locales a un AdmiTomi remoto (Render), conservando nombres.

Uso (PowerShell):
  $env:REMOTE_URL = "https://sistema-admision-tominaga.onrender.com"
  $env:ADMIN_USER = "admin"
  $env:ADMIN_PASSWORD = "tu-password"
  python scripts/sync_uploads_to_remote.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
UPLOADS = ROOT / "app" / "static" / "uploads"


def main() -> None:
    base = os.getenv("REMOTE_URL", "").rstrip("/")
    username = os.getenv("ADMIN_USER", "admin")
    password = os.getenv("ADMIN_PASSWORD", "")
    if not base:
        raise SystemExit("Define REMOTE_URL (ej. https://tu-servicio.onrender.com)")
    if not password:
        raise SystemExit("Define ADMIN_PASSWORD del admin en Render")
    if not UPLOADS.is_dir():
        raise SystemExit(f"No existe {UPLOADS}")

    files = [p for p in UPLOADS.rglob("*") if p.is_file() and p.name != ".gitkeep"]
    if not files:
        raise SystemExit("No hay archivos en app/static/uploads para sincronizar")

    with httpx.Client(base_url=base, timeout=120.0, follow_redirects=True) as client:
        login = client.post(
            "/api/auth/login/json",
            json={"username": username, "password": password},
        )
        if login.status_code >= 400:
            raise SystemExit(f"Login falló ({login.status_code}): {login.text}")
        token = login.json().get("access_token")
        if not token:
            raise SystemExit("Login OK pero no devolvió access_token")
        headers = {"Authorization": f"Bearer {token}"}

        ok = 0
        for path in sorted(files):
            relative = path.relative_to(UPLOADS).as_posix()
            with path.open("rb") as fh:
                response = client.post(
                    "/api/admin/restore-upload",
                    params={"relative_path": relative},
                    files={"file": (path.name, fh, "application/octet-stream")},
                    headers=headers,
                )
            if response.status_code >= 400:
                print(f"[fail] {relative}: {response.status_code} {response.text}")
                continue
            print(f"[ok] {relative}")
            ok += 1

    print(f"Sincronizados {ok}/{len(files)} archivos.")


if __name__ == "__main__":
    main()
