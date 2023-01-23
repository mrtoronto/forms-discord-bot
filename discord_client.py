from datetime import datetime, timedelta
import json
import os
import discord
from discord.ext import tasks
from local_settings import DISCORD_TOKEN
import logging

from config_parameters import *

from filelock import FileLock

lock = FileLock("data/forms_points.json.lock")

logger = logging.getLogger('FORMS_BOT')

class FormsClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._load_forms_points()

        self.ALPHA_CHANNEL_ID = 1045019403701461092

        self.pending_alpha = {}
        self.all_sent_alpha = []

    def _load_forms_points(self):
        with lock:
            with open('data/forms_points.json', 'r') as f:
                self.forms_points = json.load(f)

    async def setup_hook(self) -> None:
        ### Checks one channel for alpha now. Could be updated to check a list of channels or all
        self.check_recent_messages_task.start(channel_id=self.ALPHA_CHANNEL_ID)
        self.check_all_alpha_messages.start()

        ### Used when bot sends a message about alpha
        self.ALPHA_CHANNEL = await self.fetch_channel(self.ALPHA_CHANNEL_ID)

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
    async def check_recent_messages_task(self, channel_id, threshold=LAYER_1_ALPHA_THRESHOLD):
        ### Check for new messages with `threshold` or more alpha reacts
        ### Check messages that had alpha reacts before to see if any broke threshold
        logger.info('Checking for new messages with alpha reacts')
        channel = await self.fetch_channel(channel_id)
        
        ### Get all messages sent since start_date
        start_date = datetime.now() - timedelta(hours=TRAILING_ALPHA_PERIOD)
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

    @tasks.loop(seconds=CHECK_PENDING_ALPHA_INTERVAL)  # task runs every 60 seconds
    async def check_all_alpha_messages(self, threshold=LAYER_2_ALPHA_THRESHOLD):
        ### Check for new messages with alpha reacts
        ### Check messages that had alpha reacts before to see if any broke threshold
        logger.info('Checking messages with alpha reacts')
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

    @check_recent_messages_task.before_loop
    async def before_my_task(self):
        await self.wait_until_ready()  # wait until the bot logs in

def _run_discord_client():
    client = FormsClient(intents=discord.Intents(messages=True, message_content=True))
    client.run(DISCORD_TOKEN)