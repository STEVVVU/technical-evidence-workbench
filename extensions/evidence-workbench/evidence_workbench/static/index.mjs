// Administrator-installed browser module. All user content is rendered as text.
const el = (tag, text = "", attrs = {}) => {
  const node = document.createElement(tag);
  node.textContent = text;
  for (const [key, value] of Object.entries(attrs))
    node.setAttribute(key, value);
  return node;
};
const badge = (text) => el("span", text, { class: `badge ${text}` });
const count = (value, noun) => `${value} ${noun}${value === 1 ? "" : "s"}`;
const field = (label, tag = "input", attrs = {}) => {
  const wrap = el("label", label);
  const input = el(tag, "", attrs);
  input.setAttribute("aria-label", label);
  wrap.append(input);
  return [wrap, input];
};
const button = (label, handler, primary = false) => {
  const node = el("button", label, {
    type: "button",
    ...(primary ? { class: "primary" } : {}),
  });
  node.addEventListener("click", handler);
  return node;
};

export function mountWorkbench(root, context) {
  let alive = true,
    generation = 0,
    current = null,
    tab = "sources",
    busy = false;
  let items = [],
    report = null;
  const sheet = el("link", "", {
    rel: "stylesheet",
    crossorigin: "use-credentials",
    href: new URL("./styles.css", import.meta.url).href,
  });
  const shell = el("div");
  const messages = el("div", "", { role: "status", "aria-live": "polite" });
  const intro = el("div", "", { class: "intro" });
  const introText = el("div");
  introText.append(
    el("div", "Technical evidence workbench", { class: "eyebrow" }),
    el("h2", "Keep the evidence attached."),
    el(
      "p",
      "Investigate a technical question. Save the sources, connect exact quotations, and review what the evidence supports.",
    ),
  );
  intro.append(
    introText,
    button("+ New investigation", () => {
      generation++;
      current = null;
      report = null;
      renderCreate();
    }),
  );
  const layout = el("div", "", { class: "layout" });
  const sidebar = el("aside");
  const cases = el("div", "", { class: "cases" });
  sidebar.append(el("div", "Investigations", { class: "eyebrow" }), cases);
  const content = el("div", "", { "aria-label": "Investigation details" });
  layout.append(sidebar, content);
  shell.append(intro, messages, layout);
  root.replaceChildren(sheet, shell);

  const showError = (error) => {
    if (!alive || context.signal.aborted) return;
    messages.className = "alert";
    messages.setAttribute("role", "alert");
    messages.textContent =
      error instanceof Error
        ? error.message
        : "The action could not be completed. Please retry.";
  };
  const clearMessage = () => {
    messages.textContent = "";
    messages.className = "";
    messages.setAttribute("role", "status");
  };
  const call = async (action, payload) => {
    const result = await context.callBackend(action, payload);
    if (!alive || context.signal.aborted)
      throw new DOMException("View closed", "AbortError");
    return result;
  };
  const run = async (action) => {
    if (busy) return;
    busy = true;
    clearMessage();
    for (const node of shell.querySelectorAll("button")) node.disabled = true;
    try {
      await action();
    } catch (error) {
      showError(error);
    } finally {
      busy = false;
      if (alive)
        for (const node of shell.querySelectorAll("button"))
          node.disabled = node.hasAttribute("data-unavailable");
    }
  };
  const renderList = () => {
    cases.replaceChildren();
    if (!items.length)
      cases.append(el("p", "No investigations yet.", { class: "muted small" }));
    for (const item of items) {
      const node = button("", () => void run(() => select(item.id)));
      node.className = "case";
      node.setAttribute("aria-current", String(item.id === current?.id));
      node.append(
        el("strong", item.title),
        el("span", `${count(item.source_count, "source")} · ${count(item.claim_count, "claim")}`),
      );
      cases.append(node);
    }
  };
  const refreshList = async () => {
    const data = await call("list", {});
    items = data.items;
    renderList();
  };
  const select = async (id) => {
    const selected = ++generation;
    const data = await call("get", { id });
    if (selected !== generation) return;
    current = data;
    report = null;
    renderList();
    renderDetail();
  };
  const mutate = async (action, payload) => {
    const id = current.id,
      revision = current.revision;
    const updated = await call(action, { id, revision, ...payload });
    current = updated;
    report = null;
    renderDetail();
    await refreshList();
  };
  function renderCreate() {
    renderList();
    content.replaceChildren();
    const panel = el("section", "", { class: "panel" });
    panel.append(
      el("h3", "Start with a question"),
      el(
        "p",
        "Choose something specific enough to support or challenge with evidence.",
        { class: "muted small" },
      ),
    );
    const form = el("form");
    const [titleLabel, title] = field("Investigation title", "input", {
      required: "",
      maxlength: "120",
      placeholder: "e.g. WAL durability under power loss",
    });
    const [questionLabel, question] = field("Technical question", "textarea", {
      required: "",
      maxlength: "2000",
      placeholder:
        "What needs to hold for an acknowledged write to survive a crash?",
    });
    const submit = el("button", "Create investigation", {
      type: "submit",
      class: "primary",
    });
    form.append(titleLabel, questionLabel, submit);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      void run(async () => {
        current = await call("create", {
          title: title.value,
          question: question.value,
        });
        tab = "sources";
        renderDetail();
        await refreshList();
      });
    });
    panel.append(form);
    content.append(panel);
  }
  function renderDetail() {
    content.replaceChildren();
    const heading = el("div");
    const meta = el("div", "", { class: "row between" });
    const status = el("div", "", { class: "row" });
    status.append(
      badge(current.status === "reviewed" ? "reviewed" : "draft"),
      el("span", `Revision ${current.revision}`, { class: "small muted" }),
    );
    meta.append(
      status,
      button("Reload saved revision", () => void run(() => select(current.id))),
    );
    heading.append(
      meta,
      el("h2", current.title),
      el("p", current.question, { class: "question" }),
    );
    const counts = el("div", "", { class: "row small muted" });
    counts.append(
      el("span", count(current.sources.length, "source")),
      el("span", "·"),
      el("span", count(current.claims.length, "claim")),
      el("span", "·"),
      el(
        "span",
        `${current.claims.filter((claim) => claim.status === "disputed").length} disputed`,
      ),
    );
    heading.append(counts);
    content.append(heading);
    const tabs = el("nav", "", {
      class: "tabs",
      "aria-label": "Investigation sections",
    });
    for (const [id, label] of [
      ["sources", "Sources"],
      ["claims", "Claims"],
      ["report", "Review & export"],
    ]) {
      const node = button(label, () => {
        tab = id;
        clearMessage();
        renderDetail();
      });
      node.setAttribute("aria-current", String(tab === id));
      tabs.append(node);
    }
    content.append(tabs);
    if (tab === "sources") renderSources();
    if (tab === "claims") renderClaims();
    if (tab === "report") renderReport();
    content.append(
      el(
        "p",
        "Quote matching checks the saved text. Evidence classifications are judgments, not proof that a claim is true.",
        { class: "notice" },
      ),
    );
  }
  function renderSources() {
    const panel = el("section", "", { class: "panel" });
    const head = el("div", "", { class: "section-head" });
    head.append(
      el("h3", "Source snapshots"),
      el("span", "Saved text · SHA-256", { class: "small muted" }),
    );
    panel.append(head);
    if (!current.sources.length)
      panel.append(
        el(
          "p",
          "Add a documentation excerpt, paper passage, or experiment output. Snapshots keep the text that your claims refer to.",
          { class: "muted" },
        ),
      );
    for (const source of current.sources) {
      const item = el("article", "", { class: "source" });
      item.append(el("h4", source.title));
      if (/^https?:\/\//i.test(source.url))
        item.append(
          el("a", source.url, {
            href: source.url,
            target: "_blank",
            rel: "noopener noreferrer",
          }),
        );
      item.append(
        el("p", source.excerpt, { class: "excerpt" }),
        el("p", `SHA-256 ${source.sha256}`, { class: "hash" }),
      );
      const full = el("details");
      const summary = el("summary", "Read saved text");
      full.append(summary);
      let loaded = false;
      full.addEventListener("toggle", () => {
        if (!full.open || loaded) return;
        const id = current.id;
        void run(async () => {
          const data = await call("get_source", { id, source_id: source.id });
          if (!full.isConnected) return;
          full.append(el("pre", data.text));
          loaded = true;
        });
      });
      item.append(full);
      panel.append(item);
    }
    content.append(panel);
    const add = el("details", "", {
      class: "panel",
      ...(!current.sources.length ? { open: "" } : {}),
    });
    add.append(el("summary", "+ Add source snapshot"));
    const form = el("form");
    const [titleLabel, title] = field("Source title", "input", {
      required: "",
      maxlength: "120",
      placeholder: "Paper, document, or experiment name",
    });
    const [urlLabel, url] = field("Source URL (optional)", "input", {
      type: "url",
      placeholder: "https://…",
      maxlength: "2000",
    });
    const [textLabel, text] = field("Saved source text", "textarea", {
      required: "",
      maxlength: "8000",
      rows: "7",
      placeholder:
        "Paste up to 8,000 characters. URLs are recorded, not fetched.",
    });
    form.append(
      titleLabel,
      urlLabel,
      textLabel,
      el("button", "Save snapshot", { type: "submit", class: "primary" }),
    );
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      void run(async () => {
        if (url.value && !/^https?:\/\//i.test(url.value))
          throw new Error(
            "Use an HTTP or HTTPS source URL, or leave it empty.",
          );
        await mutate("add_source", {
          title: title.value,
          url: url.value,
          text: text.value,
        });
      });
    });
    add.append(form);
    content.append(add);
  }
  function renderClaims() {
    const panel = el("section", "", { class: "panel" });
    panel.append(el("h3", "Claims & evidence"));
    if (!current.claims.length)
      panel.append(
        el(
          "p",
          "State one testable claim at a time. Attach quotations and say whether each supports, contradicts, or gives context.",
          { class: "muted" },
        ),
      );
    for (const claim of current.claims) {
      const item = el("article", "", { class: "claim" });
      const head = el("div", "", { class: "row between" });
      head.append(
        el("p", claim.text, { class: "statement" }),
        badge(claim.status),
      );
      item.append(head);
      for (const evidence of claim.evidence) {
        const source = current.sources.find(
          (value) => value.id === evidence.source_id,
        );
        const quote = el("blockquote");
        quote.append(
          el("p", evidence.quote),
          el(
            "footer",
            `${evidence.relation} · ${source?.title ?? "Source unavailable"}`,
          ),
        );
        item.append(quote);
      }
      if (!claim.evidence.length)
        item.append(el("p", "No evidence attached.", { class: "muted small" }));
      panel.append(item);
    }
    content.append(panel);
    const add = el("details", "", {
      class: "panel",
      ...(!current.claims.length ? { open: "" } : {}),
    });
    add.append(el("summary", "+ Add a claim"));
    const form = el("form");
    const [textLabel, text] = field("Claim statement", "textarea", {
      required: "",
      maxlength: "2000",
      placeholder: "A specific statement the evidence can support or challenge",
    });
    form.append(textLabel);
    const links = el("div", "", { class: "stack" });
    const inputs = [];
    const appendEvidence = () => {
      if (inputs.length >= 12) {
        showError(new Error("A claim can contain up to 12 evidence links."));
        return;
      }
      const group = el("div", "", { class: "evidence-input" });
      const [sourceLabel, source] = field("Saved source", "select", {
        required: "",
      });
      source.append(el("option", "Select a source", { value: "" }));
      for (const entry of current.sources)
        source.append(el("option", entry.title, { value: entry.id }));
      const [relationLabel, relation] = field("Relation to claim", "select");
      for (const value of ["supports", "contradicts", "context"])
        relation.append(el("option", value, { value }));
      const [quoteLabel, quote] = field(
        "Exact quotation from saved text",
        "textarea",
        { required: "", maxlength: "2000", rows: "3" },
      );
      const record = { source, relation, quote };
      inputs.push(record);
      group.append(
        sourceLabel,
        relationLabel,
        quoteLabel,
        button("Remove evidence link", () => {
          inputs.splice(inputs.indexOf(record), 1);
          group.remove();
        }),
      );
      links.append(group);
    };
    const attach = button("+ Attach evidence", appendEvidence);
    attach.disabled = !current.sources.length;
    if (!current.sources.length) attach.setAttribute("data-unavailable", "");
    form.append(
      links,
      attach,
      el(
        "p",
        current.sources.length
          ? "Copy quotes exactly, including punctuation and line breaks. You can attach conflicting evidence to the same claim."
          : "Add a source first, or save this claim as unsubstantiated.",
        { class: "small muted" },
      ),
      el("button", "Save claim", { type: "submit", class: "primary" }),
    );
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      void run(async () => {
        const evidence = inputs.map((entry) => ({
          source_id: entry.source.value,
          relation: entry.relation.value,
          quote: entry.quote.value,
        }));
        for (const link of evidence) {
          const source = await call("get_source", {
            id: current.id,
            source_id: link.source_id,
          });
          if (!source.text.includes(link.quote))
            throw new Error(
              "That quotation does not exactly match the saved source. Check punctuation, spaces, and line breaks. Your draft is still here.",
            );
        }
        await mutate("add_claim", { text: text.value, evidence });
      });
    });
    add.append(form);
    content.append(add);
  }
  function renderReport() {
    const panel = el("section", "", { class: "panel stack" });
    panel.append(
      el(
        "h3",
        current.status === "reviewed"
          ? "Review recorded"
          : "Review the evidence",
      ),
      el(
        "p",
        "Review means a person inspected this revision. It does not certify truth or resolve conflicting claims. New sources or claims return the investigation to draft.",
        { class: "muted" },
      ),
    );
    const unresolved = current.claims.filter(
      (claim) => claim.status !== "supported",
    );
    panel.append(
      el(
        "p",
        `${unresolved.length} of ${current.claims.length} claims are disputed, contradicted, or unsubstantiated.`,
        { class: "small" },
      ),
    );
    const actions = el("div", "", { class: "row" });
    if (current.status !== "reviewed")
      actions.append(
        button(
          "Mark this revision reviewed",
          () => void run(() => mutate("review", {})),
        ),
      );
    actions.append(
      button(
        "Generate Markdown report",
        () =>
          void run(async () => {
            report = await call("export", { id: current.id });
            renderDetail();
          }),
        true,
      ),
    );
    panel.append(actions);
    if (report) {
      panel.append(
        el("pre", report.markdown),
        button("Download report .md", () => {
          const url = URL.createObjectURL(
            new Blob([report.markdown], {
              type: "text/markdown;charset=utf-8",
            }),
          );
          const link = el("a", "", { href: url, download: report.filename });
          root.append(link);
          link.click();
          link.remove();
          URL.revokeObjectURL(url);
        }),
      );
    }
    content.append(panel);
    const research = el("section", "", { class: "panel stack research" });
    research.append(
      el("h3", "Continue in research chat"),
      el(
        "p",
        "Prepare a conversation and a briefing for the existing agent runtime. This creates no model run. A configured model is needed when you send the briefing.",
        { class: "muted small" },
      ),
    );
    research.append(
      button(
        "Prepare research chat",
        () =>
          void run(async () => {
            const result = await call("prepare_research", {
              id: current.id,
              revision: current.revision,
            });
            current = await call("get", { id: current.id });
            report = null;
            renderDetail();
            await refreshList();
            const brief = el("section", "", { class: "panel stack" });
            brief.append(
              el("h3", "Research briefing"),
              el("pre", result.brief),
            );
            const actions = el("div", "", { class: "row" });
            actions.append(
              button(
                "Copy briefing",
                () =>
                  void run(async () => {
                    await navigator.clipboard.writeText(result.brief);
                    messages.textContent =
                      "Briefing copied. Paste it into the research chat when a model is configured.";
                    messages.className = "success";
                  }),
              ),
            );
            if (context.openConversation)
              actions.append(
                button(
                  "Open research chat",
                  () =>
                    void run(() => context.openConversation(result.thread_id)),
                ),
              );
            brief.append(actions);
            content.append(brief);
          }),
      ),
    );
    content.append(research);
  }
  void run(async () => {
    await refreshList();
    if (items.length) await select(items[0].id);
    else renderCreate();
  });
  return {
    dispose() {
      alive = false;
      generation++;
      root.replaceChildren();
    },
  };
}

export default {
  apiVersion: 1,
  module: "evidence.workbench.v1",
  icon: "notebook-pen",
  surfaces: [
    {
      id: "investigations",
      slot: "page",
      title: "Investigations",
      navigation: {
        label: "Investigations",
        labelZh: "调查",
        icon: "notebook-pen",
      },
      mount: mountWorkbench,
    },
  ],
};
