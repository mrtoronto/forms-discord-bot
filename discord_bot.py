import time
import traceback
import openai

# Load your API key from an environment variable or secret management service

import asyncio
import json
import discord
from discord.ext import commands
from local_settings import DISCORD_TOKEN, OPENAI_API_KEY
import logging
from filelock import FileLock

lock = FileLock("data/forms_points.json.lock")

openai.api_key = OPENAI_API_KEY

logger = logging.getLogger('FORMS_BOT')

class FormsBot:
    def __init__(self):
        
        with open('data/forms_points.json', 'r') as f:
            self.forms_points = json.load(f)

        self._bot = commands.Bot(
            command_prefix=commands.when_mentioned_or('/'), 
            intents=discord.Intents.all()
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

@bot._bot.event
async def on_message(message):
    if bot._bot.user in message.mentions and message.author != bot._bot.user:
        previous_messages = message.channel.history(limit=10)
        previous_messages_list = []
        async for history_message in previous_messages:
            if history_message.author == message.author:
                proc_message = history_message.content.replace('/ask', '').strip()
                previous_messages_list.append(f'{message.author.name}: {proc_message}')
        previous_messages_list = previous_messages_list[::-1]
        previous_messages_str = '\n'.join(previous_messages_list)[-500:]
        lines = _get_gpt_response(message.content, previous_messages_str)

        for idx, line in enumerate(lines):
            await message.channel.send(line)



#Events
@bot._bot.event
async def on_member_join(member):
    # Get the moderator role
    roles = await member.guild.fetch_roles()
    categories = member.guild.categories
    moderator_role = discord.utils.get(roles, name='Team')
    wavey_role = discord.utils.get(roles, name='Wavey')
    con_category = discord.utils.get(categories, name='Concierge')
    logger.info(f'Running event on_member_join for {member} with {moderator_role} & {wavey_role} in {con_category}')
    
    # Create a new private voice channel for the user
    new_channel = await member.guild.create_text_channel(
        name=f"{member.display_name} - From Concierge",
        category=con_category,
        overwrites={
            member.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True),
            moderator_role: discord.PermissionOverwrite(read_messages=True),
            wavey_role: discord.PermissionOverwrite(read_messages=True, read_message_history=True)
        },
        position=0,
        reason='Creating a private voice channel for the new user'
    )

    



def _get_gpt_response(question, previous_messages_str):
    prompt = f"""You are Wavey. A cheeky, sarcastic but caring robot tasked with helping the people of the Forms Server after making them laugh a bit. 

You have been asked the following question. Before the question you are given some conversation history. Generate a response to the user and don't talk to yourself after.

HISTORY:
{previous_messages_str}

QUESTION TO RESPOND TO: 
{question}"""

    print(f'Prompt: \n{prompt}')
    response = openai.Completion.create(
        model="text-davinci-003", 
        prompt=prompt.strip(), 
        temperature=0.7, 
        max_tokens=300
    )
    lines = response.choices[0].text.split('\n')
    lines = [l for l in lines if l.strip()]
    return lines

@bot._bot.hybrid_command(name='wavey', description='Asks a question to the bot')
async def wavey(ctx, *, args):
    question = args
    print(f'Asking question: {question}')
    previous_messages = ctx.channel.history(limit=10)
    previous_messages_list = []
    async for message in previous_messages:
        if message.author == ctx.author:
            proc_message = message.content.replace('/ask', '').strip()
            previous_messages_list.append(f'{message.author.name}: {proc_message}')
    previous_messages_list = previous_messages_list[::-1]
    previous_messages_str = '\n'.join(previous_messages_list)[-500:]
    try:
        lines = _get_gpt_response(question, previous_messages_str)
        for idx, line in enumerate(lines):
            await ctx.send(line)
    except:
        print(traceback.format_exc())
    
    # for line in lines:

@bot._bot.hybrid_command(name='tip', description='Sends tip to another user')
async def tip(ctx, username, amount: int):
    """Sets current channel to the guild's notification channel."""
    member = await bot.member_converter.convert(ctx, username)
    tipped_user_id_str = str(member.id)
    author_id_str = str(ctx.message.author.id)
    
    if author_id_str not in bot.forms_points:
        await ctx.send(f'User {ctx.message.author} has no points.')
        return None
    elif bot.forms_points[author_id_str] < amount:
        await ctx.send(f'User {ctx.message.author} has insufficient points.')
        return None
    else:
        bot.forms_points[author_id_str] = bot.forms_points.get(author_id_str, 0) - amount
        bot.forms_points[tipped_user_id_str] = bot.forms_points.get(tipped_user_id_str, 0) + amount
        await ctx.send(f'User {ctx.message.author.name} sent {amount} to {member.name}.')
        bot._export_forms_points()

@bot._bot.hybrid_command(name='give', description='Give form points to self')
async def give(ctx, amount: int):
    author_id = str(ctx.message.author.id)
    author_name = ctx.message.author.name
    bot.forms_points[author_id] = bot.forms_points.get(author_id, 0) + amount
    await ctx.send(f'User {author_name} sent {amount} to {author_name}.')
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
        user_obj = await ctx.guild.fetch_member(user)
        username = user_obj.name
        leader_board_str += f'{username}: {score} \n'
    await ctx.send(f'LEADERBOARD: \n\n {leader_board_str}')

@tip.error
async def tip_error(ctx, error):
    await ctx.send(f'Failed to tip. {error}')

def _run_discord_bot():
    bot._bot.run(DISCORD_TOKEN)