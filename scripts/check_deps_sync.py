"""Fail if Vercel deps (backend/pyproject.toml) drift from Docker deps (requirements.txt)."""

import sys
import tomllib
from pathlib import Path

backend = Path(__file__).resolve().parent.parent / "backend"
vercel = set(tomllib.loads((backend / "pyproject.toml").read_text())["project"]["dependencies"])
docker = {
    line.strip()
    for line in (backend / "requirements.txt").read_text().splitlines()
    if line.strip() and not line.startswith("#")
}
if vercel != docker:
    print(f"Only in backend/pyproject.toml: {sorted(vercel - docker)}")
    print(f"Only in backend/requirements.txt: {sorted(docker - vercel)}")
    sys.exit(1)
print("Dependencies in sync.")
