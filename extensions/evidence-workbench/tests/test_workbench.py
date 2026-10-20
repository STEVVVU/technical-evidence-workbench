import hashlib
import json

import pytest

from evidence_workbench.store import Workbench


@pytest.fixture
def store(tmp_path):
    return Workbench(str(tmp_path / "evidence.sqlite"))


def create(store, owner="alice"):
    return store.apply(
        "create", {"title": "Decision", "question": "What is known?"}, owner
    )


def source(store, detail, text="Observed result", owner="alice"):
    return store.apply(
        "add_source",
        dict(
            id=detail["id"],
            revision=detail["revision"],
            title="Report",
            url="https://example.org/report",
            text=text,
        ),
        owner,
    )


def test_snapshots_quotes_revision_and_review(store):
    d = create(store)
    d = source(store, d)
    s = d["sources"][0]
    assert "text" not in s
    raw = store.apply("get_source", {"id": d["id"], "source_id": s["id"]}, "alice")
    assert raw["sha256"] == hashlib.sha256(raw["text"].encode()).hexdigest()
    with pytest.raises(ValueError, match="revision"):
        source(store, {**d, "revision": 1})
    payload = dict(
        id=d["id"],
        revision=d["revision"],
        text="A claim",
        evidence=[dict(source_id=s["id"], quote="invented", relation="supports")],
    )
    with pytest.raises(ValueError, match="quote"):
        store.apply("add_claim", payload, "alice")
    payload["evidence"][0]["quote"] = "Observed"
    d = store.apply("add_claim", payload, "alice")
    assert d["claims"][0]["status"] == "supported"
    d = store.apply("review", dict(id=d["id"], revision=d["revision"]), "alice")
    assert d["status"] == "reviewed"
    d = source(store, d)
    assert d["status"] == "open"


def test_owner_persistence_and_cross_investigation(store):
    d = source(store, create(store))
    other = create(store)
    with pytest.raises(ValueError):
        store.apply("get", {"id": d["id"]}, "bob")
    with pytest.raises(ValueError):
        store.apply(
            "add_claim",
            dict(
                id=other["id"],
                revision=1,
                text="Claim",
                evidence=[
                    dict(
                        source_id=d["sources"][0]["id"],
                        quote="Observed",
                        relation="supports",
                    )
                ],
            ),
            "alice",
        )
    assert Workbench(str(store.path)).apply("get", {"id": d["id"]}, "alice") == d
    assert store.apply("list", {}, "bob") == {"items": []}


def test_budget_rolls_back_and_url_validation(store):
    d = create(store)
    for url in [
        "javascript:alert(1)",
        "https://user:password@example.org",
        "http://127.0.0.1/a",
    ]:
        with pytest.raises(ValueError):
            store.apply(
                "add_source",
                dict(id=d["id"], revision=1, title="Bad", url=url, text="x"),
                "alice",
            )
    for _ in range(100):
        before = d
        try:
            d = store.apply(
                "add_claim",
                dict(id=d["id"], revision=d["revision"], text="長" * 2000, evidence=[]),
                "alice",
            )
        except ValueError as exc:
            assert "capacity" in str(exc)
            assert store.apply("get", {"id": d["id"]}, "alice") == before
            break
    else:
        pytest.fail("No bounded capacity")
    assert len(json.dumps(d).encode()) < 65536
    assert (
        len(json.dumps(store.apply("export", {"id": d["id"]}, "alice")).encode())
        < 65536
    )


@pytest.mark.asyncio
async def test_session_and_thread_provenance(store):
    from deerflow_extension_api.auth import ExtensionPrincipal
    from deerflow_extension_api.plugins import ActionContext, ToolContext

    principal = ExtensionPrincipal(user_id="alice")
    d = create(store)
    payload = dict(id=d["id"], revision=1)
    with pytest.raises(ValueError, match="session"):
        await store.handler("review")(payload, ActionContext(principal, {}))
    with pytest.raises(ValueError, match="session"):
        await store.handler("review")(
            payload, ToolContext(principal, {}, "fake", interaction="session")
        )

    class Runs:
        calls = 0

        async def create_thread(self, **kwargs):
            self.calls += 1
            return kwargs["thread_id"]

    runs = Runs()
    ctx = ActionContext(principal, {}, interaction="session", agent_runs=runs)
    result = await store.handler("prepare_research")(payload, ctx)
    d = store.apply("get", {"id": d["id"]}, "alice")
    assert (
        await store.handler("prepare_research")(
            dict(id=d["id"], revision=d["revision"]), ctx
        )
    ) == result
    assert runs.calls == 1
    mutation = dict(
        id=d["id"],
        revision=d["revision"],
        title="Tool report",
        url="",
        text="actual evidence",
    )
    with pytest.raises(ValueError, match="thread"):
        await store.handler("add_source")(mutation, ToolContext(principal, {}, "wrong"))
    d = await store.handler("add_source")(
        mutation, ToolContext(principal, {}, result["thread_id"])
    )
    with pytest.raises(ValueError, match="thread"):
        await store.handler("get")({"id": d["id"]}, ToolContext(principal, {}, "wrong"))
    assert (
        await store.handler("get")(
            {"id": d["id"]}, ToolContext(principal, {}, result["thread_id"])
        )
        == d
    )


