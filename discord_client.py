from datetime import datetime, timedelta
import json
import random
import tweepy
import time
import discord
from discord.ext import tasks
from local_settings import DISCORD_TOKEN, TWITTER_TOKEN
import logging

from config_parameters import *

from filelock import FileLock

lock = FileLock("data/forms_points.json.lock")

logger = logging.getLogger('FORMS_BOT')

embed_colors = [0xA429D6, 0xB654DE]


class FormsClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._load_forms_points()

        self.pending_alpha = {}
        self.all_sent_alpha = []

        self.past_tweet_ids = []

        self.next_token = None

        self.client = tweepy.Client(
            TWITTER_TOKEN,
            return_type=dict
        )

    def _load_forms_points(self):
        with lock:
            with open('data/forms_points.json', 'r') as f:
                self.forms_points = json.load(f)

    async def setup_hook(self) -> None:
        ### Checks one channel for alpha now. Could be updated to check a list of channels or all
        self.check_twitter.start()

        ### Used when bot sends a message about alpha
        self.ALPHA_CHANNEL = await self.fetch_channel(ALPHA_CHANNEL_ID)
        self.TWITTER_CHANNEL = await self.fetch_channel(TWITTER_CHANNEL_ID)

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')

    @tasks.loop(seconds=RELOAD_FORMS_POINTS_INTERVAL)  # task runs every 60 seconds
    async def reload_forms_points(self):
        ### Check for new messages with alpha reacts
        ### Check messages that had alpha reacts before to see if any broke threshold
        self._load_forms_points()

    @tasks.loop(seconds=CHECK_TWITTER_INTERVAL)  # task runs every 60 seconds
    async def check_twitter(self):
        result = self.client.get_list_tweets(
            id='1623371721813200932', expansions=["author_id", "attachments.media_keys"],
            tweet_fields=['attachments', 'public_metrics', 'created_at', 'author_id'],
            user_fields=['profile_image_url', 'username'],
            media_fields=['url', 'preview_image_url'], 
            max_results=5,
            pagination_token=self.next_token
        )
        next_token = result['meta']['next_token']
        tweet_data = result['data']
        user_data = result['includes']['users']

        try:
            media_data = result['includes']['media']
        except:
            media_data = []

        tweet_data = sorted(tweet_data, key=lambda x: x['created_at'])
        for tweet in tweet_data:
            if tweet['id'] in self.past_tweet_ids:
                continue

            author_id = tweet['author_id']
            if 'attachments' in tweet:
                try:
                    media_key = tweet['attachments']['media_keys'][0]
                    media_tweet = [i for i in media_data if i['media_key'] == media_key][0]
                except:
                    media_tweet = {}

            else:
                media_tweet = {}

            user = [i for i in user_data if i['id'] == author_id][0]
            user_img = user['profile_image_url']
            embed = discord.Embed(
                title=f"Tweet from @{user['username']}", 
                url=f"https://twitter.com/{user['username']}/status/{tweet['id']}",
                description=f"{tweet['text']}\n\n[forms friends list](https://twitter.com/i/lists/1623371721813200932)", 
                timestamp=datetime.strptime(tweet['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ"),
                colour=random.choice(embed_colors)
            )
            if user_img:
                embed.set_thumbnail(url=user_img)
            
            await self.TWITTER_CHANNEL.send(
                embed=embed
            )
            
            self.past_tweet_ids.append(tweet['id'])

    @check_twitter.before_loop
    async def before_my_task(self):
        await self.wait_until_ready()  # wait until the bot logs in

def _run_discord_client():
    client = FormsClient(intents=discord.Intents.all())
    client.run(DISCORD_TOKEN)