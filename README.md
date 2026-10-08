# Made with Nestlé AI Assistant

**An end-to-end AI knowledge assistant grounded in dynamically scraped [Made with Nestlé](https://www.madewithnestle.ca/) content.**

Built with **RAG · GraphRAG · Vector Search · Web Scraping · Azure OpenAI · React**

[Live Demo](#demo) · [Architecture](#architecture) · [Local Development](#local-development) · [Deployment](#deployment)

> **Status:** Active development. The repo currently includes a production-oriented Azure RAG chat foundation (forked from [Azure-Samples/azure-search-openai-demo](https://github.com/Azure-Samples/azure-search-openai-demo)). Nestlé-specific scraping, GraphRAG, and branded UI are being layered on top — see [Roadmap](#roadmap).

### Highlights

- **Dynamic knowledge ingestion** — scrape and refresh website content so answers stay current
- **RAG pipeline** — semantic retrieval over indexed Made with Nestlé pages
- **GraphRAG** — model relationships between products, recipes, ingredients, and other entities
- **Grounded generation** — responses linked back to relevant website sources
- **Cloud deployment** — real-time chat experience on Azure
- **Interactive UI** — production-oriented chatbot interface designed for the Made with Nestlé experience

---

## What I Built

An AI knowledge assistant that answers questions using real Made with Nestlé website content, instead of relying only on a static LLM knowledge cutoff.

Example interaction:

```text
User:
"What can I make with Carnation milk?"

AI:
[recipe suggestions grounded in retrieved pages]

Sources:
→ Nestlé recipe page
→ Product page
```

This project is positioned as a **portfolio AI engineering system** — raw web data → retrieval infrastructure → LLM → backend → frontend → Azure deployment — that originated from a Nestlé technical assessment.

---

## Demo

| Resource | Link |
| --- | --- |
| Live app | _Coming soon — Azure deployment URL_ |
| Architecture | [Architecture](#architecture) |
| Source site | [madewithnestle.ca](https://www.madewithnestle.ca/) |

Once deployed, expect:

- Multi-turn chat over Nestlé website content
- Citations / source links with answers
- Pop-out chatbot UI with customizable name and icon

---

## Architecture

```text
Made with Nestlé Website
          │
          ▼
     Web Scraper
          │
          ▼
 ┌───────────────────┐
 │ Content Processing│
 │ (chunk + metadata)│
 └─────────┬─────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
Vector Store   Knowledge Graph
(Azure AI      (GraphRAG /
 Search)        graph DB)
     │           │
     └─────┬─────┘
           ▼
       Retrieval
           │
           ▼
      Azure OpenAI
           │
           ▼
      AI Assistant
           │
           ▼
     User + Sources
```

This is an end-to-end AI system, not just an LLM wrapper: ingestion, indexing, retrieval, generation, and a chat UI.

### Dynamic knowledge pipeline

```text
Made with Nestlé
       ↓
Scheduled / on-demand crawl
       ↓
Content extraction (text, links, tables, images)
       ↓
Chunking + metadata
       ↓
Embedding generation
       ↓
Vector index (+ graph) update
       ↓
Chatbot retrieval → grounded answer
```

---

## AI / RAG Pipeline

1. **Ingest** website content via scraping
2. **Process** pages into chunks with metadata (URL, title, entity type, etc.)
3. **Embed** chunks and index them in Azure AI Search
4. **Retrieve** relevant passages for each user question (semantic / hybrid search)
5. **Generate** an answer with Azure OpenAI, constrained to retrieved context
6. **Cite** source URLs so users can verify claims

GraphRAG adds a second retrieval path for questions that need **relationships** (e.g. product ↔ recipe ↔ ingredient), not only similar text chunks.

### GraphRAG

A rule-based extractor turns the scraped pages into a graph of brands, products, recipes, ingredients and allergens (about 1,100 nodes and 8,000 edges). At question time, entities named in the question seed a neighbor expansion. For example, *"Which KIT KAT products may contain peanuts?"* intersects the KIT KAT brand with the peanuts allergen. The linked pages are pulled from the search index, and relationship facts with citations are added to the prompt. New entity types are one extractor function, and nodes or edges can be added through the `/graph` API without code changes. See [docs/graphrag.md](docs/graphrag.md).

### Chat widget

The site root shows a Made with Nestlé–styled landing page with a pop-out chat launcher (`app/frontend/src/components/ChatWidget`). The assistant's name, tagline, icon and colours come from `app/frontend/src/assistantConfig.ts` and can be overridden at build time with `VITE_ASSISTANT_NAME`, `VITE_ASSISTANT_TAGLINE`, `VITE_ASSISTANT_ICON_URL`, `VITE_ASSISTANT_PRIMARY_COLOR` and `VITE_ASSISTANT_ACCENT_COLOR`. The full-page chat is at `/#/chat`.

---

## Technology Stack

### AI / ML
RAG · GraphRAG · Azure OpenAI · embeddings · semantic/vector search · prompt & context construction · grounded responses

### Data
Web scraping · HTML/content extraction · text chunking · metadata extraction · document indexing · knowledge graph construction

### Backend
Python · Quart · REST API · retrieval pipeline · Azure SDKs · configuration via `azd` / environment variables

### Cloud / Deployment
Azure Container Apps · Azure OpenAI · Azure AI Search · Azure Blob Storage · Infrastructure as Code (Bicep)

### Frontend
React · TypeScript · Vite · chat UI · citations / source links · streaming-capable app shell

---

## Engineering Decisions

**Why RAG instead of fine-tuning?**  
Website content changes frequently. Retrieval lets the knowledge base update without retraining the underlying LLM.

**Why vector / semantic search?**  
Users ask questions in natural language that rarely match page wording exactly. Embeddings retrieve relevant passages by meaning.

**Why GraphRAG?**  
Some questions need multi-hop context — relationships between products, recipes, ingredients, and pages — which a flat chunk index alone does not model well.

**Why start from the Azure RAG sample?**  
It provides a battle-tested path for auth-ready chat, Azure OpenAI + AI Search wiring, IaC, and deployment. Custom Nestlé ingestion, GraphRAG, and UI are built on that foundation rather than reinventing cloud plumbing.

**Why Azure?**  
Matches the assessment deployment target and keeps OpenAI, search, storage, and hosting in one cloud with managed identity and `azd` workflows.

---

## Evaluation

Most student AI projects stop at “it works.” This project aims to measure retrieval and answer quality.

Planned metrics (fill in after running an eval set of ~30–50 questions):

```text
                    Baseline     RAG      GraphRAG
Answer relevance       —         —          —
Citation accuracy      —         —          —
Retrieval precision    —         —          —
```

Existing tooling in this repo (from the Azure sample) includes an `evals/` workflow that can be adapted for Nestlé-domain questions. See [docs/evaluation.md](docs/evaluation.md).

---

## Roadmap

| Area | Status |
| --- | --- |
| Azure RAG chat app (OpenAI + AI Search + React) | ✅ In repo (scaffold) |
| Azure deploy with `azd` | ✅ Supported |
| Citations / thought process UI | ✅ Supported by base app |
| Made with Nestlé web scraper + refresh pipeline | 🚧 Planned |
| Nestlé content index replacing sample Zava docs | 🚧 Planned |
| GraphRAG module (graph DB + relationship retrieval) | 🚧 Planned |
| User-editable graph nodes / relationships | 🚧 Planned |
| Branded pop-out chatbot UI over Nestlé screenshot | 🚧 Planned |
| Live Azure demo link | 🚧 Planned |
| Domain evaluation set + reported metrics | 🚧 Planned |

---

## Deployment

Provision Azure resources and deploy with the Azure Developer CLI:

```shell
azd auth login
azd env new
azd up
```

`azd up` provisions infrastructure and deploys the app (default host: Azure Container Apps). The endpoint URL is printed when deployment succeeds.

Useful follow-ups:

```shell
azd deploy          # code-only redeploy
azd down            # tear down resources (avoid idle cost)
```

More detail: [docs/azd.md](docs/azd.md) · [docs/azure_container_apps.md](docs/azure_container_apps.md) · [docs/deploy_troubleshooting.md](docs/deploy_troubleshooting.md)

> **Cost note:** Azure AI Search and OpenAI incur charges even at low usage. Tear down unused environments with `azd down`.

---

## Local Development

You can only run the app locally **after** a successful `azd up` (so Azure resources and env config exist).

**Prerequisites:** [Azure Developer CLI](https://aka.ms/azure-dev/install) · Python 3.10+ · Node.js 20+ · Git

```shell
# Backend + built frontend
./app/start.sh

# Optional: frontend HMR in a second terminal
cd app/frontend && BACKEND_PORT=50505 npm run dev
```

Open `http://127.0.0.1:50505` (or the Vite URL when using the frontend dev server).

More tips: [docs/localdev.md](docs/localdev.md)

### Project layout (high level)

```text
app/backend/     Quart API, RAG approaches, ingestion (prepdocslib)
app/frontend/    React + TypeScript chat UI
data/            Documents indexed into Azure AI Search
infra/           Bicep templates for Azure resources
evals/           Evaluation configs and results
docs/            Deep-dive guides (architecture, deploy, ingestion, …)
scripts/         Setup, ACL, and operational scripts
```

---

## Limitations

- Nestlé scraping, GraphRAG, and branded UI are not complete yet; the runnable app today is the Azure RAG foundation with sample documents under `data/`.
- Answer quality depends on indexed content coverage and retrieval settings.
- Live website scraping must respect site terms, robots rules, and rate limits.
- GraphRAG adds operational complexity (graph DB + sync with vector index).
- Cloud resources incur ongoing cost if left running.

---

## Future Work

- Production scrape schedule and incremental index updates
- Stronger entity extraction for products / recipes / ingredients
- Hybrid RAG + GraphRAG routing by query type
- Domain evaluation dashboard and regression checks
- Hardened production settings (auth, rate limits, monitoring) — see [docs/productionizing.md](docs/productionizing.md)

---

## Attribution

- **Origin:** Built as a portfolio project aligned with a Nestlé AI chatbot technical assessment for [Made with Nestlé](https://www.madewithnestle.ca/).
- **Foundation:** Application scaffold and Azure RAG patterns adapted from [Azure-Samples/azure-search-openai-demo](https://github.com/Azure-Samples/azure-search-openai-demo) (MIT).
- **Content:** Made with Nestlé website content belongs to Nestlé / respective rights holders; used here for the assessment and demonstration purposes only.

---

## License

See [LICENSE](LICENSE) for the terms inherited from the Azure sample foundation.
