---
name: verify-workbench
description: Launch and drive the real Technical Evidence Workbench Gateway, verify ownership and persistent investigation behavior, and inspect its browser UI after changes.
---

# Verify the workbench

## Launch

From the repository root on Windows, after locked backend dependency installation:

```powershell
.\backend\.venv\Scripts\python.exe scripts/verify_workbench.py --evidence .deer-flow/verification/baseline-001 --feature baseline
```

Choose a fresh evidence directory each time. The maintained helper launches the actual Gateway using an ephemeral loopback port and isolated SQLite/config/home directories. It creates a synthetic local account via the production initialization API. No authentication bypass, model call or cloud service is used.

For the browser surface, start the backend with `.\backend\.venv\Scripts\python.exe -m uvicorn app.gateway.app:app --app-dir backend --host 127.0.0.1 --port 8420`. Start the frontend from `frontend/` with `DEER_FLOW_INTERNAL_GATEWAY_BASE_URL=http://127.0.0.1:8420` and `node scripts/dev.mjs --port 3320`. Open `http://127.0.0.1:3320` through the supported CUA browser. Use an isolated instance/account for destructive test actions. Keep the user's existing instance intact.

## Doctor

The helper waits for the actual `/health` response while checking its owned process is alive. It then checks setup state, initializes its test account and confirms the authenticated identity through `/api/v1/auth/me`. A response from a different preexisting process is not sufficient.

## Drive

The baseline mapped feature uses the real account and thread APIs. Read [features/README.md](features/README.md). Run the relevant unit/type/lint checks separately. For UI changes, use the supported CUA browser and inspect the actual page, interactions, keyboard focus, long content and a narrow viewport. Do not substitute mocked UI responses for a real Gateway check.

For the evidence workflow, use `--feature evidence` with a fresh evidence directory. The locked local extension must be installed through `uv sync --locked` in `backend/`. This path checks extension discovery/assets, source persistence and hashing, invalid exact quotes, disputed claims, revision conflicts, session review, Markdown export, research thread preparation without a model call, persistence across a real Gateway restart, and a second session's denied read. See [features/investigations.md](features/investigations.md).

## Evidence

The requested evidence directory retains `actions.json`, `result.json`, `gateway.log` and isolated SQLite state. Actions include public response bodies and status codes but never passwords, cookies or headers. Confirm the expected UI state with browser screenshots and keep those beside this evidence. Do not claim live model behavior from an offline run.

## Cleanup

The helper stops only its own Gateway process tree in `finally`, including failed runs. On Windows this includes the venv launcher's child interpreter. It checks both process exit and listener shutdown. It does not delete its evidence or stop other instances. Manually started UI/frontend development sessions are separate task-owned processes; stop their known handles when no longer needed. Confirm `result.json` and `gateway.log` still exist after cleanup.

## Helpers

`scripts/verify_workbench.py` owns Launch, Doctor, Drive, Evidence and Cleanup for the API surface. Use the backend virtual environment so it imports the installed real app and HTTP client.
