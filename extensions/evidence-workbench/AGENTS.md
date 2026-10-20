# Evidence workbench

Use only deerflow_extension_api. Keep all business data in the separately configured absolute SQLite storage_path. Every data query is fenced by principal.user_id. Source snapshots are append-only. Changes require the current revision and reset human review.

Only browser ActionContext with interaction=session may review or prepare research. ToolContext is never a human session. Research tools require the investigation's bound thread. Thread preparation records a durable deterministic pending intent before calling the owned thread service. Pending intent blocks writes until the same preparation is retried successfully. It never starts a model run.

Detail and Markdown budgets are checked inside the write transaction. Preserve the explicit capacity errors and rollback. Source full text is exposed only by get_source. Evidence statuses describe recorded support and contradiction links, not verified truth.

Run tests with PYTHONPATH including this directory and backend/packages/extension-api. Invoke pytest --confcutdir extensions/evidence-workbench/tests extensions/evidence-workbench/tests. UI assets and ui_manifest.json are packaged alongside the module.
