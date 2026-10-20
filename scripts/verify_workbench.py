"""Drive an isolated real Gateway; retain evidence after stopping its process."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]


def unused_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def is_listening(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.2)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def stop_owned_process(process, port: int) -> None:
    if process is not None and process.poll() is None and os.name == "nt":
        # A Windows venv python.exe redirects to a child interpreter. Stopping
        # only Popen's PID can leave that server listening after wait() returns.
        stopped = subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if stopped.returncode and process.poll() is None:
            raise RuntimeError("Could not stop the owned Gateway process tree")
    elif process is not None and process.poll() is None:
        process.terminate()
    if process is not None:
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    deadline = time.monotonic() + 5
    while is_listening(port):
        if time.monotonic() > deadline:
            raise TimeoutError("Owned Gateway listener did not stop")
        time.sleep(0.02)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument(
        "--feature", choices=["baseline", "evidence"], default="baseline"
    )
    args = parser.parse_args()
    output = args.evidence.resolve()
    output.mkdir(parents=True, exist_ok=False)
    state = output / "state"
    state.mkdir()
    config = {
        "config_version": 61,
        "models": [],
        "sandbox": {
            "use": "deerflow.sandbox.local:LocalSandboxProvider",
            "allow_host_bash": False,
        },
        "database": {"backend": "sqlite", "sqlite_dir": str(state / "data")},
        "memory": {"enabled": False},
        "plugins": [
            {
                "name": "evidence-workbench",
                "use": "evidence_workbench:install",
                "required": True,
                "config": {
                    "enabled": True,
                    "storage_path": str(state / "evidence.sqlite"),
                },
            }
        ]
        if args.feature == "evidence"
        else [],
    }
    config_path = state / "config.yaml"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    env_file = state / ".env"
    env_file.write_text("", encoding="utf-8")
    port = unused_port()
    base = f"http://127.0.0.1:{port}"
    environment = os.environ.copy()
    environment.update(
        DEER_FLOW_CONFIG_PATH=str(config_path),
        DEER_FLOW_PROJECT_ROOT=str(ROOT),
        DEER_FLOW_HOME=str(state / "home"),
        DEER_FLOW_ENV_FILE=str(env_file),
        PYTHONUTF8="1",
        GATEWAY_CORS_ORIGINS=base,
    )
    events: list[dict] = []
    result = {"feature": args.feature, "base_url": base, "passed": False}
    log_path = output / "gateway.log"
    process = None
    try:
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.gateway.app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                cwd=ROOT / "backend",
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            with httpx.Client(
                base_url=base,
                timeout=20,
                headers={"Origin": base},
            ) as client:
                deadline = time.monotonic() + 50
                while True:
                    if process.poll() is not None:
                        raise RuntimeError(
                            f"Gateway exited before readiness: {process.returncode}. See gateway.log"
                        )
                    try:
                        health = client.get("/health")
                        if (
                            health.status_code == 200
                            and health.json().get("status") == "healthy"
                        ):
                            break
                    except httpx.ConnectError:
                        pass
                    if time.monotonic() >= deadline:
                        raise TimeoutError(
                            "Gateway readiness deadline exceeded. See gateway.log"
                        )
                    time.sleep(0.2)
                events.append(
                    {"phase": "launch", "pid": process.pid, "health": health.json()}
                )

                def request(method, path, payload=None, expected=None):
                    csrf = client.cookies.get("csrf_token")
                    headers = {"X-CSRF-Token": csrf} if csrf else {}
                    response = client.request(
                        method, path, json=payload, headers=headers
                    )
                    body = response.json()
                    events.append(
                        {
                            "phase": "drive",
                            "method": method,
                            "path": path,
                            "status": response.status_code,
                            "body": body,
                        }
                    )
                    assert (
                        (200 <= response.status_code < 300)
                        if expected is None
                        else response.status_code == expected
                    ), f"{method} {path}: {response.status_code} {body}"
                    return body

                setup = request("GET", "/api/v1/auth/setup-status")
                assert setup["needs_setup"] is True, setup
                account = request(
                    "POST",
                    "/api/v1/auth/initialize",
                    {
                        "email": "verification@example.com",
                        "password": "Verify9!" + secrets.token_hex(16),
                        "remember_me": False,
                    },
                )
                me = request("GET", "/api/v1/auth/me")
                assert me["id"] == account["id"], me
                events.append(
                    {
                        "phase": "doctor",
                        "authenticated_owner": me["id"],
                        "owned_process_alive": process.poll() is None,
                    }
                )
                thread = request(
                    "POST",
                    "/api/threads",
                    {"metadata": {"title": "Verification baseline"}},
                )
                restored = request("GET", f"/api/threads/{thread['thread_id']}")
                assert restored["thread_id"] == thread["thread_id"], restored
                assert list((state / "data").glob("*.db")), (
                    "No persistent application database was created"
                )
                if args.feature == "evidence":
                    prefix = "/api/plugins/evidence.workbench/actions/"

                    def action(name, payload, expected=None):
                        return request("POST", prefix + name, payload, expected)

                    plugins = request("GET", "/api/plugins")
                    plugin = next(
                        item
                        for item in plugins
                        if item["namespace"] == "evidence.workbench"
                    )
                    assert plugin["settings"]["enabled"] is True
                    asset = client.get(plugin["entry"])
                    assert asset.status_code == 200 and "mountWorkbench" in asset.text
                    d = action(
                        "create",
                        {
                            "title": "WAL durability",
                            "question": "Does WAL mode always guarantee durability?",
                        },
                    )
                    text = "The WAL is very fast since writing content to the WAL file does not involve syncing the content to disk.\nTransactions are durable if the synchronous pragma is FULL."
                    d = action(
                        "add_source",
                        {
                            "id": d["id"],
                            "revision": d["revision"],
                            "title": "Controlled verification fixture",
                            "url": "",
                            "text": text,
                        },
                    )
                    sid = d["sources"][0]["id"]
                    payload = {
                        "id": d["id"],
                        "revision": d["revision"],
                        "text": "WAL always guarantees durability",
                        "evidence": [
                            {
                                "source_id": sid,
                                "quote": "fabricated quotation",
                                "relation": "supports",
                            }
                        ],
                    }
                    action("add_claim", payload, 422)
                    assert action("get", {"id": d["id"]}) == d
                    payload["evidence"] = [
                        {
                            "source_id": sid,
                            "quote": "Transactions are durable if the synchronous pragma is FULL.",
                            "relation": "supports",
                        },
                        {
                            "source_id": sid,
                            "quote": "does not involve syncing the content to disk",
                            "relation": "contradicts",
                        },
                    ]
                    d = action("add_claim", payload)
                    assert d["claims"][0]["status"] == "disputed"
                    action("review", {"id": d["id"], "revision": 1}, 422)
                    d = action("review", {"id": d["id"], "revision": d["revision"]})
                    assert d["status"] == "reviewed"
                    report = action("export", {"id": d["id"]})
                    assert (
                        "reviewed" in report["markdown"]
                        and "disputed" in report["markdown"]
                    )
                    snapshot = action("get_source", {"id": d["id"], "source_id": sid})
                    assert snapshot["text"] == text
                    assert (
                        snapshot["sha256"] == hashlib.sha256(text.encode()).hexdigest()
                    )
                    prepared = action(
                        "prepare_research", {"id": d["id"], "revision": d["revision"]}
                    )
                    assert (
                        request("GET", f"/api/threads/{prepared['thread_id']}")[
                            "thread_id"
                        ]
                        == prepared["thread_id"]
                    )
                    d = action("get", {"id": d["id"]})
                    assert (
                        d["thread_id"] == prepared["thread_id"]
                        and d["status"] == "open"
                    )
                    # Recreate the store object to prove disk persistence independently of process caches.
                    from evidence_workbench.store import Workbench

                    assert (
                        Workbench(str(state / "evidence.sqlite")).apply(
                            "get", {"id": d["id"]}, me["id"]
                        )
                        == d
                    )
                    assert Workbench(str(state / "evidence.sqlite")).apply(
                        "list", {}, "unrelated-owner"
                    ) == {"items": []}
                    # Restart the real Gateway and read the same owned data through HTTP.
                    command = process.args
                    stop_owned_process(process, port)
                    assert not is_listening(port), (
                        "Owned Gateway still listens after shutdown"
                    )
                    process = subprocess.Popen(
                        command,
                        cwd=ROOT / "backend",
                        env=environment,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NO_WINDOW
                        if os.name == "nt"
                        else 0,
                    )
                    deadline = time.monotonic() + 50
                    while True:
                        if process.poll() is not None:
                            raise RuntimeError(
                                "Restarted Gateway exited before readiness"
                            )
                        try:
                            health = client.get("/health")
                            if health.status_code == 200:
                                break
                        except httpx.ConnectError:
                            pass
                        if time.monotonic() > deadline:
                            raise TimeoutError("Restart readiness deadline exceeded")
                        time.sleep(0.2)
                    assert action("get", {"id": d["id"]}) == d
                    events.append(
                        {
                            "phase": "restart_persistence",
                            "pid": process.pid,
                            "investigation_id": d["id"],
                        }
                    )
                    # A second real session cannot read another user's investigation or source.
                    other = httpx.Client(
                        base_url=base, timeout=20, headers={"Origin": base}
                    )
                    try:
                        registration = other.post(
                            "/api/v1/auth/register",
                            json={
                                "email": "other@example.com",
                                "password": "Other9!" + secrets.token_hex(16),
                            },
                        )
                        assert registration.status_code in (200, 201), registration.text
                        csrf = other.cookies.get("csrf_token")
                        denied = other.post(
                            prefix + "get",
                            json={"id": d["id"]},
                            headers={"X-CSRF-Token": csrf} if csrf else {},
                        )
                        events.append(
                            {
                                "phase": "owner_isolation",
                                "status": denied.status_code,
                                "body": denied.json(),
                            }
                        )
                        assert denied.status_code == 422
                        denied_source = other.post(
                            prefix + "get_source",
                            json={"id": d["id"], "source_id": sid},
                            headers={"X-CSRF-Token": csrf} if csrf else {},
                        )
                        assert denied_source.status_code == 422
                        events.append(
                            {
                                "phase": "source_owner_isolation",
                                "status": denied_source.status_code,
                            }
                        )
                    finally:
                        other.close()
                result["passed"] = True
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        try:
            stop_owned_process(process, port)
        except Exception as error:
            result["cleanup_error"] = f"{type(error).__name__}: {error}"
        result["cleanup"] = {
            "process_stopped": process is None or process.poll() is not None,
            "listener_stopped": not is_listening(port),
        }
        (output / "actions.json").write_text(
            json.dumps(events, indent=2), encoding="utf-8"
        )
        (output / "result.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
    assert (output / "result.json").is_file() and log_path.is_file()
    print(json.dumps(result))
    return (
        0
        if result["passed"]
        and all(result["cleanup"].values())
        and "cleanup_error" not in result
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
