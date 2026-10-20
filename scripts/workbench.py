"""Configure and run the local workbench without a model or external service."""

import argparse
import os
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "gateway", "web"])
    args = parser.parse_args()
    config_path = ROOT / "config.yaml"
    if args.command == "init":
        config = (
            yaml.safe_load(config_path.read_text(encoding="utf-8"))
            if config_path.exists()
            else {
                "config_version": 61,
                "models": [],
                "sandbox": {
                    "use": "deerflow.sandbox.local:LocalSandboxProvider",
                    "allow_host_bash": False,
                },
                "database": {
                    "backend": "sqlite",
                    "sqlite_dir": str(ROOT / ".deer-flow/data"),
                },
                "memory": {"enabled": False},
            }
        )
        if not isinstance(config, dict):
            raise ValueError("Existing config must be a mapping")
        config.setdefault("config_version", 61)
        database = config.get("database", {})
        if (
            database.get("backend") == "sqlite"
            and not Path(database.get("sqlite_dir", ".deer-flow/data")).is_absolute()
        ):
            database["sqlite_dir"] = str(
                ROOT / database.get("sqlite_dir", ".deer-flow/data")
            )
        plugins = config.setdefault("plugins", [])
        if not any(
            plugin.get("use") == "evidence_workbench:install" for plugin in plugins
        ):
            plugins.append(
                {
                    "name": "evidence-workbench",
                    "use": "evidence_workbench:install",
                    "required": True,
                    "config": {
                        "enabled": True,
                        "storage_path": str(
                            ROOT / ".deer-flow/evidence/workbench.sqlite"
                        ),
                    },
                }
            )
        config_path.write_text(
            yaml.safe_dump(config, sort_keys=False), encoding="utf-8"
        )
        print(
            f"Configured {config_path}. Existing model configuration preserved. No model call made."
        )
        return 0
    if not config_path.exists():
        raise SystemExit("Run scripts/workbench.py init first")
    environment = os.environ.copy()
    environment.update(
        DEER_FLOW_PROJECT_ROOT=str(ROOT),
        DEER_FLOW_CONFIG_PATH=str(config_path),
        PYTHONUTF8="1",
    )
    if args.command == "gateway":
        command = [
            sys.executable,
            "-m",
            "uvicorn",
            "app.gateway.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8420",
        ]
        cwd = ROOT / "backend"
    else:
        environment["DEER_FLOW_INTERNAL_GATEWAY_BASE_URL"] = "http://127.0.0.1:8420"
        command = ["node", "scripts/dev.mjs", "--port", "3320"]
        cwd = ROOT / "frontend"
    return subprocess.call(command, cwd=cwd, env=environment)


if __name__ == "__main__":
    raise SystemExit(main())
