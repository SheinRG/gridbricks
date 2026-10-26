"""Fail if Vercel deps (pyproject.toml) drift from Docker deps (backend/requirements.txt)."""

import sys
import tomllib
from pathlib import Path

root = Path(__file__).resolve().parent.parent
vercel = set(tomllib.loads((root / "pyproject.toml").read_text())["project"]["dependencies"])
docker = {
    line.strip()
    for line in (root / "backend" / "requirements.txt").read_text().splitlines()
    if line.strip() and not line.startswith("#")
}
if vercel != docker:
    print(f"Only in pyproject.toml: {sorted(vercel - docker)}")
    print(f"Only in backend/requirements.txt: {sorted(docker - vercel)}")
    sys.exit(1)
print("Dependencies in sync.")
