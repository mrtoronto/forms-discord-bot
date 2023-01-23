import asyncio
import json
import discord
from discord.ext import commands
from local_settings import DISCORD_TOKEN

import logging

from filelock import FileLock

lock = FileLock("data/forms_points.json.lock")

logger = logging.getLogger('FORMS_BOT')
class FormsBot:
    def __init__(self):
        
        with open('data/forms_points.json', 'r') as f:
            self.forms_points = json.load(f)

        self._bot = commands.Bot(
            command_prefix='/', 
            intents=discord.Intents(messages=True, message_content=True)
        )

        self.member_converter = commands.MemberConverter()

    def _export_forms_points(self):
        with lock:
            with open('data/forms_points.json', 'w') as f:
                json.dump(self.forms_points, f)

bot = FormsBot()

@bot._bot.event
async def on_ready():
    logger.info(f'Logged in as {bot._bot.user} (ID: {bot._bot.user.id})')
    logger.info('------')

@bot._bot.hybrid_command(name='tip', description='Sends tip to another user')
async def tip(ctx, username, amount: int):
    """Sets current channel to the guild's notification channel."""
    member = await bot.member_converter.convert(ctx, username)
    print(member)
    tipped_user_id = member.id
    
    if ctx.message.author.id not in bot.forms_points:
        await ctx.send(f'User {ctx.message.author} has no points.')
        return None
    elif bot.forms_points[ctx.message.author.id] < amount:
        await ctx.send(f'User {ctx.message.author} has insufficient points.')
        return None
    else:
        bot.forms_points[ctx.message.author.id] = bot.forms_points.get(tipped_user_id, 0) - amount
        bot.forms_points[tipped_user_id] = bot.forms_points.get(tipped_user_id, 0) + amount
        await ctx.send(f'User {ctx.message.author} sent {amount} to {tipped_user_id}.')
        bot._export_forms_points()

@bot._bot.hybrid_command(name='give', description='Give form points to self')
async def give(ctx, amount: int):
    author_id = ctx.message.author.id
    author_name = ctx.message.author.name
    bot.forms_points[author_id] = bot.forms_points.get(author_id, 0) + amount
    await ctx.send(f'User {author_name} sent {amount} to {author_id}.')

    bot._export_forms_points()

@bot._bot.hybrid_command(name='check_balance', description='Check personal balance of forms points')
async def check_balance(ctx):
    author_id = ctx.message.author.id
    author_name = ctx.message.author.name
    await ctx.send(f'User {author_name} has {bot.forms_points[author_id]} forms points.')

@bot._bot.hybrid_command(name='check_leaderboards', description='Check leaderboards')
async def check_leaderboards(ctx):
    leader_board = sorted(bot.forms_points.items(), key=lambda x: x[1])
    leader_board_str = ''
    for user, score in leader_board:
        print(user, score)
        user_obj = await ctx.guild.fetch_member(user)
        username = user_obj.name
        leader_board_str += f'{username}: {score} \n'
    await ctx.send(f'LEADERBOARD: \n\n {leader_board_str}')

@tip.error
async def tip_error(ctx, error):
    await ctx.send(f'Failed to tip. {error}')

def _run_discord_bot():
    bot._bot.run(DISCORD_TOKEN)