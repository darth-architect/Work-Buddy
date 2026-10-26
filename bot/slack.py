import asyncio
import os

from dotenv import load_dotenv
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler

from test_mcp import build_agent, current_user_email, current_user_message

load_dotenv()

slack_app = AsyncApp(token=os.getenv("SLACK_BOT_TOKEN"))

agent = None
histories = {}
email_cache = {}

MAX_HISTORY_MESSAGES = 12  # how many recent turns to keep feeding the model; tune to taste

RESET_PHRASES = {
    "reset", "/reset", "start over", "/start over",
    "cancel", "/cancel", "clear", "/clear", "new conversation",
}


async def get_user_email(user_id, client):
    if user_id in email_cache:
        return email_cache[user_id]
    info = await client.users_info(user=user_id)
    email = info["user"]["profile"].get("email")
    email_cache[user_id] = email
    return email


def is_reset_command(text: str) -> bool:
    return text.strip().lower() in RESET_PHRASES


async def run_agent(user_id, text, client):
    if is_reset_command(text):
        histories[user_id] = []
        return "Starting fresh — I've cleared our conversation so far. What do you need help with?"

    email = await get_user_email(user_id, client)
    if not email:
        return "I couldn't find a verified email on your Slack account, so I can't safely run this for you."

    current_user_email.set(email)

    history = histories.setdefault(user_id, [])
    history.append({"role": "user", "content": text})

    trimmed_history = history[-MAX_HISTORY_MESSAGES:]
    current_user_message.set(" ".join(m["content"] for m in trimmed_history if m["role"] == "user"))

    result = await agent.ainvoke({"messages": trimmed_history})
    reply = result["messages"][-1].content
    history.append({"role": "assistant", "content": reply})
    return reply


@slack_app.event("app_mention")
async def handle_mention(event, say, client):
    reply = await run_agent(event["user"], event["text"], client)
    await say(reply)


@slack_app.event("message")
async def handle_dm(event, say, client):
    if event.get("channel_type") == "im" and "subtype" not in event:
        reply = await run_agent(event["user"], event["text"], client)
        await say(reply)


async def main():
    global agent
    last_error = None
    for attempt in range(1, 6):
        try:
            agent = await build_agent()
            break
        except Exception as e:
            last_error = e
            wait = attempt * 3  # 3s, 6s, 9s, 12s, 15s
            print(f"build_agent() failed (attempt {attempt}/5): {e}")
            print(f"Retrying in {wait}s...")
            await asyncio.sleep(wait)
    else:
        print("build_agent() failed after 5 attempts — giving up.")
        raise last_error

    handler = AsyncSocketModeHandler(slack_app, os.getenv("SLACK_APP_TOKEN"))
    print("Slack bot running (Socket Mode)...")
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(main())