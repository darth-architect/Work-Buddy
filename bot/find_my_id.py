import os
from slack_sdk import WebClient

client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

for member in client.users_list()["members"]:
    print(member["id"], member.get("real_name"), member.get("profile", {}).get("email"))