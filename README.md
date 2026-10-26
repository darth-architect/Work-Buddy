# Work Buddy

A multi-domain Slack bot that lets employees handle IT and sales tasks from one conversation — account unlocks, password resets, DL management, app access provisioning, Salesforce lead/quota lookups, and full user onboarding — instead of juggling separate consoles.

See [`docs/one-pager.md`](docs/one-pager.md) for the business summary, or [`architecture/architecture.md`](architecture/architecture.md) for how it's built.

## Stack

- **Agent**: [LangGraph](https://github.com/langchain-ai/langgraph) + [LangChain](https://github.com/langchain-ai/langchain), reasoning with [Ollama](https://ollama.com)'s `granite4.1:8b`, running entirely locally.
- **Tools**: exposed via the [Model Context Protocol](https://modelcontextprotocol.io) (MCP) — platform-agnostic, not tied to any one host. Today the MCP servers are hosted on n8n for speed of iteration; see the architecture doc for why that's a hosting choice, not a dependency.
- **Interface**: Slack, via `slack_bolt` (Socket Mode).
- **Connected systems**: Okta, Azure AD, Salesforce, Jira Service Management (JSM).

## Repo layout

```
bot/            core agent + Slack integration code
scripts/        maintenance scripts (Slack channel cleanup, id lookup, MCP connectivity checks)
docs/           the one-pager sent to partners
architecture/   overall system architecture
workflows/      one folder per capability — usecase doc, demo video, screenshots
screenshots/    general app screenshots not tied to one workflow
```

## Workflows

| Workflow | Status | Folder |
|---|---|---|
| Okta account unlock | shipped (OTP-based; see note in its usecase doc) | [`workflows/account-unlock`](workflows/account-unlock) |
| Salesforce lead & quota lookup | shipped | [`workflows/salesforce-lead-quota-lookup`](workflows/salesforce-lead-quota-lookup) |
| Full user onboarding | shipped | [`workflows/user-onboarding`](workflows/user-onboarding) |
| Password reset | design doc only | [`workflows/password-reset`](workflows/password-reset) |
| DL management | design doc only | [`workflows/dl-management`](workflows/dl-management) |
| Application access provisioning (Okta) | design doc only | [`workflows/application-access-provisioning-okta`](workflows/application-access-provisioning-okta) |

Each workflow folder holds a `usecase.md` (problem, solution, workflow, architecture, tech stack), and a `demo_video.mp4` + `screenshots/` where recorded.

## Running it locally

1. `python -m venv venv && source venv/bin/activate`
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in the real tokens/URLs (never commit `.env`).
4. `python bot/slack.py`

Or via Docker: `docker build -t slack-bot . && docker run --env-file .env.docker slack-bot` (no volume mounts — rebuild the image after every code change).

## Maintenance

Before a demo/recording session, clear stale scrollback from the bot's App Home DM:

```
python scripts/clearup_slack.py   # wipes the bot's own messages
python scripts/cleanup_slack.py   # wipes your own messages (needs SLACK_USER_TOKEN)
```

## History

This repo merges the full commit history of two earlier repos: `IAM-Automation-Workflow` (the original identity-automation design docs) and `Slack-Bot` (the actual agent build). Both remain on disk at `~/Documents/IAM-Automation-Workflow` and `~/Documents/Slack-Bot` for reference; this repo supersedes them going forward.
