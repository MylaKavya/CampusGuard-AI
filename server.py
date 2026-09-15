"""
CampusGuard AI -- FastAPI MCP Tool Server + Web Chat Backend
Run: python server.py

Endpoints:
  GET  /            -> serves the browser chat UI
  POST /chat        -> conversational message handler (used by the web UI)
  GET  /health      -> health check
  GET  /tools       -> list all MCP tools
  POST /tools/{name}-> call a specific MCP tool
"""

import json
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Any, Dict, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tools.handlers import TOOL_HANDLERS, _read_db, get_stats, reset_db
from agent.workflow import WorkflowEngine, Intent
from agent.intake_agent import IntakeAgent
from agent.matching_agent import MatchingAgent

# ── Tool metadata ──────────────────────────────────────────────────────────────

TOOL_META = [
    {"name": "search_items",        "description": "Search lost/found items by description, category, location, or date range."},
    {"name": "report_lost_item",    "description": "Log a new lost item report. Auto-triggers match search."},
    {"name": "report_found_item",   "description": "Log a found item. Auto-triggers match search against lost reports."},
    {"name": "match_items",         "description": "Run AI semantic matching for a given item ID."},
    {"name": "notify_owner",        "description": "Send email/SMS alert to item owner or finder."},
    {"name": "get_item_status",     "description": "Get current status of a specific item report."},
    {"name": "update_item_status",  "description": "Advance item lifecycle: open -> matched -> claimed -> resolved."},
    {"name": "upload_item_image",   "description": "Upload and analyze an item image via Vision AI."},
    {"name": "get_stats",           "description": "Return live aggregate statistics from the database."},
    {"name": "reset_db",            "description": "Restore the database to the original seed state (demo reset)."},
]

# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="CampusGuard AI",
    description="Lost & Found Agentic Assistant — IBM Bob Hackathon",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Per-session agent state (single-user dev server) ──────────────────────────

_intake   = IntakeAgent()
_matching = MatchingAgent()
_workflow = WorkflowEngine()


# ── Chat logic (same as chat.py but returns strings instead of printing) ───────

def _format_search(result: dict) -> str:
    if result["found"] == 0:
        return ("No items found matching your description.\n"
                "Would you like to file a lost item report? Say \"I lost my ...\" to begin.")
    lines = [f"Found {result['found']} result(s):\n"]
    for i, r in enumerate(result["results"], 1):
        lines.append(
            f"{i}. [{r['id']}] {r['title']}  ({r['status'].upper()})\n"
            f"   Category: {r['category']}  |  Color: {r.get('color') or '?'}\n"
            f"   Location: {r['location']}\n"
            f"   Match score: {r['score']}"
        )
    lines.append("\nWant to claim one? Type: /claim ITEM-ID CLAIM-CODE YOUR-STU-ID")
    return "\n".join(lines)


def _format_status(result: dict) -> str:
    if "error" in result:
        return result["error"]
    loc = result.get("location") or {}
    loc_str = ", ".join(filter(None, [loc.get("building"), loc.get("room")]))
    lines = [
        f"Status Report -- {result['id']}",
        f"  Title    : {result['title']}",
        f"  Type     : {result['type'].upper()}",
        f"  Status   : {result['status'].upper()}",
        f"  Category : {result['category']}",
        f"  Location : {loc_str or 'N/A'}",
        f"  Reported : {result['date_reported'][:10]}",
    ]
    if result.get("best_match_id"):
        lines.append(f"  Best Match: {result['best_match_id']}  (score: {result['best_match_score']})")
    if result.get("claim_code"):
        lines.append(f"  Claim Code: {result['claim_code']}")
    if result.get("holding_location"):
        hl = result["holding_location"]
        lines.append(f"  Pickup At : {hl.get('building','')}, {hl.get('room','')}")
    return "\n".join(lines)


