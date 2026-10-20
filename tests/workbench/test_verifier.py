import os
import subprocess
import sys
import time

import httpx

from scripts.verify_workbench import is_listening, stop_owned_process, unused_port


def test_owned_server_listener_stops_with_its_launcher():
    port = unused_port()
    process = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    try:
        with httpx.Client(trust_env=False) as client:
            deadline = time.monotonic() + 10
            while True:
                assert process.poll() is None
                try:
                    response = client.get(f"http://127.0.0.1:{port}/")
                    assert response.status_code == 200
                    break
                except httpx.ConnectError:
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(0.05)
        stop_owned_process(process, port)
        assert process.poll() is not None
        assert not is_listening(port)
    finally:
        stop_owned_process(process, port)
