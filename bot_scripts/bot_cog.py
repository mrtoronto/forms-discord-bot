from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from datetime import time as dt_time
import random

# Load your API key from an environment variable or secret management service

import asyncio
from discord.ext import commands
import pytz
from scripts.gcs import upload_blob
import logging
import sched
import time

logger = logging.getLogger('FORMS_BOT')

scheduler = sched.scheduler(time.time, time.sleep)     


async def wakeup_message(bot):
    forms_guild_id = 1072543131607777300
    forms_guild = bot.get_guild(forms_guild_id)
    bot_commands_channel = forms_guild.get_channel(1072555059637923910)
    nsfwavey_channel = forms_guild.get_channel(1080986943946502235)
    logger.info('Sending wakeup message')
    await bot.wait_until_ready()
    await nsfwavey_channel.send('Gm ;)')
    await bot_commands_channel.send('NSFWavey is awake.')


class WaveyCog(commands.Cog):
    def __init__(self, bot):
        logger.info('Initializing WaveyCog')
        self.bot = bot
        self.morning_start = 0
        self.night_start = 0

        self.scheduler = AsyncIOScheduler()
        ### Save job so its schedule can be edited later
        self.wake_up_job = self.scheduler.add_job(self.wake_up, CronTrigger(hour='9', minute=0, second=0))
        self.clear_channel_job = self.scheduler.add_job(
            self.clear_channel, 
            CronTrigger(hour='*', minute=52, second=0)
        )
        self.scheduler.add_job(
            self._update_start_times, 
            CronTrigger(hour=0, minute=0, second=0)
        )
        self.scheduler.add_job(
            self._backup_forms_points, 
            CronTrigger(hour=0, minute=0, second=0)
        )
        self.scheduler.start()

        asyncio.create_task(self._update_start_times())

        self._backup_forms_points()

    def _backup_forms_points(self):
        logger.info('Backing up forms points')
        upload_blob(
            source_filename='data/forms_points.json',
            remote_filename=f'form_point_backup/forms_points_{datetime.now():%Y%m%d}.json'
        )
        upload_blob(
            source_filename='data/forms_points_trxns.json',
            remote_filename=f'form_point_backup/forms_points_trxns_{datetime.now():%Y%m%d}.json'
        )

    async def _update_start_times(self):
        await self.bot.wait_until_ready()  # Wait until the bot is fully connected
        logger.info('Updating start times')
        self.morning_start = random.randint(0, 5)
        self.night_start = random.randint(12, 17)

        self.scheduler.reschedule_job(
            self.wake_up_job.id, 
            trigger=CronTrigger(hour=f'{self.morning_start},{self.night_start}')
        )

        morning_end = self.morning_start + 6
        night_end = self.night_start + 6

        self.scheduler.reschedule_job(
            self.clear_channel_job.id, 
            trigger=CronTrigger(hour=f'{morning_end},{night_end}')
        )

        await self.new_times_alert()

    async def new_times_alert(self):
        forms_guild_id = 1072543131607777300
        forms_guild = self.bot.get_guild(forms_guild_id)
        bot_commands_channel = forms_guild.get_channel(1072555059637923910)
        est_tz_out = pytz.timezone("US/Eastern")
        pst_tz_out = pytz.timezone("US/Pacific")
        current_date = datetime.utcnow().date()
        morning_start_est = datetime.combine(current_date, dt_time(self.morning_start, 0, 0, tzinfo=pytz.utc)).astimezone(est_tz_out).time()
        night_start_est = datetime.combine(current_date, dt_time(self.night_start, 0, 0, tzinfo=pytz.utc)).astimezone(est_tz_out).time()
        morning_start_pst = datetime.combine(current_date, dt_time(self.morning_start, 0, 0, tzinfo=pytz.utc)).astimezone(pst_tz_out).time()
        night_start_pst = datetime.combine(current_date, dt_time(self.night_start, 0, 0, tzinfo=pytz.utc)).astimezone(pst_tz_out).time()
        
        await self.bot.wait_until_ready()

        await bot_commands_channel.send(
            f'[NSFWavey Wake-up Times]: I\'ll be up for 6 hours between {self.morning_start}:00-{self.morning_start + 6}:00 and {self.night_start}:00-{self.night_start + 6}:00 UTC'
            f' /// {morning_start_est:%H:%M} and {night_start_est:%H:%M} EST '
            f' /// {morning_start_pst:%H:%M} and {night_start_pst:%H:%M} PST today.'
        )

    def cog_unload(self):
        self.scheduler.shutdown()

    async def wake_up(self):
        logger.info('Task running')
        await wakeup_message(self.bot)

    async def clear_channel(self):
        forms_guild_id = 1072543131607777300
        forms_guild = self.bot.get_guild(forms_guild_id)
        bot_commands_channel = forms_guild.get_channel(1072555059637923910)
        nsfwavey_channel = forms_guild.get_channel(1080986943946502235)
        await nsfwavey_channel.purge()
        await bot_commands_channel.send('NSFWavey is asleep.')

        
