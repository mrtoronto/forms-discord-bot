import functools
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
from oa_api import _get_gpt_prompt, _get_gpt_response

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

        self.temperature = 0.7
        self.max_length = 300

    def _export_forms_points(self):
        with lock:
            with open('data/forms_points.json', 'w') as f:
                json.dump(self.forms_points, f)

bot = FormsBot()

@bot._bot.event
async def on_ready():
    logger.info(f'Logged in as {bot._bot.user} (ID: {bot._bot.user.id})')
    logger.info('------')

async def _get_previous_messages(channel, n_messages=10, n_characters=500):
    previous_messages = channel.history(limit=n_messages)
    previous_messages_list = []
    async for history_message in previous_messages:
        proc_message = history_message.clean_content.strip()
        previous_messages_list.append(f'{history_message.author.name}: {proc_message}')
    previous_messages_list = previous_messages_list[::-1]
    previous_messages_str = '\n'.join(previous_messages_list)[-n_characters:]

    return previous_messages_str


@bot._bot.event
async def on_message(message):
    ctx = await bot._bot.get_context(message)
    if bot._bot.user in message.mentions:
        if message.clean_content.split(' ')[0] == f'@{bot._bot.user.name}':
            args = message.clean_content.split(' ')[1:]

            if args[0] == 'set_temperature':
                bot.temperature = float(args[1])
                await message.channel.send(f'Set temperature to {bot.temperature}')
            elif args[0] == 'get_temperature':
                await message.channel.send(f'Temperature currently set to {bot.temperature}')
            elif args[0] == 'set_max_length':
                bot.max_length = int(args[1])
                await message.channel.send(f'Set max response length to {bot.max_length} tokens')
            elif args[0] == 'get_max_length':
                await message.channel.send(f'Max length currently set to {bot.max_length} tokens')
            elif args[0] == 'give':
                sending_name = message.author.name
                sending_member = await bot.member_converter.convert(ctx, sending_name)
                sending_member_id_str = str(sending_member.id)
                amount = float(args[1])
                bot.forms_points[sending_member_id_str] = bot.forms_points.get(sending_member_id_str, 0) + amount
                await ctx.send(f'User {sending_name} sent {amount} to {sending_name}.')
                bot._export_forms_points()

            elif args[0] == 'tip': 
                sending_name = message.author.name
                sending_member = await bot.member_converter.convert(ctx, sending_name)
                sending_member_id_str = str(sending_member.id)
                
                receiving_member_str = args[1]
                amount = float(args[2])
                receiving_member = await bot.member_converter.convert(ctx, receiving_member_str.replace('@', ''))
                receiving_member_id = str(receiving_member.id)
                
                if sending_member_id_str not in bot.forms_points:
                    await ctx.send(f'User {ctx.message.author} has no points.')
                    return None
                elif bot.forms_points[sending_member_id_str] < amount:
                    await ctx.send(f'User {ctx.message.author} has insufficient points.')
                    return None
                else:
                    bot.forms_points[sending_member_id_str] = bot.forms_points.get(sending_member_id_str, 0) - amount
                    bot.forms_points[receiving_member_id] = bot.forms_points.get(receiving_member_id, 0) + amount
                    await ctx.send(f'User {sending_name} sent {amount} to {receiving_member.name}.')
                    bot._export_forms_points()

            elif args[0] == 'check_leaderboards':
                leader_board = sorted(bot.forms_points.items(), key=lambda x: x[1])
                leader_board_str = ''
                for user_id, score in leader_board:
                    try:
                        user_obj = await ctx.guild.fetch_member(int(user_id))
                        username = user_obj.name
                        leader_board_str += f'{username}: {score} \n'
                    except:
                        print(f'Could not find user with id {user_id} in guild {ctx.guild.name}.')
                await ctx.send(f'LEADERBOARD: \n\n {leader_board_str}')

            elif args[0] == 'cleared_prompt':
                prompt = _get_gpt_prompt(" ".join(args[1:]), '', base_wavey=False)
                await message.channel.send(f'NOT WAVEY: Generating response with no additional prompting and temperature {bot.temperature}. \n`{prompt}`')
                async with ctx.typing():
                    func = functools.partial(
                        _get_gpt_response, 
                        prompt=prompt, 
                        temperature=bot.temperature, 
                        max_length=bot.max_length
                    )

                    lines = await bot._bot.loop.run_in_executor(None, func)


                    for idx, line in enumerate(lines):
                        if idx == 0:
                            last_msg = await message.channel.send(line, reference=message)
                        else:
                            last_msg = await message.channel.send(line, reference=last_msg)

            elif args[0] == 'cleared_prompt_n_messages':
                n_messages = int(args[1])
                previous_messages_str = await _get_previous_messages(message.channel, n_messages=n_messages)
                prompt = _get_gpt_prompt(" ".join(args[1:]), previous_messages_str, base_wavey=False)
                await message.channel.send(f'NOT WAVEY: Generating response including last {n_messages} messages and temperature {bot.temperature}. \n`{prompt}`')
                async with ctx.typing():
                    func = functools.partial(
                        _get_gpt_response, 
                        prompt=prompt, 
                        temperature=bot.temperature, 
                        max_length=bot.max_length
                    )

                    lines = await bot._bot.loop.run_in_executor(None, func)


                    for idx, line in enumerate(lines):
                        if idx == 0:
                            last_msg = await message.channel.send(line, reference=message)
                        else:
                            last_msg = await message.channel.send(line, reference=last_msg)
            ### This is a command
            else:
                async with ctx.typing():
                    previous_messages_str = await _get_previous_messages(
                        message.channel,
                        n_messages=10,
                        n_characters=500
                    )
                    prompt = _get_gpt_prompt(message.clean_content, previous_messages_str, base_wavey=True)

                    print(f'Generating response to {message.clean_content} with temperature {bot.temperature}')
                    func = functools.partial(
                        _get_gpt_response,
                        prompt=prompt,
                        temperature=bot.temperature,
                        max_length=bot.max_length
                    )
                    lines = await bot._bot.loop.run_in_executor(None, func)

                    for idx, line in enumerate(lines):
                        if idx == 0:
                            last_msg = await message.channel.send(line, reference=message)
                        else:
                            last_msg = await message.channel.send(line, reference=last_msg)

        elif message.author != bot._bot.user:
            
            previous_messages_str = await _get_previous_messages(
                message.channel,
                n_messages=10,
                n_characters=500
            )
            print(f'Generating response to {message.clean_content} with temperature {bot.temperature}')
            lines = _get_gpt_response(
                question=message.clean_content, 
                previous_messages_str=previous_messages_str,
                temperature=bot.temperature,
                max_length=bot.max_length
            )
            for idx, line in enumerate(lines):
                await message.channel.send(line)

    ### This is where we'd add a rare chance for the bot to speak up unprompted



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

@bot._bot.hybrid_command(name='wavey', description='Asks a question to the bot')
async def wavey(ctx, *, args):
    question = args
    print(f'Asking question: {question}')
    previous_messages_str = await _get_previous_messages(
        ctx.channel,
        n_messages=10,
        n_characters=500
    )
    try:
        lines = _get_gpt_response(
            question=question, 
            previous_messages_str=previous_messages_str, 
            temperature=bot.temperature,
            max_length=bot.max_length
        )
        for idx, line in enumerate(lines):
            await ctx.send(line)
    except:
        print(traceback.format_exc())


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