from datetime import datetime, time, timezone
import re
import traceback
import openai

# Load your API key from an environment variable or secret management service

import asyncio
import json
import discord
from discord.ext import commands
import pytz
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
            logger.info(f'Removing alpha role from {user.name}')
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
    bot.genesis_invite_uses = await bot.update_genesis_invite_use_count()
    logger.info(f'Logged in as {bot._bot.user} (ID: {bot._bot.user.id})')
    logger.info(f'Genesis invite uses: {bot.genesis_invite_uses}')
    logger.info('------')

async def _send_lines(lines, message):
    logger.info(f'Sending lines: {lines}')
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
            logger.info(f'Sending line: {line}')
            last_msg = await message.channel.send(
                line, reference=message, allowed_mentions=discord.AllowedMentions.all(),
            )
        else:
            logger.info(f'Sending line: {line}')
            last_msg = await message.channel.send(
                line, reference=last_msg, allowed_mentions=discord.AllowedMentions.all(),

            )

    

@bot._bot.event
async def on_message(message):
    now = datetime.now(tz=pytz.utc).time()
    if message.channel.id == config.NSFWAVEY_CHANNEL_ID and now > time(0, 0, 0) and now < time(10, 0, 0):
        NSFWavey = True
    else:
        NSFWavey = False
    if bot._bot.user in message.mentions:
        ctx = await bot._bot.get_context(message)        
        args = re.split("( +|\n+)", message.clean_content)
        args = [arg for arg in args if arg.strip() != '']
        if args[0] == f'@{bot._bot.user.name}':
            success = False
            retry_count = 0
            while (not success) and (retry_count < 5):
                async with ctx.typing():
                    try:
                        wavey_reply = await asyncio.wait_for(
                            _process_wavey_command(
                                bot=bot, 
                                message=message, 
                                args=args[1:],
                                prompt_type='command',
                                NSFWavey=NSFWavey
                            ), timeout=20)

                        success = True

                    except asyncio.TimeoutError as e:
                        logger.warning(f'Wavey timed out {retry_count} times for {message.author}\'s mention {e}- {args}')
                        retry_count += 1
            if not success:
                logger.warning(f'Wavey failed to respond to {message.author}\'s mention - {args}')
                await ctx.send("I got distracted... Remind me what you wanted...?")
                
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
                            reference=value.get('reference'),
                            allowed_mentions=discord.AllowedMentions.all()
                        )
                    elif 'text_lines' in value:
                        lines = value['text_lines']
                        await _send_lines(lines, message)
                    elif 'embed' in value:
                        channel_to_send = value['channel']
                        embed = value['embed']
                        try:
                            await channel_to_send.send(
                                embed=embed,
                                allowed_mentions=discord.AllowedMentions.all(),
                            )
                            genesis_role = message.guild.get_role(1072547064271077436)
                            logger.info(f'Genesis role: {genesis_role.mention}')
                        except Exception as e:
                            await ctx.send(
                                f'I tried to send an embed but I can\'t. {e}'
                            )



        elif message.author != bot._bot.user:
            success = False
            retry_count = 0
            while (not success) and (retry_count < 5):
                async with ctx.typing():
                    try:
                        wavey_reply = await asyncio.wait_for(
                            _process_wavey_command(
                                bot=bot, 
                                message=message, 
                                args=args[1:],
                                prompt_type='mention',
                                NSFWavey=NSFWavey
                            ), timeout=20)
                        print(wavey_reply)
                        success = True

                    except asyncio.TimeoutError as e:
                        logger.warning(f'Wavey timed out {retry_count} times for {message.author}\'s mention {e}- {args}')
                        retry_count += 1
                
            if not success:
                logger.warning(f'Wavey failed to respond to {message.author}\'s mention - {args}')
                await ctx.send("Oops I got distracted... Remind me what you wanted...?")
                
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
                            reference=value.get('reference'),
                            allowed_mentions=discord.AllowedMentions.all()
                        )
                    elif 'text_lines' in value:
                        lines = value['text_lines']
                        await _send_lines(lines, message)
                    elif 'embed' in value:
                        channel_to_send = value['channel']
                        embed = value['embed']
                        try:
                            await channel_to_send.send(
                                embed=embed,
                                allowed_mentions=discord.AllowedMentions.all()
                            )

                        except Exception as e:
                            await ctx.send(
                                f'I tried to send an embed but I can\'t. {e}'
                            )
            

    ### This is where we'd add a rare chance for the bot to speak up unprompted

#Events
@bot._bot.event
async def on_member_update(before, after):

    genesis_member_role_id = 1072547064271077436
    team_role_id = 1072543560915746826
    wavey_role_id = 1072632909078462597
    con_category_id = 1078710998808141945

    if after.get_role(genesis_member_role_id) is not None and before.get_role(genesis_member_role_id) is None:
        categories = after.guild.categories
        team_role = after.guild.get_role(team_role_id)
        wavey_role = after.guild.get_role(wavey_role_id)
        con_category = [c for c in categories if c.id == con_category_id][0]
        logger.info(f'Running event on_member_update for {after} with {team_role} & {wavey_role} in {con_category}')

        user_id = after.id
        bot.forms_points[str(user_id)] = 1000
        
        # Create a new private voice channel for the user
        await after.guild.create_text_channel(
            name=f"☎️┃{after.display_name}-hotline",
            category=con_category,
            overwrites={
                after.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                after: discord.PermissionOverwrite(read_messages=True),
                team_role: discord.PermissionOverwrite(read_messages=True),
                wavey_role: discord.PermissionOverwrite(read_messages=True, read_message_history=True)
            },
            position=0,
            reason='Creating a private channel for the new user'
        )


@bot._bot.event
async def on_member_join(member):
    """
    https://discord.gg/8zepXuy5au
    """
    logger.info(f'Running event on_member_join for {member}')

    ### Check whether genesis invite was used
    old_count = bot.genesis_invite_uses

    new_count = await bot.update_genesis_invite_use_count()

    logger.info(f'Genesis invite use count: {old_count} -> {new_count}')

    if old_count != new_count:
        logger.info(f'Genesis invite used by {member}')
        await member.add_roles(member.guild.get_role(1079479548950880378))
        await member.add_roles(member.guild.get_role(1072547064271077436))

    bot.genesis_invite_uses = new_count

    


def _run_discord_bot():
    bot._bot.run(DISCORD_TOKEN)