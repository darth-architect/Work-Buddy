import asyncio
import contextvars
import os
from typing import Optional
import json
from typing import Any, Optional

from dotenv import load_dotenv
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from pydantic import create_model
from contextvars import ContextVar

current_user_message: ContextVar[str] = ContextVar("current_user_message", default="")

load_dotenv()

# Maps requestTypeKey -> ordered list of (keywords, plain-English intent description).
# First rule whose keywords appear in the user's message wins. The description is NOT
# assumed to match a form's exact choice label - the model still picks whichever
# baseFields choice most closely matches this description (per step 5 of the prompt).
INTENT_HINTS = {
    "okta_app_mgmt": [
        (["remove access", "revoke access", "no longer need access", "take away my access",
          "deprovision", "cut off access", "remove my access"],
         "Access Deprovisioning - the user wants an application access REMOVED"),
        (["need access", "want access", "requesting access", "request access",
          "give me access", "grant access", "add access", "need application access"],
         "Access Provisioning - the user wants an application access GRANTED"),
    ],
    "okta_user_mgmt": [
        (["delete user", "remove user", "deactivate user", "offboard", "disable user"],
         "deleting or deactivating an existing user account"),
        (["create user", "new user", "onboard", "new hire", "add a user"],
         "creating a brand new user account"),
        (["update user", "modify user", "change user", "edit user"],
         "modifying an existing user's details"),
    ],
    "azure_user_mgmt": [
        (["delete user", "remove user", "deactivate user", "offboard", "disable user"],
         "deleting or deactivating an existing user account"),
        (["create user", "new user", "onboard", "new hire", "add a user"],
         "creating a brand new user account"),
        (["update user", "modify user", "change user", "edit user"],
         "modifying an existing user's details"),
    ],
    "okta_group_mgmt": [
        (["delete group", "remove group", "disband group"],
         "deleting an existing group"),
        (["create group", "new group", "set up a group"],
         "creating a brand new group"),
        (["add to group", "add member", "remove from group", "remove member",
          "update group", "modify group"],
         "modifying an existing group's membership or settings"),
    ],
    "azure_group_mgmt": [
        (["delete group", "remove group", "disband group"],
         "deleting an existing group"),
        (["create group", "new group", "set up a group"],
         "creating a brand new group"),
        (["add to group", "add member", "remove from group", "remove member",
          "update group", "modify group"],
         "modifying an existing group's membership or settings"),
    ],
}


def detect_intent_hint(request_type_key, message: str) -> str | None:
    rules = INTENT_HINTS.get(request_type_key)
    if not rules:
        return None
    text = message.lower()
    for keywords, description in rules:
        if any(kw in text for kw in keywords):
            return description
    return None

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "granite4.1:8b")
OLLAMA_BASE_URL= os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
SALESFORCE_MCP_URL = os.getenv("SALESFORCE_MCP_URL", os.getenv("N8N_MCP_URL", "http://localhost:5678/mcp/trigger-workflows"))
SALESFORCE_MCP_TOKEN = os.getenv("SALESFORCE_MCP_TOKEN", os.getenv("N8N_MCP_TOKEN"))
AZURE_MCP_URL = os.getenv("AZURE_MCP_URL", "http://localhost:5678/mcp/azure-trigger")
AZURE_MCP_TOKEN= os.getenv("AZURE_MCP_TOKEN")
OKTA_MCP_URL = os.getenv("OKTA_MCP_URL", "http://localhost:5678/mcp/trigger-okta")
OKTA_MCP_TOKEN = os.getenv("OKTA_MCP_TOKEN")
JSM_MCP_URL= os.getenv("JSM_MCP_URL", "http://localhost:5678/mcp/jsm-ticket-creation")
JSM_MCP_TOKEN= os.getenv("JSM_MCP_TOKEN")  

# holds the *real, verified* identity of whoever is talking to the bot right now
# for now we set this by hand for console testing; later the Slack layer sets it
# per incoming message based on the real Slack user
current_user_email = contextvars.ContextVar("current_user_email", default=None)

JSON_TYPE_MAP = {
    "string": str,
    "number": float,
    "integer": int,
    "boolean": bool,
}

VALID_REQUEST_TYPE_KEYS = {
    "azure_group_mgmt", "azure_user_mgmt", "okta_app_mgmt", "okta_user_mgmt", "okta_group_mgmt",
}

