---
title: "Retrieval flow — how a query becomes an answer"
tags: [system, retrieval, documentation]
---

# Retrieval flow — how a query becomes an answer

System documentation (not clinical content). It traces how the app routes a
question, pins the reasoning lenses, and falls back to grounded search — using a
real worked example. See also the principle layer (`wiki/principles/`) and the
link contract in `SCHEMA.md`.

## The pipeline

1. **Route (Flash).** Embed the query, take the top-N most similar pages, and let
   Flash rerank that shortlist. Cheap — only candidate summaries are sent, not the
   whole index.
2. **Graph expand (principle-blind).** Pull in relationally-connected *entity*
   pages via shared hubs, weighted by hub specificity. Principle/lens nodes are
   excluded as hubs and candidates so they never bridge unrelated topics.
3. **Pin lenses.** For every picked page, add the principle nodes it links to
   (efficacy, adverse-events, …). Pinned deterministically — not scored — because
   the most-linked lenses would otherwise be suppressed by anti-hub weighting.
4. **Load (user-aware).** Read the chosen pages. Principle stems resolve to the
   provider's personal fork in `avatar/{user}/principles/` if present, else the
   shared skeleton.
5. **Synthesize (Pro).** Answer strictly from the loaded pages. If they lack the
   specifics, emit `INSUFFICIENT_WIKI_DATA`.
6. **Fallback (grounded).** On insufficiency, run grounded search — but keep the
   wiki pages in context so the lenses steer the grounded answer. Origin becomes
   `mixed`.

## Worked example — "Treatment options for stage III bladder cancer"

Actual run: **origin = mixed · 3 Gemini calls · 13.8k tokens**. The six retrieved
pages were all principle nodes — the disease framework plus the five lenses it
pins — with no entity pages.

```mermaid
flowchart TD
    Q["🧑‍⚕️ Query:<br/>'Treatment options for<br/>stage III bladder cancer'"]

    subgraph ROUTE["① ROUTE — Flash (call 1)"]
        E["Embed query →<br/>cosine vs page embeddings →<br/>top-6 shortlist"]
        R["Flash rerank shortlist"]
        E --> R
    end
    Q --> E

    R -->|"picks best semantic match"| FW["📐 urothelial-carcinoma-approach<br/><i>(disease framework)</i>"]
    R -.->|"NOT picked: entity is<br/>metastatic-focused, not stage III"| SKIP["🚫 urothelial-carcinoma entity<br/>+ drug pages"]

    FW --> GX{"Graph expand<br/>(principle-blind)"}
    GX -->|"lenses excluded as hubs →<br/>no entity pages added"| PIN

    subgraph PIN["② PIN — lenses linked by the framework"]
        L1["staging-and-resectability"]
        L2["biomarker-testing"]
        L3["tolerability-and-comorbidity"]
        L4["efficacy"]
        L5["adverse-events"]
    end

    FW --> CTX["📥 Context = 6 pages<br/>(framework + 5 lenses)<br/><i>user-aware resolution</i>"]
    PIN --> CTX

    CTX --> S2["③ SYNTHESIZE — Pro (call 2)<br/>answer strictly from wiki"]
    S2 -->|"scaffold present,<br/>but no stage III regimen facts"| INSUF["⚠️ INSUFFICIENT_WIKI_DATA"]

    INSUF --> S3["④ FALLBACK — Gemini grounded (call 3)<br/><b>wiki pages stay in context</b>"]
    CTX -.->|"framework + lenses steer<br/>the grounded answer"| S3

    S3 --> ANS["✅ Answer · origin = MIXED<br/>3 calls · 13.8k tokens<br/>reasoned clinical guidance,<br/>not a web dump"]

    classDef lens fill:#ecfdf5,stroke:#059669,color:#065f46;
    classDef frame fill:#eef2ff,stroke:#4f46e5,color:#3730a3;
    classDef skip fill:#fef2f2,stroke:#dc2626,color:#991b1b,stroke-dasharray:4 3;
    classDef out fill:#fffbeb,stroke:#d97706,color:#92400e;
    class L1,L2,L3,L4,L5 lens;
    class FW frame;
    class SKIP skip;
    class ANS,INSUF out;
```

## Why this is the design working

- **Division of labor.** The principle layer supplies the *reasoning structure*
  (always reachable, pinned); grounded search supplies the *current specifics*.
  The lenses are why the answer reads as judgment, not a list.
- **Principle-blind expansion** keeps the graph from bridging unrelated topics
  through a high-degree lens like `efficacy`.
- **Growth signal.** Falling back to `mixed` here exposed a real content gap:
  no curative-intent / muscle-invasive urothelial coverage in the wiki. That is
  exactly what the Grow agent should fill so the next such query answers
  wiki-first.
