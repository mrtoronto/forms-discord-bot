import pytz
from datetime import datetime, timedelta
import json
import random
import tweepy
import discord
from discord.ext import tasks
from local_settings import DISCORD_TOKEN, TWITTER_TOKEN
import logging

from config_parameters import *

from filelock import FileLock

from oa_api import _get_gpt_response

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
        self.past_influencer_tweet_ids = []

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
        self.check_influencer_twitter.start()

        self.TWITTER_CHANNEL = await self.fetch_channel(TWITTER_CHANNEL_ID)
        self.INFLUENCER_TWITTER_CHANNEL = await self.fetch_channel(INFLUENCER_TWITTER_CHANNEL_ID)

        twitter_channel_history = self.TWITTER_CHANNEL.history(limit=50)
        async for message in twitter_channel_history:
            
            tweet_id = message.embeds[0].url.split('/')[-1]
            self.past_tweet_ids.append(tweet_id)

        logger.info(f'Found {len(self.past_tweet_ids)} tweets in history.. Saving to past tweets.')

        await self.check_recent_infl_tweets(send=True)

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
            max_results=15,
            pagination_token=self.next_token
        )
        next_token = result['meta']['next_token']
        tweet_data = result['data']
        user_data = result['includes']['users']

        tweet_data = sorted(tweet_data, key=lambda x: x['created_at'])
        for tweet in tweet_data:
            if tweet['id'] in self.past_tweet_ids:
                continue
            author_id = tweet['author_id']            
            user = [i for i in user_data if i['id'] == author_id][0]
            user_img = user['profile_image_url']
            sent_at = datetime.strptime(tweet['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
            sent_at = sent_at.replace(tzinfo=pytz.UTC)
            if tweet['text'][0:2] == 'RT':
                # original_poster = tweet['text'].split('RT')[1].split(':')[0].strip()
                # title = f"@{user['username']} retweeted {original_poster}"
                continue
            else:
                title = f"@{user['username']} tweeted"
            embed = discord.Embed(
                title=title,
                url=f"https://twitter.com/{user['username']}/status/{tweet['id']}",
                description=f"{tweet['text']}\n\n[forms friends](https://twitter.com/i/lists/1623371721813200932)\n\n", 
                colour=random.choice(embed_colors)
            )
            if user_img:
                embed.set_thumbnail(url=user_img)
            embed.add_field(
                name=f'',
                value=f'Twitter • <t:{int(sent_at.timestamp())}:R>',
                inline=False
            )
            file = discord.File("twitter_logo.png", filename="twitter_logo.png")
            embed.set_footer(
                text="\u200b",
                icon_url="attachment://twitter_logo.png"
            )
            
            await self.TWITTER_CHANNEL.send(
                embed=embed,
                file=file
            )
            
            self.past_tweet_ids.append(tweet['id'])

    @check_twitter.before_loop
    async def before_my_task(self):
        await self.wait_until_ready()  # wait until the bot logs in
    


    def get_user_id(self, username):
        user = self.client.get_user(username=username)
        print(user)
        return user['data']['id']

    def get_recent_tweets(self, user_id, count=10):
        # Get the user's most recent tweets
        recent_tweets = self.client.get_users_tweets(id=user_id, max_results=count, exclude="replies")

        return recent_tweets\
        
    async def check_recent_infl_tweets(self, send=True):
        usernames = ["elonmusk", "chriscantino", "punk9059"]  # Replace this with the username of the Twitter account you want to fetch tweets from
        for username in usernames:
            user_id = self.get_user_id(username)
            count = 5  # The number of tweets you want to fetch (max is 100)

            tweets = self.get_recent_tweets(user_id, count)

            # Print out the fetched tweets
            for tweet in tweets['data']:
                if tweet['id'] not in self.past_influencer_tweet_ids:
                    self.past_influencer_tweet_ids.append(tweet['id'])
                    prompt = [{"role": "system", "content": "You are a sarcastic bot that replies to tweets with sarcastic replies. You are often cheeky and not too mean but always very funny. You're widely knowledgable about cryptocurrency, AI, technology and space. You're also a bit of a meme lord."}]
                    prompt += [{"role": "user", "content": tweet['text']}]
                    wavey_reply = _get_gpt_response(
                        prompt,
                        0.5, 
                        50, 
                        '', 
                        (False, False), 
                        model='gpt-3.5-turbo'
                    )
                    wavey_reply = " ".join(wavey_reply['lines'])

                    if send:
                        body = f"https://twitter.com/{username}/status/{tweet['id']}\n```{tweet['text']}```"
                        msg = await self.INFLUENCER_TWITTER_CHANNEL.send(body)
                        await msg.edit(suppress=True)
                        body = f"{wavey_reply}"
                        await self.INFLUENCER_TWITTER_CHANNEL.send(body)
    
    @tasks.loop(minutes=5)
    async def check_influencer_twitter(self):
        await self.check_recent_infl_tweets()

    @check_influencer_twitter.before_loop
    async def before_my_task(self):
        await self.wait_until_ready()  # wait until the bot logs in


def _run_discord_client():
    client = FormsClient(intents=discord.Intents.all())
    client.run(DISCORD_TOKEN)