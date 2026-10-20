import { afterEach, expect, rs, test } from "@rstest/core";

import { mountWorkbench } from "../../../../../extensions/evidence-workbench/evidence_workbench/static/index.mjs";

afterEach(() => document.body.replaceChildren());

test("investigation titles and questions are inert text", async () => {
  const detail = {
    id: "a",
    title: '<img src=x onerror="alert(1)">',
    question: "<script>unsafe()</script>",
    revision: 1,
    status: "open",
    sources: [],
    claims: [],
  };
  const callBackend = rs.fn(async (action: string) =>
    action === "list"
      ? { items: [{ ...detail, source_count: 0, claim_count: 0 }] }
      : detail,
  );
  const root = document.createElement("div");
  const control = mountWorkbench(root, {
    locale: "en-US",
    signal: new AbortController().signal,
    callBackend,
  });
  await rs.waitFor(() => expect(root.textContent).toContain(detail.question));
  expect(root.querySelector("img")).toBeNull();
  expect(root.querySelector("script")).toBeNull();
  expect(root.querySelectorAll("button").length).toBeGreaterThan(0);
  control.dispose();
});

test("disposed views reject late responses and leave no account data", async () => {
  let resolveList: (data: unknown) => void = () => undefined;
  const pending = new Promise((resolve) => {
    resolveList = resolve;
  });
  const root = document.createElement("div");
  const callBackend = rs.fn(() => pending);
  const control = mountWorkbench(root, {
    locale: "en-US",
    signal: new AbortController().signal,
    callBackend,
  });
  control.dispose();
  resolveList({
    items: [
      {
        id: "late",
        title: "Private old account",
        source_count: 0,
        claim_count: 0,
      },
    ],
  });
  await pending;
  await Promise.resolve();
  expect(root.textContent).toBe("");
  expect(callBackend).toHaveBeenCalledTimes(1);
});

test("preparing research clears an export from an older reviewed revision", async () => {
  const detail = {
    id: "a",
    title: "Investigation",
    question: "Question",
    revision: 5,
    status: "reviewed",
    sources: [],
    claims: [],
  };
  let prepared = false;
  const callBackend = rs.fn(async (action: string) => {
    if (action === "list")
      return { items: [{ ...detail, source_count: 0, claim_count: 0 }] };
    if (action === "export")
      return { filename: "report.md", markdown: "REVIEWED OLD REVISION FIVE" };
    if (action === "prepare_research") {
      prepared = true;
      return { thread_id: "owned", brief: "Research briefing contents" };
    }
    return prepared
      ? { ...detail, revision: 6, status: "open", thread_id: "owned" }
      : detail;
  });
  const root = document.createElement("div");
  const control = mountWorkbench(root, {
    locale: "en-US",
    signal: new AbortController().signal,
    callBackend,
  });
  const click = (label: string) => {
    const target = Array.from(root.querySelectorAll("button")).find(
      (node) => node.textContent === label,
    );
    expect(target).toBeDefined();
    target!.click();
  };
  await rs.waitFor(() => expect(root.textContent).toContain("Revision 5"));
  click("Review & export");
  click("Generate Markdown report");
  await rs.waitFor(() =>
    expect(root.textContent).toContain("REVIEWED OLD REVISION FIVE"),
  );
  click("Prepare research chat");
  await rs.waitFor(() =>
    expect(root.textContent).toContain("Research briefing contents"),
  );
  expect(root.textContent).toContain("Revision 6");
  expect(root.textContent).not.toContain("REVIEWED OLD REVISION FIVE");
  control.dispose();
});
