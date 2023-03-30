
import asyncio
import json
import discord
from discord.ext import commands
from bot_scripts.member_update import _on_member_join, _on_member_update
from bot_scripts.on_message import _on_message
from bot_scripts.react_add import _on_raw_reaction_add
from bot_scripts.react_remove import _on_raw_reaction_remove
from local_settings import DISCORD_TOKEN
import logging
from filelock import FileLock
import config_parameters as config

from bot_scripts.bot_cog import WaveyCog

lock = FileLock("data/forms_points.json.lock")



logger = logging.getLogger('FORMS_BOT')

class FormsBot:
    def __init__(self):
        with open('data/forms_points.json', 'r') as f:
            self.forms_points = json.load(f)
        with open('data/forms_points_trxns.json', 'r') as f:
            self.forms_points_trxns = json.load(f)

        self._bot = commands.Bot(
            command_prefix=commands.when_mentioned_or('/'), 
            intents=discord.Intents.all()
        )

        self.pending_alpha = {}
        self.sent_alpha = {1073324858575945748: True}

        self.GWP = {
            'temperature': 0.7,
            'max_length': 300,
            'alpha_threshold': config.ALPHA_REACT_THRESHOLD,
        }

        self.member_converter = commands.MemberConverter()
        self.genesis_invite = None
        self.genesis_invite_uses = 0

    async def update_genesis_invite_use_count(self):
        genesis_invite_code = "8zepXuy5au"
        guild = await self._bot.fetch_guild(1072543131607777300)
        guild_invites = await guild.invites()
        self.genesis_invite = [i for i in guild_invites if i.code == genesis_invite_code][0]
        self.genesis_invite_uses = bot.genesis_invite.uses
        logger.info(f'Genesis invite uses: {self.genesis_invite_uses}')
        return self.genesis_invite_uses

    def _export_forms_points(self):
        with lock:
            with open('data/forms_points.json', 'w') as f:
                json.dump(self.forms_points, f)
            with open('data/forms_points_trxns.json', 'w') as f:
                json.dump(self.forms_points_trxns, f)

bot = FormsBot()

@bot._bot.event
async def on_raw_reaction_remove(payload):
    await _on_raw_reaction_remove(payload, bot)

@bot._bot.event
async def on_raw_reaction_add(payload):
    await _on_raw_reaction_add(payload, bot)

@bot._bot.event
async def on_ready():
    bot.genesis_invite_uses = await bot.update_genesis_invite_use_count()
    logger.info(f'Logged in as {bot._bot.user} (ID: {bot._bot.user.id})')
    logger.info(f'Genesis invite uses: {bot.genesis_invite_uses}')
    logger.info('------')
    asyncio.ensure_future(add_cog(bot))
    
async def add_cog(bot):
    await bot._bot.wait_until_ready()
    await bot._bot.add_cog(WaveyCog(bot._bot))
    
@bot._bot.event
async def on_message(message):
    await _on_message(message, bot)

#Events
@bot._bot.event
async def on_member_update(before, after):
    await _on_member_update(before, after, bot)


@bot._bot.event
async def on_member_join(member):
    await _on_member_join(member, bot)


def _run_discord_bot():
    bot._bot.run(DISCORD_TOKEN)