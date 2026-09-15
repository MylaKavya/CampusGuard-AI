# IBM Bob Integration in CampusGuard AI

This document outlines how **IBM Bob** was leveraged to build the core agentic workflow of CampusGuard AI.

## Architecture Overview
CampusGuard AI uses IBM Bob as its central Agent Runtime layer to process natural language conversations from students, manage session context, and execute automated tool calls.

## Key Features & Workflows Powered by IBM Bob:
- **Intent Detection & Routing:** Automatically distinguishes whether a student is reporting a lost item, reporting a found item, searching records, or checking claim status.
- **MCP Tool Calling:** Executes backend operations dynamically via custom tool definitions (`search_items`, `report_lost_item`, `report_found_item`, `match_items`, `notify_owner`).
- **Semantic & Vision Matching:** Coordinates multi-signal confidence scoring to automatically match lost reports with found items.
- **System Guardrails:** Enforces privacy rules and maintains an empathetic, helpful campus assistant persona.
