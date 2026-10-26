import os
import time
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
YOUR_USER_ID = "U0C1FTC0B40"  # your Slack member id — profile picture > "Copy member ID"

client = WebClient(token=SLACK_BOT_TOKEN)
channel_id = client.conversations_open(users=[YOUR_USER_ID])["channel"]["id"]

def delete_all_bot_messages(channel_id):
    cursor = None
    deleted = 0
    while True:
        resp = client.conversations_history(channel=channel_id, cursor=cursor, limit=200)
        for msg in resp["messages"]:
            if msg.get("bot_id") or msg.get("subtype") == "bot_message":
                while True:
                    try:
                        client.chat_delete(channel=channel_id, ts=msg["ts"])
                        deleted += 1
                        print(f"Deleted {msg['ts']} (total: {deleted})")
                        time.sleep(0.3)
                        break
                    except SlackApiError as e:
                        if e.response.get("error") == "ratelimited":
                            wait = int(e.response.headers.get("Retry-After", 5))
                            print(f"Rate limited, waiting {wait}s...")
                            time.sleep(wait)
                        else:
                            print(f"Failed on {msg['ts']}: {e.response['error']}")
                            break
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    print(f"Done — deleted {deleted} messages.")

delete_all_bot_messages(channel_id)