def test_classification_and_review_are_honest(store):
    d = source(store, create(store), "<script>facts</script>")
    sid = d["sources"][0]["id"]
    for relations, expected in [
        ([], "unsubstantiated"),
        (["context"], "unsubstantiated"),
        (["contradicts"], "contradicted"),
        (["supports", "contradicts"], "disputed"),
    ]:
        d = store.apply(
            "add_claim",
            dict(
                id=d["id"],
                revision=d["revision"],
                text="[unsafe](javascript:alert(1))",
                evidence=[
                    dict(source_id=sid, quote="facts", relation=r) for r in relations
                ],
            ),
            "alice",
        )
        assert d["claims"][-1]["status"] == expected
    markdown = store.apply("export", {"id": d["id"]}, "alice")["markdown"]
    assert "Status: open" in markdown
    assert "## Unresolved and disputed" in markdown
    assert "\\[unsafe\\]" in markdown
    assert "not semantic truth" in markdown


@pytest.mark.asyncio
async def test_pending_research_retry_is_durable_and_blocks_mutations(store):
    from deerflow_extension_api.auth import ExtensionPrincipal
    from deerflow_extension_api.plugins import ActionContext

    class Runs:
        targets = []

        async def create_thread(self, **kwargs):
            self.targets.append(kwargs["thread_id"])
            if len(self.targets) == 1:
                raise RuntimeError("service interrupted")
            return kwargs["thread_id"]

    d = create(store)
    runs = Runs()
    ctx = ActionContext(
        ExtensionPrincipal(user_id="alice"), {}, interaction="session", agent_runs=runs
    )
    with pytest.raises(RuntimeError, match="interrupted"):
        await store.handler("prepare_research")(dict(id=d["id"], revision=1), ctx)
    with pytest.raises(ValueError, match="pending"):
        source(store, d)
    reopened = Workbench(str(store.path))
    result = await reopened.handler("prepare_research")(
        dict(id=d["id"], revision=1), ctx
    )
    assert runs.targets == [result["thread_id"]] * 2
    assert reopened.apply("get", {"id": d["id"]}, "alice")["revision"] == 2


def test_source_capacity_transaction_and_response_bounds(store):
    d = create(store)
    with pytest.raises(ValueError, match="capacity"):
        source(store, d, "\U0001f50e" * 8000)
    assert store.apply("get", {"id": d["id"]}, "alice") == d
    body = "\U0001f50e" * 4000
    for _ in range(50):
        before = d
        try:
            d = source(store, d, body)
        except ValueError as exc:
            assert "capacity" in str(exc)
            assert store.apply("get", {"id": d["id"]}, "alice") == before
            with store.connect() as db:
                assert db.execute(
                    "SELECT count(*) FROM sources WHERE owner=? AND investigation=?",
                    ("alice", d["id"]),
                ).fetchone()[0] == len(d["sources"])
            break
    else:
        pytest.fail("Unbounded snapshot metadata")
    raw = store.apply(
        "get_source", dict(id=d["id"], source_id=d["sources"][0]["id"]), "alice"
    )
    assert len(json.dumps(raw).encode()) < 65536


def test_collection_supports_more_than_four_investigations(store):
    for _ in range(6):
        create(store)
    assert len(store.apply("list", {}, "alice")["items"]) == 6


def test_concurrent_writers_require_one_current_revision(store):
    from concurrent.futures import ThreadPoolExecutor

    d = create(store)

    def write():
        try:
            source(Workbench(str(store.path)), d)
            return "saved"
        except ValueError as exc:
            assert "revision" in str(exc)
            return "stale"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: write(), range(2))) == ["saved", "stale"]
    assert len(store.apply("get", {"id": d["id"]}, "alice")["sources"]) == 1
