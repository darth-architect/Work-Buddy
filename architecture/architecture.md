# Architecture

## Overview

Work Buddy is a single LangGraph agent, fronted by Slack, that reasons over a small set of MCP tool servers instead of hard-coded integrations per system. The agent doesn't know or care where a tool is hosted — it only knows the tool's name, description, and schema, all discovered over MCP at startup.

```
                         ┌─────────────────────────┐
                         │          Slack           │
                         │   (slack_bolt, Socket    │
                         │         Mode)             │
                         └────────────┬─────────────┘
                                      │ message / event
                                      ▼
                         ┌─────────────────────────┐
                         │      LangGraph agent      │
                         │  (LangChain + Ollama       │
                         │   granite4.1:8b, local)    │
                         └────────────┬─────────────┘
                                      │ MultiServerMCPClient
                                      ▼
                 ┌───────────────────────────────────────┐
                 │        MCP tool servers (today: n8n)    │
                 ├───────────┬───────────┬────────┬────────┤
                 │   Okta    │ Azure AD  │Salesforce│  JSM  │
                 └───────────┴───────────┴────────┴────────┘
```

## Why this is platform-agnostic

The reasoning layer (LangGraph + LangChain) and the tool layer (MCP) are two separate, swappable pieces:

- The **agent** is ordinary Python. It has no n8n-specific code anywhere — it talks `MultiServerMCPClient` to whatever MCP server URLs are in its config.
- The **tool servers** happen to be hosted on n8n today, because n8n let us stand up and iterate on four system integrations quickly. Each one could instead be a plain Python MCP server on Replit, a serverless function, or anything else that speaks MCP — the agent would not need a single line changed.

This means hosting the integration layer is a business/operational decision (who hosts it, where, at what cost), not an architectural constraint.

## Governance tiers

Every tool is tagged with a tier, and the agent routes accordingly:

- **Tier 1 — sensitive actions** (new account creation, access grants): routed through a JSM ticket with manager approval and a full audit trail before anything executes.
- **Tier 2 — everyday actions** (status checks, unlocks, lookups): executed immediately from the Slack conversation, no ticket.

## Local model

The agent reasons with Ollama's `granite4.1:8b`, run entirely on local hardware — no conversation content or tool output is sent to an external LLM API.

## Current components

| Piece | File | Role |
|---|---|---|
| Slack integration | `bot/slack.py` | Socket Mode event handling, per-user conversation history, reset commands |
| Agent + MCP client | `bot/test_mcp.py` | Builds the LangGraph agent, wires up `MultiServerMCPClient`, holds the system prompt |
| MCP connectivity check | `bot/check_mcp.py` | Standalone script to verify the MCP servers are reachable |
| Slack id lookup | `bot/find_my_id.py` | One-off helper to find a Slack member id |
| Channel cleanup | `scripts/cleanup_slack.py`, `scripts/clearup_slack.py` | Clear stale scrollback before recording a demo |

## Near-term hardening

- Response formatting: a system-prompt rule to always list every record a tool returns (instead of letting the model re-filter already-correct results), and a ban on markdown tables (Slack's `mrkdwn` doesn't render them — numbered/bulleted lists instead).
- Moving from a single Docker container with no volume mounts to a proper CI/CD build.