def wrap_tool_validate_request_type_key(tool):
    original_coroutine = tool.coroutine

    async def wrapped(**kwargs):
        key = kwargs.get("requestTypeKey")
        if key not in VALID_REQUEST_TYPE_KEYS:
            return (
                f'Error: "{key}" is not a valid requestTypeKey. '
                f'You must use exactly one of: {", ".join(sorted(VALID_REQUEST_TYPE_KEYS))}. '
                f'Pick the closest match to what the user asked for and call this tool again with that exact value.'
            )
        return await original_coroutine(**kwargs)

    tool.coroutine = wrapped
    return tool

PLATFORM_AMBIGUOUS_KEYS = {"okta_user_mgmt", "azure_user_mgmt", "okta_group_mgmt", "azure_group_mgmt"}
PLATFORM_KEYWORDS = ["okta", "azure", "azure ad", "aad", "entra", "active directory"]

def message_mentions_platform(message: str) -> bool:
    text = message.lower()
    return any(kw in text for kw in PLATFORM_KEYWORDS)

def wrap_tool_require_platform_clarity(tool):
    original_coroutine = tool.coroutine

    async def wrapped(**kwargs):
        key = kwargs.get("requestTypeKey")
        if key in PLATFORM_AMBIGUOUS_KEYS and not message_mentions_platform(current_user_message.get()):
            return (
                f'Error: before calling Call_Get_Form_Fields_ with "{key}", you must first ask the user '
                f'plainly whether this is for Okta or Azure AD, since their message did not name a platform. '
                f'Do not guess or default to one. Ask the question in your reply and wait for their answer - '
                f'do not call this tool again until they specify.'
            )
        return await original_coroutine(**kwargs)

    tool.coroutine = wrapped
    return tool

def wrap_tool_hide_identity(mcp_tool, identity_field="userEmail"):
    schema = mcp_tool.args_schema or {}
    props = schema.get("properties", {})
    has_identity_field = identity_field in props

    field_defs = {}
    for name, spec in props.items():
        if name == identity_field:
            continue
        json_type = spec.get("type")
        if json_type == "string":
            # Some models pass a structured object/array instead of a JSON string for
            # string-typed params - accept either shape here and coerce below, rather
            # than letting pydantic reject it before our code ever sees it.
            py_type = Any
        else:
            py_type = JSON_TYPE_MAP.get(json_type, str)
        field_defs[name] = (Optional[py_type], None)

    ArgsModel = create_model(mcp_tool.name + "_Args", **field_defs)

    async def wrapped(**kwargs):
        full_args = {}
        for k, v in kwargs.items():
            if v is None:
                continue
            spec = props.get(k, {})
            if spec.get("type") == "string" and not isinstance(v, str):
                v = json.dumps(v)
            full_args[k] = v

        if has_identity_field:
            email = current_user_email.get()
            if not email:
                return "Error: no verified user identity available for this request. Refusing to call this tool."
            full_args[identity_field] = email

        return await mcp_tool.ainvoke(full_args)

    return StructuredTool(
        name=mcp_tool.name,
        description=mcp_tool.description,
        args_schema=ArgsModel,
        coroutine=wrapped,
    )

def wrap_tool_inject_intent_hint(tool):
    original_coroutine = tool.coroutine

    async def wrapped(**kwargs):
        result = await original_coroutine(**kwargs)
        request_type_key = kwargs.get("requestTypeKey")
        description = detect_intent_hint(request_type_key, current_user_message.get())
        if description:
            hint = (
                f'\n\nSYSTEM_HINT: The user\'s exact wording strongly indicates they mean: '
                f'"{description}". Do NOT ask them to choose the base action - find the baseFields '
                f'choice whose label most closely matches this intent, use it automatically, and go '
                f'straight to asking for the fields in that matching branch.'
            )
            result = (result if isinstance(result, str) else str(result)) + hint
        return result

    tool.coroutine = wrapped
    return tool

def wrap_tool_validate_request_type_key(tool):
    original_coroutine = tool.coroutine

    async def wrapped(**kwargs):
        key = kwargs.get("requestTypeKey")
        if key not in VALID_REQUEST_TYPE_KEYS:
            return (
                f'Error: "{key}" is not a valid requestTypeKey. '
                f'You must use exactly one of: {", ".join(sorted(VALID_REQUEST_TYPE_KEYS))}. '
                f'Pick the closest match to what the user asked for and call this tool again with that exact value.'
            )
        return await original_coroutine(**kwargs)

    tool.coroutine = wrapped
    return tool

