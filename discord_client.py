from datetime import datetime, timedelta
import json
import random
# import tweepy
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

        # self.client = tweepy.Client(
        #     TWITTER_TOKEN,
        #     return_type=dict
        # )

    def _load_forms_points(self):
        with lock:
            with open('data/forms_points.json', 'r') as f:
                self.forms_points = json.load(f)

    # async def on_member_join(self, member):
    #     # Get the moderator role
    #     logger.info(f'Running event on_member_join for {member}')
    #     moderator_role = discord.utils.get(member.guild.roles, name='Team')
        
    #     # Create a new private voice channel for the user
    #     new_channel = await member.guild.create_text_channel(
    #         name=member.display_name,
    #         category=None,
    #         overwrites={
    #             member.guild.default_role: discord.PermissionOverwrite(read_messages=False),
    #             member: discord.PermissionOverwrite(read_messages=True),
    #             moderator_role: discord.PermissionOverwrite(read_messages=True)
    #         },
    #         position=0,
    #         reason='Creating a private voice channel for the new user'
    #     )


    async def setup_hook(self) -> None:
        ### Checks one channel for alpha now. Could be updated to check a list of channels or all
        self.check_recent_messages_task.start(channel_ids=CHANNELS_TO_CHECK)
        self.check_all_alpha_messages.start()
        # self.check_twitter.start()

        ### Used when bot sends a message about alpha
        self.ALPHA_CHANNEL = await self.fetch_channel(ALPHA_CHANNEL_ID)
        self.TWITTER_CHANNEL = await self.fetch_channel(TWITTER_CHANNEL_ID)

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')

    def _check_custom_react(self, r, n, react_id):
        return (r.is_custom_emoji() and r.emoji.id == react_id and r.count >= n)

    def _check_normal_react(self, r, n, emoji='🌞'):
        return (r.emoji == emoji and r.count >= n)

    @tasks.loop(seconds=RELOAD_FORMS_POINTS_INTERVAL)  # task runs every 60 seconds
    async def reload_forms_points(self):
        ### Check for new messages with alpha reacts
        ### Check messages that had alpha reacts before to see if any broke threshold
        self._load_forms_points()

    @tasks.loop(seconds=CHECK_RECENT_MESSAGES_INTERVAL)  # task runs every 60 seconds
    async def check_recent_messages_task(self, channel_ids, threshold=LAYER_1_ALPHA_THRESHOLD):
        ### Check for new messages with `threshold` or more alpha reacts
        ### Check messages that had alpha reacts before to see if any broke threshold
        
        start_time = time.time()
        ### Get all messages sent since start_date
        start_date = datetime.now() - timedelta(hours=TRAILING_ALPHA_PERIOD)

        logger.info(f'Checking for new messages with alpha reacts in channels: {channel_ids}')
        for channel_id in channel_ids:
            channel = await self.fetch_channel(channel_id)    
            async for message in channel.history(after=start_date):
                ### Check reacts on each message in the history
                for r in message.reactions:
                    ### Check if message has a single alpha react
                    ### Check if message has already been sent as alpha
                    ### Check if message is already pending alpha
                    if (self._check_custom_react(r, n=threshold, react_id=ALPHA_REACT_ID)) and \
                        (message.id not in self.all_sent_alpha) and \
                        (message.id not in self.pending_alpha):
                        logger.info('Found one with an ALPHA!')
                        self.pending_alpha[message.id] = {'channel_id': message.channel.id}

            run_time = time.time() - start_time
            logger.info(f'Checked for new messages with alpha reacts in channel: {channel_id} in {run_time:1f}s')

        run_time = time.time() - start_time
        logger.info(f'Checked for new messages in all channels in {run_time:1f}s')

    @tasks.loop(seconds=CHECK_PENDING_ALPHA_INTERVAL)  # task runs every 60 seconds
    async def check_all_alpha_messages(self, threshold=LAYER_2_ALPHA_THRESHOLD):
        ### Check for new messages with alpha reacts
        ### Check messages that had alpha reacts before to see if any broke threshold
        if len(self.pending_alpha.items()):
            logger.info(f'Checking all pending alpha ({len(self.pending_alpha)} messages)')
        
        start_time = time.time()
        messages_to_remove = []
        ### Check messages that had alpha reacts before to see if any broke threshold
        ### Messages only added to pending_alpha if they haven't been quoted before
        for message_id, message_data in self.pending_alpha.items():
            channel = await self.fetch_channel(message_data['channel_id'])
            message = await channel.fetch_message(message_id)

            for r in message.reactions:
                if self._check_custom_react(r, n=threshold, react_id=ALPHA_REACT_ID):
                    
                    ### Update message bot sends to channel
                    ### Make it pretty
                    await self.ALPHA_CHANNEL.send(
                        'ALPHA REACHED THRESHOLD. CHECK IT OUT!', 
                        reference=message
                    )

                    ### Remove the message when the loop is finished
                    messages_to_remove.append(message_id)
                    
                    ### Record sent alpha messages to theyre not resent
                    self.all_sent_alpha.append(message_id)
                    break
            
        for message_id in messages_to_remove:
            self.pending_alpha.pop(message_id)

        run_time = time.time() - start_time
        logger.info(f'Checked all pending alpha in {run_time:1f}s')

    @check_recent_messages_task.before_loop
    async def before_my_task(self):
        await self.wait_until_ready()  # wait until the bot logs in

    @check_all_alpha_messages.before_loop
    async def before_my_task(self):
        await self.wait_until_ready()  # wait until the bot logs in
    

    # @tasks.loop(seconds=CHECK_TWITTER_INTERVAL)  # task runs every 60 seconds
    # async def check_twitter(self):
    #     result = self.client.get_list_tweets(
    #         id='7450', expansions=["author_id", "attachments.media_keys"],
    #         tweet_fields=['attachments', 'public_metrics', 'created_at', 'author_id'],
    #         user_fields=['profile_image_url', 'username'],
    #         media_fields=['url', 'preview_image_url'], 
    #         max_results=5,
    #         pagination_token=self.next_token
    #     )
    #     print(result)
    #     next_token = result['meta']['next_token']
    #     tweet_data = result['data']
    #     user_data = result['includes']['users']

    #     try:
    #         media_data = result['includes']['media']
    #     except:
    #         media_data = []

    #     print('Tweet DATA: ', len(tweet_data), tweet_data[0])
    #     print('USERS DATA: ', len(user_data), user_data[0])
    #     if media_data:
    #         print('MEDIA DATA: ', len(media_data), media_data[0])

    #     for tweet in tweet_data:
    #         if tweet['id'] in self.past_tweet_ids:
    #             continue

    #         author_id = tweet['author_id']
    #         if 'attachments' in tweet:
    #             try:
    #                 media_key = tweet['attachments']['media_keys'][0]
    #                 media_tweet = [i for i in media_data if i['media_key'] == media_key][0]
    #             except:
    #                 media_tweet = {}

    #         else:
    #             media_tweet = {}

    #         user = [i for i in user_data if i['id'] == author_id][0]
    #         print(f'Sending Discord message for {tweet}')
    #         embed = discord.Embed(
    #             title="Tweet", 
    #             url=f"https://twitter.com/{user['username']}/status/{tweet['id']}",
    #             description=f"{tweet['text']}", 
    #             timestamp=datetime.strptime(tweet['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ"),
    #             colour=random.choice(embed_colors)
    #         )  # Initializing an
    #         await self.TWITTER_CHANNEL.send(
    #             embed=embed
    #         )

    # @check_twitter.before_loop
    # async def before_my_task(self):
    #     await self.wait_until_ready()  # wait until the bot logs in

def _run_discord_client():
    client = FormsClient(intents=discord.Intents.all())
    client.run(DISCORD_TOKEN)