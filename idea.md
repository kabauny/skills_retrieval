# AI Agent Skills: A Cross-Platform Overview

*A reference summary covering Claude, Gemini, and OpenAI skill systems, with application notes for clinical decision support and information retrieval architectures.*

---

## What Skills Are

A **skill** is a folder containing a `SKILL.md` file (and optionally supporting files like scripts, templates, or reference documents). The `SKILL.md` has two key parts:

1. **A description** — tells the LLM *when* to use the skill (the trigger conditions)
2. **Instructions** — tells the LLM *how* to do the task well (best practices, steps, gotchas)

When a user makes a request, the agent scans available skill descriptions. If one matches, it reads that skill's full instructions *before* doing the work. This is called **progressive disclosure** — the agent doesn't load everything upfront, just what's relevant.

### Why Skills Exist

LLMs are generalists. For specialized tasks, you want distilled, battle-tested procedural knowledge. Skills solve three problems:

- Training data gets stale (e.g., product details, guidelines change)
- Generic LLM output is often mediocre for specialized tasks
- Organizations have proprietary workflows the model can't know from pretraining

### Basic Structure

```
my-skill/
├── SKILL.md           # Entry point: description + instructions
├── scripts/           # Helper code (optional)
├── templates/         # Boilerplate files (optional)
└── references/        # Deeper docs loaded only if needed
```

The `SKILL.md` uses YAML frontmatter:

```markdown
---
name: skill-name
description: Explain exactly when this skill should and should not trigger.
---

Skill instructions for the agent to follow.
```

---

## The Cross-Platform Picture

### Anthropic (Claude)

- **Claude Skills** — the original SKILL.md format, available across Claude.ai, Claude Desktop, Claude Code, and the API
- Portable across platforms supporting the open Agent Skills spec
- No character limit on instructions; supports multi-file skill folders

### Google (Gemini)

Three distinct things, all called "skills" or "skill-like" but *not equivalent*:

1. **Gemini Gems** (consumer app) — custom assistants with a persona and ~4,000 character instruction cap. Equivalent to Custom GPTs. Too shallow for complex procedural knowledge.
2. **Gemini CLI Skills** (developer) — uses the same `SKILL.md` format as Claude. A skill written for Claude Code works in Gemini CLI unchanged. Uses three-tier discovery (workspace, user, extension) with progressive disclosure.
3. **Skills in Chrome** (consumer) — bookmarked prompts, not procedural skills. Ignore this for architectural purposes.

### OpenAI

1. **Custom GPTs** (consumer ChatGPT) — the oldest and shallowest. ~8,000 character cap. Not portable outside ChatGPT.
2. **Codex Agent Skills** — full `SKILL.md` support, same format as Claude and Gemini CLI. Progressive disclosure, explicit and implicit invocation, workspace/user/admin/system scoping.

### The Convergence

Claude, Gemini CLI, OpenAI Codex, GitHub Copilot, Cursor, VS Code, and OpenCode have all adopted the same **Agent Skills open standard** (agentskills.io). Write a skill once, use it across platforms. This is the most important practical takeaway: **you are not locked in to any provider.**

---

## Skills for Information Retrieval (vs. Code Execution)

Most public writing about SKILL.md is coding-flavored, but skills work equally well — arguably better — for **information retrieval**.

### Skills as Retrieval Routing

For retrieval, a skill is a **routing decision wrapped around a curated knowledge bundle**. The instructions aren't "run this script." They're "when a query matches *this scenario*, load *this reference content* and reason over it using *these rules*."

Example structure:

```
nsclc-first-line-egfr-mutant/
├── SKILL.md                    # when to load, how to reason
├── references/
│   ├── nccn-guidelines.md      # guideline excerpts
│   ├── flaura-trial.md         # pivotal trial summary
│   └── resistance-mutations.md # second-line context
└── schemas/
    └── required-pso-fields.json  # required patient data
```

### Skills vs. Traditional RAG

| Aspect | Traditional RAG | Skills-Based Retrieval |
|---|---|---|
| Retrieval basis | Chunk similarity (embedding-based) | Semantic scope (description-matched) |
| Determinism | Probabilistic top-k | Named, curated bundle |
| Auditability | "Top-5 cosine matches" | "Loaded skill X, which cites Y" |
| Scope control | Relies on chunker quality | Hand-assembled knowledge bundles |
| Preconditions | Cannot enforce | Can declare required inputs |
| Token efficiency | Top-k regardless of relevance | Only matched skill's references |
| Rare/long-tail queries | Strong | Weak — falls back to RAG |

### When to Use Which

- **Skills** for well-characterized decision nodes (first-line EGFR, HR+/HER2- adjuvant, staging pathways)
- **RAG** as fallback for queries that don't match any skill cleanly
- **Hybrid** is the realistic production pattern

---

## Skills as Living Wikis: The Maintenance Dimension

The section above treats a skill as a *static bundle* — references handed to the LLM at query time. That framing is incomplete. A skill's reference folder can be a **living wiki** that the LLM maintains over time, which solves problems the static view leaves open: how guidelines stay current, how edge cases from real queries get captured, and how the audit trail is produced.

This draws on Karpathy's [LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). Instead of re-deriving knowledge from raw sources on every query, the LLM *incrementally builds and maintains* a persistent, structured knowledge base. The bookkeeping — cross-references, contradictions, consistency across pages — is the part humans abandon; LLMs do it cheaply.

### Three Layers Inside a Skill

