import re
import openai

# Load your API key from an environment variable or secret management service

import asyncio
import json
import discord
from discord.ext import commands
from local_settings import DISCORD_TOKEN, OPENAI_API_KEY
import logging
from filelock import FileLock
import config_parameters as config
from string import punctuation
from oa_api import _get_gpt_prompt, _get_gpt_response
from process_wavey_commands import _process_wavey_command, _process_wavey_mention, _replace_mentions, _try_converting_mentions

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

        # self.alpha_threshold = config.ALPHA_REACT_THRESHOLD

        self.pending_alpha = {}
        self.sent_alpha = {1073324858575945748: True}

        self.GWP = {
            'temperature': 0.7,
            'max_length': 300,
            'alpha_threshold': config.ALPHA_REACT_THRESHOLD,
        }

        self.member_converter = commands.MemberConverter()

    def _export_forms_points(self):
        with lock:
            with open('data/forms_points.json', 'w') as f:
                json.dump(self.forms_points, f)

bot = FormsBot()

@bot._bot.event
async def on_raw_reaction_remove(payload):
    channel = await bot._bot.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    user = await message.guild.fetch_member(payload.user_id)
    emoji = payload.emoji
    if payload.message_id == 1074408946762268763 :
        reacted_user_ids = set()
        logger.info(f'Reacted')
        for reaction in message.reactions:
            reacted_users = reaction.users()
            async for reacting_user in reacted_users:
                reacted_user_ids.add(reacting_user.id)

        if user.id not in reacted_user_ids:
        
            alpha_role = message.guild.get_role(1073331675397898281)
            print(f'Removing alpha role from {user.name}')
            await user.remove_roles(alpha_role)

@bot._bot.event
async def on_raw_reaction_add(payload):
    channel = await bot._bot.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    user = await message.guild.fetch_member(payload.user_id)
    emoji = payload.emoji
    if payload.message_id == 1074408946762268763 and emoji.is_custom_emoji() and emoji.name in config.ALPHA_REACT_IDS:
        logger.info(f'Reacted')
        alpha_role = user.get_role(1073331675397898281)
        if alpha_role:
            logger.info(f'User {user.name} already has alpha role')
            return
        else:
            alpha_role = message.guild.get_role(1073331675397898281)
            logger.info(f'Giving alpha role to {user.name}')
            await user.add_roles(alpha_role)
    elif emoji.is_custom_emoji() and emoji.name in config.ALPHA_REACT_IDS:
        if message.id in bot.sent_alpha:
            return
        
        if message.id in bot.pending_alpha:
            bot.pending_alpha[message.id] += 1
        
        else:
            bot.pending_alpha[message.id] = 1

        if bot.pending_alpha[message.id] >= bot.GWP['alpha_threshold']:
            alpha_role = message.guild.get_role(1073331675397898281)
            ALPHA_CHANNEL = await bot._bot.fetch_channel(config.ALPHA_CHANNEL_ID)
            embed = discord.Embed(
                title=f'Alpha from @{message.author.name}',
                description=f'{message.content}\n\n{message.created_at:%Y / %m / %d %I:%M}',
                color=0xA429D6,
                url = message.jump_url
            )
            embed.set_thumbnail(url=message.author.avatar.url)
            
            await ALPHA_CHANNEL.send(
                f'{alpha_role.mention} {message.author.mention}', 
                embed=embed
            )
            bot.sent_alpha[message.id] = True

            prompt = _get_gpt_prompt(
                message.content, 
                None, 
                wavey_discord_id=bot._bot.user.id,
                user_discord_id=message.author.id,
                prompt_type='alpha'
            )

            loop = asyncio.get_running_loop()
            gpt_output = await loop.run_in_executor(
                None, 
                _get_gpt_response, 
                prompt, 
                bot.GWP['temperature'],
                bot.GWP['max_length'],
                bot._bot.user.id
            )

            await _send_lines(gpt_output['lines'], message)
    return

@bot._bot.event
async def on_ready():
    logger.info(f'Logged in as {bot._bot.user} (ID: {bot._bot.user.id})')
    logger.info('------')

async def _send_lines(lines, message):
    for idx, line in enumerate(lines):
        line = line.replace('Wavey: ', '')
        line = line.strip()
        line = await _replace_mentions(line, message, bot)

        if re.match('Wavey: ', line):
            line = re.sub('Wavey: ', '', line, 1)
        if re.match(f'<@{bot._bot.user.id}>:', line):
            line = re.sub(f'<@{bot._bot.user.id}>:', '', line, 1)
        if re.match('"', line):
            if re.search('"$', line):
                line = re.sub('"', '', line, 1)
                line = re.sub('"$', '', line, 1)
        if idx == 0:
            last_msg = await message.channel.send(
                line, reference=message
            )
        else:
            last_msg = await message.channel.send(
                line, reference=last_msg

            )

    

