# Investigations, source snapshots and reports

Entry: `/workspace/extensions/evidence.workbench/investigations`, after real local sign-in. Extension namespace `evidence.workbench`; actions travel through the host's authenticated and CSRF-protected plugin API. No model is needed.

Maintained driver: `scripts/verify_workbench.py --feature evidence --evidence <fresh directory>` using the backend virtual environment. Launch/Doctor/Evidence/Cleanup remain as described in the parent skill. Preserved `actions.json`, `result.json`, `gateway.log`, SQLite state and any browser screenshots must survive cleanup.

| Path | Actions and expected state | Side effects / proof |
| --- | --- | --- |
| Question to investigation | Create a title/question; select it from the list | Owned SQLite record and revision 1 |
| Source snapshot | Save title, optional HTTP(S) URL and supplied text; inspect full text | Immutable body and SHA-256; metadata in detail; full text through get_source |
| Claim evidence | Attach exact quote and supports/contradicts/context relation; combine links | Derived supported/contradicted/disputed/unsubstantiated classification |
| Invalid quote | Submit text absent from the saved source | API rejects, revision unchanged; browser keeps the form and displays an actionable error |
| Revision conflict | Repeat a mutation with an old revision | No overwrite; reload saved revision explicitly before retrying |
| Review/export | Mark current revision reviewed; generate Markdown | Session-only review, report includes status/revision and unresolved claims; new mutation resets review |
| Research preparation | Prepare chat, inspect/copy briefing, open owned thread | Durable bound thread; no model start; discard any report from an earlier revision |
| Persistence / isolation | Restart Gateway; fetch same investigation; use second authenticated owner | Same stored data through HTTP; unrelated owner receives no record |
| Disposal | Leave the page/account while a response is pending | Old responses cannot repopulate a disposed surface |

Browser acceptance uses the real Gateway rather than intercepted responses. Inspect source, claim, error and report states at the available viewport. Verify keyboard navigation and safe wrapping of a long question, source title, hash and quotation. Capture screenshots. If a viewport dimension or live model is unavailable, report that limitation rather than infer a pass.

Relevant deterministic checks: `extensions/evidence-workbench/tests/test_workbench.py`; `frontend/tests/unit/core/extensions/workbench.dom.test.ts`; frontend `pnpm check`. Browser tests complement these; they do not establish source truth or model quality.
