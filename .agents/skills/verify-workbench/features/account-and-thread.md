# Account and thread persistence

## Sub-features

First-run setup, local authentication, owned thread creation and persistent thread reads.

## How to get to it (user POV)

Open `/setup` on a fresh local instance, create its first local account, then create a conversation in the workspace.

## Driving it with the maintained helper

Run `scripts/verify_workbench.py --feature baseline --evidence <fresh-directory>` using the backend Python. It follows production setup/login identity and thread endpoints with real cookies and CSRF headers. Successful evidence shows the same authenticated identity and created/read thread ID, plus an actual SQLite database.

## Gotchas

A configured provider is not required to save an empty conversation. This does not test an LLM run. An already initialized shared instance is not a substitute for the helper's isolated first-run environment. Browser UI acceptance is a separate observation.
