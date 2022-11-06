import json
import os
import time
from datetime import datetime

import requests
from importlib_metadata import pathlib

bearer = os.environ["BEARER_TOKEN"]

auth = {"Authorization": f"Bearer {bearer}"}

username = "palfrey"
folder = pathlib.Path(__file__).parent.joinpath("users", username)
if not folder.exists():
    folder.mkdir()

user = requests.get(
    f"https://api.twitter.com/2/users/by/username/{username}", headers=auth
)
user.raise_for_status()
user_id = user.json()["data"]["id"]

known_path = folder.joinpath("known.json")
try:
    known_tweets = set(json.load(known_path.open()))
except (FileNotFoundError, json.decoder.JSONDecodeError):
    known_tweets = set()

next_token = None
while False:
    if next_token is not None:
        tweets = requests.get(
            f"https://api.twitter.com/2/users/{user_id}/tweets?max_results=100&pagination_token={next_token}",
            headers=auth,
        )
    else:
        tweets = requests.get(
            f"https://api.twitter.com/2/users/{user_id}/tweets?max_results=100",
            headers=auth,
        )

    tweets.raise_for_status()
    tweets = tweets.json()
    for tweet in tweets["data"]:
        known_tweets.add(tweet["id"])
    json.dump(list(known_tweets), known_path.open("w"), indent=2)
    print(len(known_tweets))
    if "next_token" not in tweets["meta"]:
        break
    next_token = tweets["meta"]["next_token"]

tweet_folder = folder.joinpath("tweets")
if not tweet_folder.exists():
    tweet_folder.mkdir()

for tweet_id in sorted(known_tweets):
    tweet_path = tweet_folder.joinpath(f"{tweet_id}.json")
    if not tweet_path.exists():
        print(tweet_id)
        while True:
            tweet = requests.get(
                f"https://api.twitter.com/2/tweets/{tweet_id}?expansions=author_id,in_reply_to_user_id,referenced_tweets.id,referenced_tweets.id.author_id&tweet.fields=created_at,in_reply_to_user_id",
                headers=auth,
            )
            if tweet.status_code == 429:
                print("too many requests, pausing for 5 minutes", datetime.now())
                time.sleep(300)
                continue
            tweet.raise_for_status()
            json.dump(tweet.json(), tweet_path.open("w"), indent=2)
            break
