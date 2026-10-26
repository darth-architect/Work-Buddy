# Work Buddy (Slack-Bot)

A multi-domain Slack bot that lets employees handle IT and sales tasks from one conversation — account unlocks, lead/quota lookups, full user onboarding — instead of juggling separate consoles.

See [`docs/one-pager.md`](docs/one-pager.md) for the business summary, or [`architecture/architecture.md`](architecture/architecture.md) for how it's built.

## Stack

- **Agent**: [LangGraph](https://github.com/langchain-ai/langgraph) + [LangChain](https://github.com/langchain-ai/langchain), reasoning with [Ollama](https://ollama.com)'s `granite4.1:8b`, running entirely locally.
- **Tools**: exposed via the [Model Context Protocol](https://modelcontextprotocol.io) (MCP) — platform-agnostic, not tied to any one host. Today the MCP servers are hosted on n8n for speed of iteration; see the architecture doc for why that's a hosting choice, not a dependency.
- **Interface**: Slack, via `slack_bolt` (Socket Mode).
- **Connected systems**: Okta, Azure AD, Salesforce, Jira Service Management (JSM).

## Repo layout

```
bot/            core agent + Slack integration code
scripts/        one-off/maintenance scripts (Slack channel cleanup, id lookup, MCP connectivity checks)
docs/           the one-pager sent to partners
usecases/       one doc per capability — problem, workflow, architecture, tech stack
architecture/   overall system architecture
demo_videos/    recorded walkthroughs of each use case
screenshots/    supporting screenshots
```

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

## Related

[`IAM-Automation-Workflow`](https://github.com/darth-architect/IAM-Automation-Workflow) holds earlier, Okta-focused identity-automation design docs. The account-unlock flow actually shipped here uses OTP verification via Okta + Slack rather than the security-question design sketched there — see `usecases/account-unlock.md` in this repo for what's actually running.
