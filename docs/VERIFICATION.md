# Workbench verification

Recorded October 20, 2026, on Windows with Python 3.12.14, Node.js 25.8.1, pnpm 10.26.2, and uv 0.13.3. These are local results, separate from the hosted workflow status.

| Check | Result |
| --- | --- |
| Extension unit suite | 9 passed |
| Verification process lifecycle regression | 1 passed |
| Workbench and host-surface DOM suites | 7 passed |
| Frontend lint and TypeScript | Passed |
| Extension and helper Ruff checks | Passed |
| Locked dependency sync | Passed |
| Extension wheel with browser assets | Built |
| Real Gateway evidence workflow | Passed |
| Gateway restart with preserved investigation | Passed |
| Second authenticated owner's record access | Denied as expected |
| Desktop 1440×900 and mobile 390×844 | Inspected |

The real API driver exercises source hashing, invalid-quote rejection without mutation, disputed claims, stale revision rejection, session-authorized review, report export, and research thread preparation without model admission. It checks both investigation and source ownership through a second authenticated session. Its temporary process stops and the evidence survives cleanup.

Browser checks covered investigation creation, snapshot saving, claim forms, invalid-quote errors with draft preservation, supported and contradicted claims, review, report generation, research handoff, and keyboard navigation. At the mobile viewport, body width and scroll width were both 390 pixels. The download control was exercised; filesystem download completion was not independently established.

A browser check found that research preparation left an older report visible. A failing DOM regression test reproduced that state. The implementation now clears the cached report, and both the test and the real UI re-drive passed.

A publication check exposed a Windows venv launcher that left its child server listening after the parent exited. A controlled reproduction compared parent-only termination with stopping the owned process tree. The driver now stops that tree and checks listener shutdown before restart and cleanup. A maintained regression test covers the launcher/listener lifecycle. The earlier pooled-connection explanation was disproved by the reproduction.

No live model request or production deployment was tested. A production Next.js build and the broad inherited DeerFlow suites were not run. The focused tests establish state and authorization behavior, not factual truth, research completeness, or agent quality.

Run the commands in the [README](../README.md#verification). The [verification skill](../.agents/skills/verify-workbench/SKILL.md) documents Launch, Doctor, Drive, Evidence, and Cleanup. Generated credentials, local databases, and test runtime data remain excluded from Git.