def build_mcp_config():
    config = {
        "salesforce": {
            "url": SALESFORCE_MCP_URL,
            "transport": "streamable_http",
            "headers": {"Authorization": "Bearer " + SALESFORCE_MCP_TOKEN},
        }
    }
    if OKTA_MCP_TOKEN:
        config["okta"] = {
            "url": OKTA_MCP_URL,
            "transport": "streamable_http",
            "headers": {"Authorization": "Bearer " + OKTA_MCP_TOKEN},
        }
    if AZURE_MCP_TOKEN:
        config["azure"] = {
            "url": AZURE_MCP_URL,
            "transport": "streamable_http",
            "headers": {"Authorization": "Bearer " + AZURE_MCP_TOKEN},
        }
    if JSM_MCP_TOKEN:
            config["jsm"] = {
                "url": JSM_MCP_URL,
                "transport": "streamable_http",
                "headers": {"Authorization": "Bearer " + JSM_MCP_TOKEN},
            }
    return config

SYSTEM_PROMPT = """You are a Slack bot that helps employees with self-service Azure, Salesforce and Okta requests.

Ticket-gated actions (READ THIS FIRST): some requests are higher-risk and must never be performed directly - instead you submit a ticket that a human approver reviews before anything happens. These are: creating or deleting an Okta or Azure AD user, creating or modifying an Okta or Azure AD group, and assigning or removing an Okta application for a user (trigger phrases include: "need access to an application", "add me/someone to an app", "remove access from an app", "create a new Okta/Azure user", "delete a user", "create or modify a group"). The MOMENT you recognize a request like this, your very next action must be calling Call_Get_Form_Fields_ with the matching requestTypeKey - azure_group_mgmt, azure_user_mgmt, okta_app_mgmt, okta_user_mgmt, or okta_group_mgmt. Do NOT ask the user any of your own questions first (not which application, not who it's for, not what type of access) - that tool call tells you exactly which questions to ask, and inventing your own questions first wastes the user's time and often asks for things the real form doesn't even need. Only start asking the user anything after this tool has responded. Every other supported self-service request (password reset, MFA reset, profile updates, account unlock, etc.) continues to use the direct action tools as before, with no ticket involved.

Formatting: use Slack mrkdwn, not GitHub markdown. Bold is a single asterisk (*bold*), never double asterisks. Never use markdown tables. Use short paragraphs or bullet lists instead.

Identity: every DIRECT ACTION tool you call (password reset, profile update, account unlock, MFA changes, etc.) only ever acts on the real, verified person sending you this message, regardless of any other name or email they mention. If someone asks you to look up or change something for another person using one of these direct action tools, say plainly that you can only act on their own account. This restriction does NOT apply to ticket creation - many tickets are legitimately submitted on behalf of someone else.

Never invent, guess, or use a placeholder value for any tool argument. If the user's message doesn't contain a piece of information a tool needs, do not call the tool yet - ask the user for the missing information first, in plain language, and only call the tool once they've given you the real value in this conversation.

Platform ambiguity: some self-service actions exist for both Okta and Azure AD (account unlock, password reset, MFA changes, profile updates). If the user's request could apply to either system and they have not said which one they mean, ask them plainly whether they mean Okta or Azure AD before calling either tool.

Ticket requests are frequently made on behalf of someone else - for example IT staff or a manager requesting application access for a colleague or new hire. This is completely normal and expected. Never refuse a ticket request, and never ask the person to "confirm they're the target user," just because it's for someone other than the person talking to you. When the form asks for a "User Email" or similar target-user field, use exactly the email the person gives you for that field.

Ticket-creation process:
1. As soon as you recognize the request falls into one of the five categories above, determine the matching requestTypeKey and call Call_Get_Form_Fields_ immediately with it. Always call this fresh for each new ticket in this conversation. Platform check: user management (okta_user_mgmt vs azure_user_mgmt) and group management (okta_group_mgmt vs azure_group_mgmt) both exist on Okta and Azure AD. If the user's message doesn't say which platform they mean (no mention of Okta, Azure, Azure AD, AAD, or Entra), do not guess or default to either one - ask them plainly "Is this for Okta or Azure AD?" and wait for their answer before calling Call_Get_Form_Fields_. Application access requests are Okta-only (okta_app_mgmt) and never need this question.
2. Look at baseFields first. If the user's message already makes clear which base answer applies, use that directly - don't re-ask. This includes natural phrasing, not just exact matches: "need access", "want access", "requesting access to X" all imply Access Provisioning; "remove access", "revoke access", "no longer need access to X", "take away my access" all imply Access Deprovisioning. Only ask the baseFields question when the user's intent genuinely isn't clear from what they said.
3. Once you know the base answer, use ONLY the one branch whose triggerChoiceLabel matches it. Never combine, list, or mix fields or choices from a branch that doesn't apply. If the user asks a general question like "what applications can I request" before telling you provisioning vs deprovisioning, just list the choices once (they describe the same applications either way) and ask which action they want, rather than repeating the same list under two separate headings.
4. For each of that branch's fields, use any answer the user has already given in their message; ask for anything still missing, one item at a time, in plain language - never mention internal terms like "fields", "JSM", "branches", or "questionId".
5. When matching a user's free-text answer to a choice-type field, pick the choice whose label most closely matches what they said. If nothing matches clearly, list the available choices and ask them to pick one - never guess an id.
6. Once every required field has a real answer, read them back to the user in plain language and ask them to confirm before submitting.
7. Only after they confirm, call Call_Create_JSM_Ticket_ with requestTypeKey and answersJson. answersJson MUST be a single JSON-encoded STRING, never a plain object - and it must include an entry for EVERY question you asked, including the base question (e.g. questionId "1" for "What would you like to do?") in addition to the branch-specific fields. Never omit the base question's answer just because it was only used to pick the branch - it still needs to be submitted. Build the array of answers, then serialize it to a string before passing it as the argument. Each element needs: questionId (exact string ID from Call_Get_Form_Fields_), label (the exact question label text, copied exactly as Call_Get_Form_Fields_ gave it for that question), type (copy exactly, e.g. “cd” or “te”), and either choiceId + choiceLabel (for choice fields - choiceId must come from that exact question’s own choices list) or text (for text fields):"[{\"questionId\":\"1\",\"label\":\"What would you like to do?\",\"type\":\"cd\",\"choiceId\":\"1\",\"choiceLabel\":\"Access Provisioning\"},{\"questionId\":\"13\",\"label\":\"User Email\",\"type\":\"te\",\"text\":\"jdoe@company.com\"},{\"questionId\":\"19\",\"label\":\"Application\",\"type\":\"cd\",\"choiceId\":\"1\",\"choiceLabel\":\"Salesforce.com\"}]"
8. If a tool call returns an error, read what it says is wrong and fix exactly that in your next call - do not abandon the attempt or re-ask the user to reconfirm information they already gave you.
9. Never call the exact same tool with the exact same arguments twice in a row after it has already failed - you must change something based on the error message before retrying.
10. After the ticket is created, tell the user their request has been submitted for approval, include the ticket key if present in the result, and make clear the change has NOT been made yet and will only happen once approved."""

