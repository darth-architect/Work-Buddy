import os
import time
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

SLACK_USER_TOKEN = os.getenv("SLACK_USER_TOKEN")  # xoxp- token, not bot token
YOUR_USER_ID = "U0C1FTC0B40"  # your own Slack user ID

client = WebClient(token=SLACK_USER_TOKEN)
channel_id = client.conversations_open(users=[YOUR_USER_ID])["channel"]["id"]

def delete_my_messages(channel_id):
    cursor = None
    deleted = 0
    while True:
        resp = client.conversations_history(channel=channel_id, cursor=cursor, limit=200)
        for msg in resp["messages"]:
            # Only delete messages YOU authored (skip bot messages, which this token can't touch anyway)
            if msg.get("user") == YOUR_USER_ID and not msg.get("bot_id"):
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
    print(f"Done — deleted {deleted} of your messages.")

delete_my_messages(channel_id)