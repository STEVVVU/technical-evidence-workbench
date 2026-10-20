# Technical evidence workbench

This checkout retains the full DeerFlow application and adds an installed extension at `extensions/evidence-workbench`. The browser opens investigations by default. Existing research chat, agents, artifacts, tools and model settings remain available through the host.

## Local setup (Windows)

Requires Python 3.12+, Node 22+, and Git. The pnpm version is 10.26.2. From the repository root:

```powershell
python -m venv .tooling
.\.tooling\Scripts\python.exe -m pip install uv==0.13.3
cd backend
..\.tooling\Scripts\uv.exe sync --locked --python 3.12
cd ..\frontend
npx --yes pnpm@10.26.2 install --frozen-lockfile
cd ..
.\backend\.venv\Scripts\python.exe scripts/workbench.py init
```

The extension is a locked local dependency in the backend's default `extensions` group. `init` adds its operator-owned configuration to ignored `config.yaml`, preserves existing model configuration, and resolves a relative SQLite directory against the repository root. It starts with no model credentials. Review existing custom configuration before moving a populated installation to a different directory.

Start two terminals from the repository root:

```powershell
# Terminal 1: authenticated Gateway, loopback only
.\backend\.venv\Scripts\python.exe scripts/workbench.py gateway

# Terminal 2: Next.js app with its same-origin Gateway proxy
.\backend\.venv\Scripts\python.exe scripts/workbench.py web
```

Open <http://127.0.0.1:3320>. On a fresh installation, create the local admin account through setup. Stop each terminal with Ctrl+C when finished. No Docker, nginx, provider credentials or paid calls are needed for the evidence workflow. This local development path is not a production deployment recipe.

If automated browser verification initialized this checkout, its synthetic local account credentials are retained in ignored `.deer-flow/local-verification-account.json`. That account belongs only to this development instance and is separate from your GitHub sign-in.

## Workflow

1. Create an investigation with a title and technical question.
2. Paste a relevant source passage or original experiment output. Its optional public HTTP(S) URL is metadata; the app does not fetch it. Each immutable text snapshot receives a SHA-256 hash.
3. Add a specific claim. Attach up to 12 exact quotations, each classified as support, contradiction or context. Multiple links can classify a claim as disputed. A claim without substantive links remains unsubstantiated.
4. Inspect the sources, gaps and conflicts. Mark the current revision reviewed when appropriate. New evidence or claims reset it to draft.
5. Generate, inspect and download a Markdown report. Draft/reviewed status, unresolved claims, source identities and hashes remain in the export.

“Prepare research chat” creates and binds an owned conversation and produces a briefing. Copy the briefing and open that conversation. It does **not** send it or start a model run. To run agent research later, configure a model in the existing Models settings, then send the briefing. The agent receives thread-bound `evidence_get`, `evidence_get_source`, `evidence_add_source` and `evidence_add_claim` tools. It cannot mark an investigation reviewed. Live model behavior has not been verified in this model-free setup.

## Data and boundaries

- The extension uses its own SQLite file, normally `.deer-flow/evidence/workbench.sqlite`. Host accounts and conversations use the existing application database. Back up both together for a complete installation.
- Principal user ID scopes every record; an investigation or source ID alone grants no access. Browser calls retain the host's authentication, CSRF and account-change protection.
- Mutations require the current revision. Stale writes fail without overwriting stored data. Use “Reload saved revision” to reconcile another tab's changes; it discards the current unsaved form.
- A research thread preparation intent persists before the host call. If preparation fails, retry “Prepare research chat”; writes remain blocked until it reconciles the same thread. No model run is admitted by this operation.
- Human review is restricted to authenticated browser-session provenance. This is an access-control distinction, not a claim that a particular human actually inspected the evidence. Tests may exercise that path with synthetic accounts.
- Sources and claims are append-only in this first version. There is no delete/edit/archive workflow. Use a new investigation to reconsider an existing statement.
- Each source accepts up to 8,000 characters, titles 120, questions/claims/quotes 2,000. Up to 100 investigations are allowed per owner, with a 55 KB serialized collection budget. Per-investigation detail is bounded to 22 KB, full sources and reports to 60 KB; escaped Unicode may reach a byte budget earlier. Writes that exceed a budget roll back. These limits keep host action responses within its 64 KiB contract.
- Exact matching establishes that the quotation exists in the saved text. It does not establish source authenticity, factual truth, semantic entailment, research completeness or experimental reproducibility. Support/contradiction labels are supplied judgments.
- No URL ingestion, PDF parser, automatic citation extraction or automatic model execution has been added. Existing DeerFlow capabilities remain separate until explicitly used.

## Verification

Use [.agents/skills/verify-workbench/SKILL.md](../.agents/skills/verify-workbench/SKILL.md). Its maintained driver starts an isolated real Gateway, initializes synthetic sessions, drives the public actions, restarts the Gateway and checks persistence, tests owner isolation, and keeps action/log evidence after cleanup.

```powershell
.\backend\.venv\Scripts\python.exe scripts/verify_workbench.py --feature evidence --evidence .deer-flow/verification/my-fresh-run
.\backend\.venv\Scripts\python.exe -m pytest --confcutdir extensions/evidence-workbench/tests extensions/evidence-workbench/tests -q
.\backend\.venv\Scripts\ruff.exe check extensions/evidence-workbench scripts/workbench.py scripts/verify_workbench.py
cd frontend
npx --yes pnpm@10.26.2 check
npx --yes pnpm@10.26.2 exec rstest run tests/unit/core/extensions/workbench.dom.test.ts
```

No test asserts model wording. API/unit tests cover deterministic state and authorization. Browser checks cover creation, snapshot saving, quote failure with draft preservation, supported/contradicted claims, review and report generation. The real app must also be inspected after UI changes; mocked DOM checks alone do not prove its integration.

## Design and source

The interface uses the host's semantic dark/light colors and system typography. The question is the primary object; source text, evidence links, review and export remain distinct steps. A desktop master/detail layout stacks on narrow screens. Source passages and claim text are inserted as text, never interpreted HTML. Mounted views reject late responses after disposal and inherit the host's account fences.

The initial visual-reference search returned marketing layouts that did not fit an authenticated operational workbench; those layouts were not used. Rendered interaction checks guide acceptance.

Base application: [ByteDance DeerFlow](https://github.com/bytedance/deer-flow), pinned to `059758f321d83dc7196e35fa99f5829333d97ec1`, MIT license. Preserve upstream license notices and the `upstream` remote. This extension and the workbench entry/setup changes are additions in this fork. The original upstream documentation is preserved in [README.upstream.md](../README.upstream.md).