def process_message(user_text: str) -> str:
    """Core message router — mirrors chat.py logic, returns a plain string."""
    text = user_text.strip()

    # ── Slash commands ────────────────────────────────────────────────────────
    if text.startswith("/"):
        parts = text.split(None, 2)
        verb  = parts[0].lower()
        arg1  = parts[1] if len(parts) > 1 else ""
        arg2  = parts[2] if len(parts) > 2 else ""

        if verb == "/help":
            return (
                "Available commands:\n"
                "  /search <query>            Search for items\n"
                "  /status <ITEM-ID>          Check item status\n"
                "  /match  <ITEM-ID>          Run Matching Agent\n"
                "  /claim  <ID> <CODE> <STU>  Claim an item\n"
                "  /db                        Show all DB items\n"
                "  /stats                     Live database statistics\n"
                "  /reset                     Restore DB to seed state\n"
                "  /lost                      Start lost item form\n"
                "  /found                     Start found item form"
            )

        if verb == "/search":
            result = TOOL_HANDLERS["search_items"]({"query": arg1, "limit": 5})
            return _format_search(result)

        if verb == "/status":
            result = TOOL_HANDLERS["get_item_status"]({"item_id": arg1.upper()})
            return _format_status(result)

        if verb == "/match":
            db = _read_db()
            source = next((i for i in db["items"] if i["id"] == arg1.upper()), None)
            if not source:
                return f"Item {arg1.upper()} not found."
            results = _matching.run(item_id=arg1.upper(), threshold=0.40, top_k=5)
            return _matching.format_report(results, source.get("title", ""))

        if verb == "/claim":
            item_id    = arg1.upper()
            cp         = arg2.split()
            claim_code = cp[0] if cp else ""
            student_id = cp[1] if len(cp) > 1 else ""
            sr = TOOL_HANDLERS["get_item_status"]({"item_id": item_id})
            if "error" in sr:
                return sr["error"]
            if sr.get("claim_code") != claim_code:
                return f"Invalid claim code for {item_id}. Please check and try again."
            TOOL_HANDLERS["update_item_status"]({"item_id": item_id, "status": "claimed", "resolved_by": student_id})
            TOOL_HANDLERS["notify_owner"]({"student_id": student_id, "notification_type": "item_claimed", "item_id": item_id})
            return f"Item {item_id} successfully claimed! Notification sent."

        if verb == "/db":
            db = _read_db()
            lines = [f"Database: {len(db['items'])} items\n"]
            lines.append(f"{'ID':10}  {'TYPE':7}  {'STATUS':12}  TITLE")
            lines.append("-" * 55)
            for item in db["items"]:
                lines.append(f"{item['id']:10}  {item['type'].upper():7}  {item['status']:12}  {item['title']}")
            return "\n".join(lines)

        if verb == "/stats":
            s = get_stats()
            cat_lines = "\n".join(
                f"    {k:15s}: {v}" for k, v in s["by_category"].items()
            )
            return (
                f"CampusGuard AI -- Live Statistics\n"
                f"  Total reports  : {s['total_reports']}\n"
                f"  Lost reports   : {s['lost_reports']}  (open: {s['open_lost']})\n"
                f"  Found reports  : {s['found_reports']}  (holding: {s['holding']})\n"
                f"  Matched        : {s['matched']}\n"
                f"  Claimed        : {s['claimed']}\n"
                f"  Resolved       : {s['resolved']}\n"
                f"  Resolution rate: {s['resolution_rate_pct']}%\n"
                f"  Notifications  : {s['notifications_sent']}\n"
                f"  Claim requests : {s['claim_requests']}\n"
                f"\n  By Category:\n{cat_lines}"
            )

        if verb == "/reset":
            result = reset_db()
            _intake.reset()
            _workflow.reset()
            return result["message"]

        if verb == "/lost":
            return _intake.start("lost")

        if verb == "/found":
            return _intake.start("found")

        return "Unknown command. Type /help to see all commands."

    # ── Active intake session ─────────────────────────────────────────────────
    if _intake.active():
        resp = _intake.reply(text)
        return resp

    if _intake.done():
        if text.lower() in ("confirm", "yes", "submit", "ok", "y"):
            result  = _intake.submit()
            item_id = _intake.get_item_id()
            _intake.reset()
            if not result or not result.get("success"):
                return "Something went wrong. Please try again."
            db     = _read_db()
            source = next((i for i in db["items"] if i["id"] == item_id), {})
            match_results = _matching.run(item_id=item_id, threshold=0.40, top_k=3, auto_notify=True)
            report = _matching.format_report(match_results, source.get("title", ""))
            return f"Report saved! ID: {item_id}\n{result['message']}\n{report}"
        elif text.lower() in ("cancel", "no", "n", "discard"):
            _intake.reset()
            return "Report cancelled. How else can I help you?"
        else:
            return "Type 'confirm' to submit your report, or 'cancel' to discard it."

    # ── System signals from the UI ────────────────────────────────────────────
    if text == "__reset__":
        _intake.reset()
        _workflow.reset()
        return "__ok__"

    # ── Conversational routing ────────────────────────────────────────────────
    intent = _workflow.detect_intent(text)
    lower  = text.lower()

    if any(w in lower for w in ["hello", "hi", "hey", "start"]):
        return (
            "Welcome to CampusGuard AI!\n\n"
            "I have two AI agents ready:\n"
            "  [INTAKE AGENT]   -- step-by-step form to report lost or found items\n"
            "  [MATCHING AGENT] -- auto-matches items with a confidence score\n\n"
            "Try:\n"
            "  \"I lost my laptop\"\n"
            "  \"I found a backpack\"\n"
            "  \"Did anyone find my keys?\"\n"
            "  /help  for all commands"
        )

    if intent == Intent.REPORT_LOST:
        _workflow.transition(intent)
        return _intake.start("lost")

    if intent == Intent.REPORT_FOUND:
        _workflow.transition(intent)
        return _intake.start("found")

    if intent == Intent.SEARCH:
        result = TOOL_HANDLERS["search_items"]({"query": text, "limit": 5})
        return _format_search(result)

    if intent == Intent.STATUS_CHECK:
        m = re.search(r"ITEM-\d+", text, re.I)
        if m:
            result = TOOL_HANDLERS["get_item_status"]({"item_id": m.group(0).upper()})
            return _format_status(result)
        return "Please provide your item report ID (e.g. ITEM-001)."

    if intent == Intent.CLAIM:
        return ("To claim an item:\n"
                "  /claim ITEM-003 CLM-7X9K STU-10042")

    return ("I didn't understand that. Try:\n"
            "  \"I lost my laptop\"  |  \"I found a backpack\"\n"
            "  \"Did anyone find my keys?\"  |  /help")


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    """Serve the browser chat UI."""
    ui_path = Path(__file__).parent / "ui" / "index.html"
    if ui_path.exists():
        return HTMLResponse(ui_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h2>UI not found. Run the server and open /docs</h2>")


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat(body: ChatRequest):
    """Handle a chat message from the browser UI."""
    if not body.message.strip():
        return {"reply": "Please type a message."}
    try:
        reply = process_message(body.message)
        return {"reply": reply}
    except Exception as e:
        return {"reply": f"Error: {str(e)}"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "CampusGuard AI",
        "tools": [t["name"] for t in TOOL_META],
    }


@app.get("/stats")
def stats():
    """Live aggregate statistics for the dashboard / judges."""
    return get_stats()


@app.post("/reset")
def reset():
    """Restore the DB to seed state and clear agent sessions."""
    result = reset_db()
    _intake.reset()
    _workflow.reset()
    return result


@app.get("/tools")
def list_tools():
    return {"tools": TOOL_META}


class ToolCallRequest(BaseModel):
    arguments: Dict[str, Any] = {}


@app.post("/tools/{tool_name}")
def call_tool(tool_name: str, body: ToolCallRequest):
    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found.")
    try:
        result = handler(body.arguments)
        return {"result": result}
    except TypeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid arguments: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 50)
    print("  CampusGuard AI -- Web Chat + MCP Server")
    print("=" * 50)
    print("  Browser UI : http://localhost:3001")
    print("  API Docs   : http://localhost:3001/docs")
    print("  Health     : http://localhost:3001/health")
    print("=" * 50 + "\n")
    uvicorn.run("server:app", host="127.0.0.1", port=3001, reload=True)
