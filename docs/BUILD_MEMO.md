# Build Memo — Made with Nestlé AI Assistant (3 Days)

**Purpose:** Short reference you can reopen each morning.  
**Mindset:** Ship an **extendable workflow**, not a perfect product.  
**North star (end of Day 3):** GitHub + live Azure URL + Nestlé answers with sources + GraphRAG module that others can extend via README.

---

## Operating rules

1. Prefer **pipelines you can re-run and extend** over one-off hacks.
2. Every Day-N feature should leave a clear **extension point** (script, module, API, or docs section).
3. If behind, cut polish — **never cut** live deploy + Nestlé RAG + citations.
4. Last 45 minutes of each day = **Done checklist only**. Green → commit → stop.

### Cut order (when time runs out)

1. Fancy eval dashboards  
2. UI polish  
3. Rich graph-editing UI (keep a minimal API + README)  
4. Full-site scrape (prefer recipes + products first)  
5. **Never cut:** Azure live link + Nestlé answers + source links  

---

## Extendable workflow (the real deliverable)

Build these **stages** so each can be improved later without rewriting the app:

```text
[1] Crawl / scrape     →  raw pages + URLs
[2] Extract / clean    →  text + metadata
[3] Chunk + embed      →  Azure AI Search index
[4] (optional) Graph   →  entities + relationships
[5] Retrieve           →  vector (± graph expand)
[6] Generate + cite    →  Azure OpenAI answer + sources
[7] Present            →  chat / pop-out widget
[8] Refresh            →  re-run [1]→[3] (±[4]) on demand
```

**Definition of “extendable” for this project**

| Stage | Minimum to ship | Extension point to leave behind |
| --- | --- | --- |
| Scrape | Recipes + products subset | `scripts/` or `app/backend/` scraper entrypoint + config (base URL, allowlist, rate limit) |
| Ingest | Files → `prepdocs` → Search | Documented command; folder convention for new pages |
| RAG | Existing chat approach over Nestlé index | Prompt/overrides unchanged; new data just reindexes |
| GraphRAG | Entities + edges + neighbor expand → chunks | Separate module + README “how to add entity types / edges” |
| Refresh | Manual `scrape → ingest` script | One documented workflow (cron later) |
| UI | Pop-out shell, name/icon, sources | Widget props / config for name, icon, theme |
| Deploy | `azd` live URL | README deploy + env notes |

---

## Day 1 — Nestlé data on the RAG workflow

**Theme:** Wire Nestlé content into the existing Azure RAG path. Prove retrieve → answer → cite.

### Build (in order)

| # | Chunk | Extendable outcome |
| --- | --- | --- |
| 1.1 | `azd up` — OpenAI + AI Search + app host | Reusable deploy path |
| 1.2 | Scraper MVP (allowlisted sections, rate limits) | Re-runnable crawl script + saved raw/clean output |
| 1.3 | Map scrape output → ingestible `data/` (or Nestlé subfolder) + `prepdocs` | Same ingest command for future pages |
| 1.4 | Smoke-test Nestlé questions; fix empty retrieval | RAG works on **your** index, not Zava samples |

**Do not do Day 1:** GraphRAG, branded widget, evals, perfect coverage of the whole site.

### Done checklist — rest when all true

- [x] Azure (or local-against-Azure) chat responds  
- [x] Nestlé pages are indexed (sample Zava docs are not the primary knowledge)  
- [x] Question like *“What can I make with Carnation milk?”* returns grounded content + **source links**  
- [x] Off-topic / unknown → mostly “I don’t know” / no invented Nestlé facts  
- [x] You can re-run **scrape → ingest** without rewriting code  
- [x] Day 1 committed on a feature branch  

**Rest signal:** Nestlé RAG loop works end-to-end and is re-runnable.

---

## Day 2 — GraphRAG module + UI shell

**Theme:** Add GraphRAG as a **module**, and a chatbot shell that looks intentional. Depth optional; extension docs required.

### Build (in order)

| # | Chunk | Extendable outcome |
| --- | --- | --- |
| 2.1 | Extract entities (product / recipe / ingredient / URL) from scraped pages | Batch job that can gain new entity types later |
| 2.2 | Graph store MVP (Neo4j / Cosmos Gremlin / Docker Neo4j — pick one) | Graph load script; schema written down |
| 2.3 | Retrieval path: query → neighbors → linked chunks → existing answer prompt | GraphRAG behind a clear interface / flag |
| 2.4 | Minimal “add node / relationship” API (or tiny form) | Users/devs can extend the graph without code |
| 2.5 | Pop-out chat UI: custom name + icon + Nestlé-style background | Configurable widget, not hard-coded one-off |

