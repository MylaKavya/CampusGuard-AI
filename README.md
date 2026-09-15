<div align="center">

# CampusGuard AI

### Agentic Lost & Found Assistant for University Campuses

*Built with Python · FastAPI · IBM Bob · IBM watsonx.ai*

[![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.103+-green?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![IBM watsonx](https://img.shields.io/badge/IBM-watsonx.ai-blue?logo=ibm&logoColor=white)](https://www.ibm.com/watsonx)
[![IBM Bob](https://img.shields.io/badge/IBM-Bob-purple)](https://www.ibm.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## Problem Statement

Every semester, thousands of items are lost across university campuses — laptops, student ID cards, backpacks, keys, and more. Traditional lost & found systems are:

- **Passive** — students must physically visit a desk or check a bulletin board
- **Slow** — manual matching takes days or never happens at all
- **Disconnected** — security staff, students, and administration use different channels
- **Inefficient** — no automated alerts when a matching item is turned in

The result: most lost items are never reunited with their owners. Students lose expensive equipment and waste time filing reports with no feedback.

---

## Solution

**CampusGuard AI** is an intelligent, agentic lost & found assistant that automates the entire lifecycle — from intake to matching to claim resolution — through natural language conversation.

Students simply describe what they lost or found. Two specialist AI agents handle the rest:

1. **IntakeAgent** — guides students through a step-by-step conversational form, collecting all required fields (description, category, color, location, contact) before submitting the report.

2. **MatchingAgent** — automatically runs a multi-signal confidence scoring algorithm every time a new report is filed. When a high-confidence match (≥ 80%) is found, it generates a claim code and notifies the owner instantly.

No app to install. No desk to visit. No bulletin board to check.

---

## Key Features

| Feature | Description |
|---|---|
| **Natural Language Intake** | Students report items conversationally — no forms, no UI |
| **Guided Intake Agent** | Step-by-step field collector with validation and skippable optional fields |
| **Multi-Signal Matching** | 5-factor scoring: keyword overlap, category, color, location, recency |
| **Confidence Scoring** | Transparent signal breakdown with ASCII visualization |
| **Auto Notifications** | Email/SMS alert with claim code when a HIGH match is found |
| **MCP Tool Server** | FastAPI server exposing 8 tools to IBM Bob via the MCP protocol |
| **Full Item Lifecycle** | open → holding → matched → claimed → resolved |
| **Swagger API UI** | Interactive tool testing at `/docs` |

---

## Architecture Workflow

```
┌─────────────────────────────────────────────────────────┐
│                   Student / Security                     │
│              (Chat CLI  or  API Request)                 │
└───────────────────────┬─────────────────────────────────┘
                        │  Natural Language Input
                        ▼
┌─────────────────────────────────────────────────────────┐
│                  chat.py  —  Router                      │
│   Detects intent · Routes to the correct agent           │
│                                                          │
│  ┌───────────────────┐    ┌──────────────────────────┐  │
│  │   IntakeAgent     │    │     MatchingAgent         │  │
│  │ (intake_agent.py) │    │  (matching_agent.py)      │  │
│  │                   │    │                           │  │
│  │  Step-by-step     │    │  5-signal confidence      │  │
│  │  field collector  │───▶│  scorer — runs after      │  │
│  │  with validation  │    │  every report submit      │  │
│  └───────────────────┘    └──────────────────────────┘  │
│                                     │                    │
│              workflow.py            │  notify_owner()    │
│              (Intent Detection      │  if score >= 0.80  │
│               + State Machine)      ▼                    │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼  Tool Calls (MCP)
┌─────────────────────────────────────────────────────────┐
│           server.py  —  FastAPI MCP Tool Server          │
│                                                          │
│  search_items    report_lost_item   report_found_item    │
│  match_items     notify_owner       get_item_status      │
│  update_item_status                 upload_item_image    │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              data/db.json  —  Item Database              │
│  items · categories · campus_zones · notifications       │
└─────────────────────────────────────────────────────────┘
```

### Matching Algorithm

```
Final Score = (0.40 × keyword) + (0.25 × category) +
              (0.15 × color)   + (0.10 × location) + (0.10 × recency)

Confidence Bands:
  >= 0.80  →  HIGH      →  Auto-notify student + generate claim code
  0.60-0.79 → POSSIBLE  →  Surface as a suggestion to student
  0.40-0.59 → WEAK      →  Store silently, re-check on new submissions
  < 0.40   →  NO MATCH  →  Not surfaced
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| Web Framework | FastAPI + Uvicorn |
| Agent Runtime | IBM Bob (Agentic Mode) |
| LLM | IBM watsonx.ai — Granite 13B Chat |
| Embeddings | IBM Slate 125M English Retriever |
| Tool Protocol | MCP (Model Context Protocol) |
| Database | JSON file (prototype) → Cloudant (production) |
| Notifications | Console mock → Nodemailer / Twilio (production) |

---

## Project Structure

```
campusguard-ai/
│
├── chat.py                  # CLI chat runner — entry point
├── server.py                # FastAPI MCP tool server
├── requirements.txt
├── .env.example             # Environment variable template
│
├── agent/
│   ├── intake_agent.py      # IntakeAgent: guided field collection
│   ├── matching_agent.py    # MatchingAgent: 5-signal confidence scoring
│   ├── workflow.py          # Intent detection + state machine
│   └── system_prompt.py     # Agent persona & instruction set
│
├── tools/
│   └── handlers.py          # 8 MCP tool implementations
│
├── data/
│   └── db.json              # Mock database (items, zones, notifications)
│
├── ARCHITECTURE.md          # Full system design document
└── TEST_SCENARIOS.md        # 3 end-to-end hackathon test scenarios
```

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-username/campusguard-ai.git
cd campusguard-ai
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment (optional — for live LLM)

```bash
cp .env.example .env
# Edit .env and add your IBM watsonx.ai credentials
```

### 4a. Run the interactive chat (no API key needed)

```bash
python chat.py
```

### 4b. Run the MCP API server

```bash
python server.py
```

Then open in your browser:
- **http://localhost:3001/health** — health check
- **http://localhost:3001/docs** — Swagger UI to test all 8 tools
- **http://localhost:3001/tools** — list all registered tools

---

## Usage Examples

```
You: I lost my laptop

CampusGuard: >>> INTAKE AGENT: Reporting a Lost Item <<<
             Q1/10  What did you lose? Give it a short title:
```

```
You: Did anyone find my backpack near the library?

CampusGuard: SEARCH: Found 2 result(s):
             1. [ITEM-002] Blue Jansport Backpack  (HOLDING)
                Location: Student Union, Cafeteria Entrance
                Score: 100%
```

```
/match ITEM-010

  MATCHING AGENT: Found 1 candidate(s) for 'Black Dell XPS 15 Laptop'
  Match: [ITEM-010] <--> [ITEM-011]
  Signal Breakdown:
    Keyword  [######----]   58.3%  x0.40
    Category [##########]  100.0%  x0.25
    Color    [##########]  100.0%  x0.15
    Location [##########]  100.0%  x0.10
    Recency  [##########]  100.0%  x0.10
    ------------------------------------------------
    FINAL    [########--]   83.3%  -> HIGH
  >>> Claim Code: CLM-TVK8 <<<
```

---

## Chat Commands

| Command | Description |
|---|---|
| `I lost my ...` | Start the lost item intake form |
| `I found a ...` | Start the found item intake form |
| `Did anyone find my ...` | Search the database |
| `/status ITEM-001` | Check item report status |
| `/match ITEM-001` | Run the Matching Agent manually |
| `/claim ITEM-003 CLM-7X9K STU-10042` | Claim a matched item |
| `/db` | Display all items in the database |
| `/help` | Show all available commands |
| `/quit` | Exit |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/tools` | List all 8 MCP tools |
| `POST` | `/tools/search_items` | Search items by description/filters |
| `POST` | `/tools/report_lost_item` | Submit a lost item report |
| `POST` | `/tools/report_found_item` | Submit a found item report |
| `POST` | `/tools/match_items` | Run confidence matching |
| `POST` | `/tools/notify_owner` | Send match notification |
| `POST` | `/tools/get_item_status` | Retrieve item status |
| `POST` | `/tools/update_item_status` | Advance item lifecycle |
| `POST` | `/tools/upload_item_image` | Upload and tag item image |

All `POST` endpoints accept:
```json
{ "arguments": { ...tool-specific fields... } }
```

---

## Test Scenarios

Three realistic end-to-end scenarios are documented in [`TEST_SCENARIOS.md`](TEST_SCENARIOS.md):

| # | Scenario | Result |
|---|---|---|
| 1 | Student reports a lost Dell laptop | `ITEM-010` created, status: `open` |
| 2 | Security registers a found Dell laptop | `ITEM-011` created, status: `holding` |
| 3 | Automated matching fires | **83.3% HIGH confidence**, claim code generated, owner notified |

---

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `WATSONX_API_KEY` | IBM watsonx.ai API key | For live LLM mode |
| `WATSONX_PROJECT_ID` | watsonx.ai project ID | For live LLM mode |
| `WATSONX_URL` | watsonx.ai service URL | Optional |
| `LLM_MODEL_ID` | Model ID (default: `ibm/granite-13b-chat-v2`) | Optional |
| `MCP_SERVER_PORT` | Tool server port (default: `3001`) | Optional |

> The system runs fully in **DEMO mode** without any API keys using rule-based responses.

---

## Roadmap

- [ ] Integrate IBM watsonx.ai Granite LLM for full conversational responses
- [ ] Add image upload + CLIP-based visual matching
- [ ] Replace JSON file DB with IBM Cloudant / MongoDB
- [ ] Add Twilio SMS and email notifications
- [ ] Build a React + Tailwind web frontend
- [ ] Deploy to IBM Code Engine

---

## License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

Built for the **IBM Bob Hackathon** &nbsp;|&nbsp; Made with IBM Bob

</div>