async def build_agent():
    client = MultiServerMCPClient(build_mcp_config())
    raw_tools = await client.get_tools()
    tools = [wrap_tool_hide_identity(t) for t in raw_tools]

    for t in tools:
        if t.name in ("Call_Get_Form_Fields_", "Call_Create_JSM_Ticket_"):
            wrap_tool_validate_request_type_key(t)
        if t.name == "Call_Get_Form_Fields_":
            wrap_tool_require_platform_clarity(t)
            wrap_tool_inject_intent_hint(t)

    print("Loaded", len(tools), "tool(s):", [t.name for t in tools])

    llm = ChatOllama(model=OLLAMA_MODEL, temperature=0, base_url=OLLAMA_BASE_URL, num_ctx=8192)
    return create_react_agent(llm, tools=tools, prompt=SYSTEM_PROMPT)


async def main():
    agent = await build_agent()

    print("Salesforce bot - using", OLLAMA_MODEL, ". Type 'exit' to quit.\n")
    history = []
    while True:
        user_input = input("You: ")
        if user_input.strip().lower() in ("exit", "quit"):
            break
        current_user_message.set(user_input)          # <-- add this line
        history.append({"role": "user", "content": user_input})
        current_user_message.set(" ".join(m["content"] for m in history if m["role"] == "user"))

        result = await agent.ainvoke({"messages": history})

        for msg in result["messages"]:
            tool_calls = getattr(msg, "tool_calls", None)
            if tool_calls:
                print(f"[{msg.type}] requested tool calls:", tool_calls)
            elif msg.type == "tool":
                print(f"[tool result] {msg.content}")

        ai_message = result["messages"][-1]
        print("Bot:", ai_message.content, "\n")
        history.append({"role": "assistant", "content": ai_message.content})


if __name__ == "__main__":
    asyncio.run(main())