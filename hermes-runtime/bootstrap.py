"""Materialize Cloud Run secrets into Hermes' ephemeral data directory."""

from __future__ import annotations

import os
from pathlib import Path


def _write_secret(env_name: str, target: Path) -> None:
    value = os.environ.pop(env_name, "")
    if not value:
        raise RuntimeError(f"Missing required secret environment variable: {env_name}")
    target.write_text(value, encoding="utf-8")
    target.chmod(0o600)


data_dir = Path("/opt/data")
data_dir.mkdir(parents=True, exist_ok=True)
_write_secret("HERMES_CONFIG_YAML", data_dir / "config.yaml")
_write_secret("HERMES_AUTH_JSON", data_dir / "auth.json")

os.execv(
    "/opt/hermes/.venv/bin/hermes",
    ["hermes", "gateway", "run"],
)