- **Raw sources** — immutable primary documents: NCCN PDFs, trial papers, FDA labels, payer policies. The LLM reads but never modifies these.
- **The skill's wiki** — the `references/` folder. Summaries, entity pages (drugs, biomarkers, trials), comparison tables, cross-references. LLM-owned, human-reviewed.
- **The schema** — `SKILL.md` frontmatter plus workspace-level `AGENTS.md`. Defines conventions, required inputs, routing rules, update workflow.

### Three Operations

- **Ingest.** A new NCCN update or trial readout lands. The LLM reads it, identifies affected skills, updates their reference pages, flags contradictions with prior guidance, appends a log entry. One source can touch many pages across many skills.
- **Query.** A clinical case invokes the skill. The LLM synthesizes an answer from the wiki. Valuable synthesis — edge cases, unusual presentations, novel resistance patterns — gets filed back into the skill so the next identical query benefits.
- **Lint.** A periodic health check: stale claims newer trials have superseded, orphan references with no page linking to them, contradictions between pages, gaps where a concept is mentioned but not documented.

### Two Special Files per Skill

- **`index.md`** — a catalog of the skill's pages with one-line summaries, updated on every ingest. At moderate scale this replaces embedding-based retrieval inside the skill.
- **`log.md`** — append-only, chronological, with parseable entry prefixes (e.g. `## [2026-04-15] ingest | FLAURA2 OS update`). This *is* the DPO audit trail — what was loaded, what changed, what was decided, and when. One artifact, two purposes.

### Governance Split

The human curates sources, approves updates, and directs analysis. The LLM handles cross-referencing, summary maintenance, and consistency — the parts that cause human-maintained clinical wikis to decay. For regulated use, a clinician-reviewer sits in the loop on proposed updates before they go live in a skill's references. Git handles version history, branching, and review workflow for free.

---

## Application: Clinical Decision Support Architecture

### Design Pattern

1. **Skills as graph nodes.** Each node in a traversal graph is a `SKILL.md` folder. `node_role` metadata and trigger conditions live in frontmatter. The traversal engine uses description + frontmatter to decide edges.
2. **References inside skills = curated knowledge.** Trial summaries, guideline excerpts, biomarker decision tables — markdown files inside the skill folder, loaded only when that node is active.
3. **RAG as fallback.** When no skill matches confidently, fall back to dense retrieval over a broader corpus.
4. **Shared data contracts** (e.g., Patient Summary Object / Decision Processing Object) are the interface between nodes. The skill's instructions read/write these fields; the DPO captures what was loaded and why — the audit trail.

### Solving the Routing-Failure Problem

Skipped foundational steps (e.g., the LLM bypassing staging evaluation) is a classic description-matching failure. Three patterns to enforce correct routing:

1. **`allow_implicit_invocation: false`** on foundational nodes. The router cannot silently skip them via description-matching — they must be explicitly invoked by upstream logic. (This is OpenAI's flag, but the pattern works in any skill system.)
2. **Workspace-level mandatory rules** (OpenAI's AGENTS.md pattern): "Before any line-of-therapy node, call `$staging-evaluation` and `$biomarker-review`." Enforced at the orchestration layer, not inside each skill.
3. **Tighter trigger conditions** in frontmatter descriptions. Vague descriptions cause misrouting; descriptions with explicit scope and boundaries ("USE ONLY WHEN... DO NOT USE IF...") route more reliably.

### Routing Test Framework

Adapted from OpenAI's skill eval methodology, four test categories cover routing correctness:

- **Explicit invocation** — named skill call. Does the skill load?
- **Implicit invocation** — scenario described in natural language with no skill name. Does the description trigger the right skill?
- **Contextual invocation** — same scenario with noise (comorbidities, irrelevant history). Still routes correctly?
- **Negative control** — adjacent but wrong scenario. Does the skill *correctly not fire*?

Example for an NSCLC first-line EGFR skill:

| Test | Prompt | Expected |
|---|---|---|
| Explicit | "Use the EGFR first-line skill for this patient." | Loads |
| Implicit | "65F, adenocarcinoma, exon 19 deletion, treatment-naive." | Loads |
| Contextual | Same + unrelated comorbidities, remote prior cancer history | Loads |
| Negative | "65F, adenocarcinoma, ALK fusion, treatment-naive." | Does NOT load |

---

## Key Takeaways

1. **"Skills" as a formal concept exists in Claude, Gemini CLI, and OpenAI Codex**, using the same open `SKILL.md` standard. Consumer-facing Gems and Custom GPTs are a different, shallower thing.
2. **Write skills once, deploy across providers.** Lock-in is avoidable. Swap the inference model (Claude, Gemini, GPT) based on cost, latency, and accuracy for your domain.
3. **Skills are not just for code.** They're a general-purpose pattern for routing an LLM to a curated knowledge bundle with explicit preconditions.
4. **For clinical decision support specifically**, the skills pattern fits better than pure RAG for well-characterized decision nodes, because it provides auditability, version control, explicit preconditions, and token efficiency.
5. **Routing failures are the main risk.** Mitigate with explicit-only invocation on foundational nodes, workspace-level mandatory-skill rules, and a four-category eval harness (explicit, implicit, contextual, negative).
6. **Hybrid is realistic.** Skills for the known decision graph; RAG for the long tail; shared data contracts (PSO/DPO-style) as the interface.
7. **Skills are living wikis, not frozen bundles.** Each skill's `references/` folder evolves via Ingest/Query/Lint loops. Guidelines stay current because the LLM does the maintenance. `log.md` inside the skill doubles as the audit trail. Humans curate and approve; the LLM does the bookkeeping.