**Pragmatic GraphRAG:** neighbor expansion + chunk fetch. Not research-grade multi-agent GraphRAG.

### Done checklist — rest when all true

- [ ] Graph contains real Nestlé entities (at least product ↔ recipe)  
- [ ] At least one question path uses graph expansion then RAG  
- [ ] Add node/relationship works via API or simple UI  
- [ ] README/docs note: how to add entity types and edges  
- [ ] Pop-out chatbot with custom name/icon  
- [ ] Citations still work  
- [ ] Day 2 committed  

**Rest signal:** GraphRAG is a module others can extend; UI shell exists.

---

## Day 3 — Deploy, refresh workflow, docs, submit

**Theme:** Make the **workflow** obvious and the submission links reliable.

### Build (in order)

| # | Chunk | Extendable outcome |
| --- | --- | --- |
| 3.1 | Full redeploy; cold-load live URL | Stable demo endpoint |
| 3.2 | Documented refresh: scrape → ingest (± graph reload) | Dynamic-update story without pretending cron is magic |
| 3.3 | README: demo, architecture, setup, GraphRAG extension, limits | Portfolio + grader readable in 15s |
| 3.4 | Tiny eval table (15–20 Qs: relevance + citations) | Baseline you can grow in `evals/` |
| 3.5 | Bug bash on **deployed** app | Submit without obvious breaks |
| 3.6 | Submission pack: GitHub access + Azure link (+ optional short recording) | HR can click and test |

### Done checklist — rest / submit when all true

- [ ] Live Azure URL works without your laptop  
- [ ] README has setup, stack, GraphRAG how-to-extend, limitations, demo URL  
- [ ] Deployed chat answers Nestlé questions with sources  
- [ ] GraphRAG present + documented as extendable  
- [ ] Pop-out name/icon works on deploy  
- [ ] Refresh workflow written (manual is OK)  
- [ ] Repo pushed; both links shareable  

**Rest signal:** You would be fine if a reviewer only spent 5 minutes clicking around.

---

## Daily rhythm

```text
Morning     → highest-risk chunk first (deploy, scrape, graph wiring)
Afternoon   → remaining Day-N chunks
Last 45 min → Done checklist only
Green       → commit, stop. No “one more feature.”
```

---

## Branch map

| Day | Suggested branch | Merge when |
| --- | --- | --- |
| 1 | `feat/nestle-scrape-rag` | Day 1 checklist green |
| 2 | `feat/graphrag-ui` | Day 2 checklist green |
| 3 | `docs/nestle-ai-assistant-readme` (+ deploy commits) | Submit bar green |

Keep `main` deployable. Prefer merging a thin working workflow over a large unmerged perfect branch.

---

## Risk watch (especially Day 1)

| Risk | What to do fast |
| --- | --- |
| Azure OpenAI / Search quota or region | Switch region early; don’t lose half a day |
| JS-heavy or blocked pages | Sitemap + static/high-value pages first; expand scraper later |
| Empty index after ingest | Check blob + document count in Search before touching UI |
| Graph DB time sink | Cap setup at ~2h; ship neighbor-expand MVP |
| UI rabbit hole | Shell + name/icon + sources; polish only if ahead |

---

## Grader / recruiter lens (why this order)

| They care about | Satisfied by |
| --- | --- |
| Functionality | Nestlé answers + sources |
| Deployment | Live Azure link |
| Code / docs | README + re-runnable scripts + GraphRAG extension notes |
| Visual design | Pop-out widget, name/icon, Nestlé-framed UI |
| Creativity | Dynamic refresh workflow + graph relationships |

---

## Quick reopen prompts

- “What’s today’s only job?” → that day’s **Theme** + **Done checklist**  
- “Am I done?” → checklist, not vibes  
- “What do I cut?” → **Cut order** above  
- “What must remain extendable?” → the 8-stage workflow table  

---

## Attribution (for README later)

- Assessment origin: Nestlé / Made with Nestlé chatbot brief  
- Foundation: [Azure-Samples/azure-search-openai-demo](https://github.com/Azure-Samples/azure-search-openai-demo)  

---

*Last updated for a 3-day extendable-workflow plan. Revisit checklists at the end of each day; do not expand scope without cutting something else.*