@bot._bot.event
async def on_message(message):
    if bot._bot.user in message.mentions:
        ctx = await bot._bot.get_context(message)
        
        
        args = re.split("( +|\n+)", message.clean_content)
        args = [arg for arg in args if arg.strip() != '']
        if args[0] == f'@{bot._bot.user.name}':
            async with ctx.typing():
                try:
                    wavey_reply = await asyncio.wait_for(
                        _process_wavey_command(
                            bot=bot, 
                            message=message, 
                            args=args[1:],
                            prompt_type='command'
                        ), timeout=60)
                    # await _process_wavey_reply(wavey_reply, message, ctx)
                    for key, value in wavey_reply.items():
                        if key == 'GWP':
                            bot.GWP.update(value)
                        elif key == 'forms_points_dict':
                            bot.forms_points = value
                            bot._export_forms_points()
                        elif key == 'alpha_threshold':
                            bot.GWP['alpha_threshold'] = value
                        elif key == 'reply':
                            if 'text' in value:
                                channel_to_send = value['channel']
                                reply_text = value['text']
                                reply_text = await _replace_mentions(reply_text, message, bot)
                                await channel_to_send.send(
                                    reply_text,
                                    file=value.get('file'),
                                    reference=value.get('reference')
                                )
                            elif 'text_lines' in value:
                                lines = value['text_lines']
                                await _send_lines(lines, message)
                            elif 'embed' in value:
                                channel_to_send = value['channel']
                                embed = value['embed']
                                try:
                                    await channel_to_send.send(
                                        embed=embed
                                    )
                                except Exception as e:
                                    await ctx.send(
                                        f'I tried to send an embed but I can\'t. {e}'
                                    )

                except asyncio.TimeoutError:
                    await ctx.send("The command timed out.")
                



        elif message.author != bot._bot.user:
            async with ctx.typing():
                try:
                    wavey_reply = await asyncio.wait_for(
                        _process_wavey_command(
                            bot=bot, 
                            message=message, 
                            args=args[1:],
                            prompt_type='mention'
                        ), timeout=60)
                    # await _process_wavey_reply(wavey_reply, message, ctx)
                    for key, value in wavey_reply.items():
                        if key == 'GWP':
                            bot.GWP.update(value)
                        elif key == 'forms_points_dict':
                            bot.forms_points = value
                            bot._export_forms_points()
                        elif key == 'alpha_threshold':
                            bot.GWP['alpha_threshold'] = value
                        elif key == 'reply':
                            if 'text' in value:
                                channel_to_send = value['channel']
                                reply_text = value['text']
                                reply_text = await _replace_mentions(reply_text, message, bot)
                                await channel_to_send.send(
                                    reply_text,
                                    file=value.get('file'),
                                    reference=value.get('reference')
                                )
                            elif 'text_lines' in value:
                                lines = value['text_lines']
                                await _send_lines(lines, message)
                            elif 'embed' in value:
                                channel_to_send = value['channel']
                                embed = value['embed']
                                try:
                                    await channel_to_send.send(
                                        embed=embed
                                    )
                                except Exception as e:
                                    await ctx.send(
                                        f'I tried to send an embed but I can\'t. {e}'
                                    )

                except asyncio.TimeoutError:
                    await ctx.send("The command timed out.")
                
            

    ### This is where we'd add a rare chance for the bot to speak up unprompted

#Events
@bot._bot.event
async def on_member_join(member):
    # Get the moderator role
    categories = member.guild.categories
    team_role = member.guild.get_role(1072543560915746826)
    wavey_role = member.guild.get_role(1072632909078462597)
    con_category = [c for c in categories if c.id == 1074814667588911124][0]
    logger.info(f'Running event on_member_join for {member} with {team_role} & {wavey_role} in {con_category}')

    user_id = member.id
    bot.forms_points[str(user_id)] = 1000
    
    # Create a new private voice channel for the user
    await member.guild.create_text_channel(
        name=f"☎️┃{member.display_name}-hotline",
        category=con_category,
        overwrites={
            member.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True),
            team_role: discord.PermissionOverwrite(read_messages=True),
            wavey_role: discord.PermissionOverwrite(read_messages=True, read_message_history=True)
        },
        position=0,
        reason='Creating a private channel for the new user'
    )


def _run_discord_bot():
    bot._bot.run(DISCORD_TOKEN)