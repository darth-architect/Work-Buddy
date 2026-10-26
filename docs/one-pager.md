# Work Buddy — One-Pager

@Ash · Oct 26, 2026

## What We've Built

Work Buddy is a multi-domain Slack bot that lets employees handle IT and sales tasks from one conversation instead of juggling five consoles. It's built on LangGraph and LangChain, reasoning with Ollama's `granite4.1:8b` model running entirely locally — nothing goes to an external LLM API. Through the Model Context Protocol (MCP), the same agent talks to four live backend systems:

- Okta — account status, password resets, unlocks
- Azure AD — directory and access lookups
- Salesforce — lead status and sales quota reporting
- Jira Service Management (JSM) — ticket creation and approval routing

Someone asks a question in plain English in Slack, Work Buddy decides which system(s) to call, runs the lookup or action, and replies in the same thread — no separate tickets or portals for everyday requests.

## Platform-Agnostic by Design

The agent itself — the reasoning, the conversation, the decision about which tool to call — is standard LangGraph and LangChain Python code. It doesn't know or care where its tools are hosted. Tools are exposed through the Model Context Protocol (MCP), an open standard, not a proprietary API tied to one vendor.

Today, n8n hosts the integration layer because it let us stand up and iterate on Okta, Azure AD, Salesforce, and JSM connections quickly. But that's a hosting choice, not an architectural dependency. The same agent would run unchanged against tool servers hosted on Replit, a plain Python microservice, or a serverless function — swap the MCP server underneath and the bot doesn't notice. There is no lock-in to n8n or to us as the only people who can extend it.

This matters for how we partner: whoever hosts the integration layer (us, you, or a mix) is a business decision, not a technical constraint.

## Built-In Governance

Not every request should happen instantly, and Work Buddy draws that line by design, not as an afterthought:

- **Tier 1 — sensitive actions.** New account creation, access grants, anything that changes who can get into what. These go through a ticket with manager approval and leave a full audit trail before anything is provisioned.
- **Tier 2 — everyday actions.** Status checks, account unlocks, lead and quota lookups. These run instantly from Slack — no ticket, no waiting, because the risk and reversibility don't call for one.

The agent decides which tier a request falls into based on what it's being asked to do, not who's asking — so the safety rails travel with the action, not the user.

## What the Attached Demos Show

Three short clips, each exercising a different part of the system:

1. **Okta account unlock (Tier 2, instant).** A locked-out user gets unlocked from Slack in seconds, with the OTP verification step included — no help desk ticket.
2. **Salesforce lead and quota lookup (Tier 2, instant).** Shows Work Buddy isn't IT-only — the same bot answers sales questions (open leads, quota attainment) by querying Salesforce directly from a Slack conversation.
3. **Full user onboarding (Tier 1, ticket + approval).** The end-to-end provisioning flow: a ticket is raised, routed for manager approval, and once approved, the new user is set up across the connected systems — with the audit trail Tier 1 requires.

## What's Next

- **Broader department coverage.** Extend beyond IT and sales into finance, HR, and other teams with their own repetitive, system-spanning requests.
- **Response consistency and formatting.** Tighten how the agent presents multi-record results and formats messages so every answer in Slack is clean and complete, not just correct.
- **More connectors.** Add systems as new partner and client environments call for them — the MCP architecture makes each new one additive, not a rewrite.
- **Production-grade deployment.** Move from a local, demo-oriented setup toward hosting and operational practices that fit a real rollout: reliability, monitoring, and access controls at that scale.

## How We Partner

There's no single required shape for this — we see three ways it can work, and they're not mutually exclusive:

1. **White-label it.** Run Work Buddy under your own name, for your own clients, with the branding and positioning you choose.
2. **Co-sell it.** Offer it alongside what you already provide, as a complementary capability rather than a replacement for anything in your current stack.
3. **Build it out together.** Partner with us to extend it into new systems and client environments — joint development rather than a handoff in either direction.

Because the underlying agent isn't tied to n8n or to any one hosting choice, each of these is a real option, not just a pitch.
