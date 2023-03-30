from datetime import datetime
from datetime import time as dt_time
import re
import asyncio
import discord
import pytz
from bot_scripts.send_lines import _send_lines
import logging
import config_parameters as config
from scripts.process_wavey_commands import _process_wavey_command
from scripts.convert_mentions import _replace_mentions

logger = logging.getLogger('FORMS_BOT')

async def _on_message(message, bot):
    await bot._bot.wait_until_ready()
    cog = bot._bot.get_cog('WaveyCog')
    morning_start = cog.morning_start
    night_start = cog.night_start

    now = datetime.now(tz=pytz.utc).time().replace(tzinfo=pytz.utc)
    morning_start_dt = dt_time(morning_start, 0, 0, tzinfo=pytz.utc)
    morning_end_dt = dt_time(morning_start + 6, 0, 0, tzinfo=pytz.utc)
    night_start_dt = dt_time(night_start, 0, 0, tzinfo=pytz.utc)
    night_end_dt = dt_time(night_start + 6, 0, 0, tzinfo=pytz.utc)

    if cog and message.channel.id == config.NSFWAVEY_CHANNEL_ID:
        if now > morning_start_dt and now < morning_end_dt:
            NSFWavey = (True, True)
        elif now > night_start_dt and now < night_end_dt:
            NSFWavey = (True, True)
        else:
            NSFWavey = (True, False)
    else:
        NSFWavey = (False, False)
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
                elif key == 'forms_points_trxns_dict':
                    bot.forms_points_trxns = value
                    bot._export_forms_points()
                elif key == 'alpha_threshold':
                    bot.GWP['alpha_threshold'] = value
                elif key == 'reply':
                    if 'text' in value:
                        channel_to_send = value['channel']
                        reply_text = value['text']
                        reply_text = await _replace_mentions(reply_text, message, bot)

                        if len(reply_text) > 2000:
                            reply_text = reply_text[:2000]


                        await channel_to_send.send(
                            reply_text,
                            file=value.get('file'),
                            reference=value.get('reference'),
                            allowed_mentions=discord.AllowedMentions.all()
                        )
                    elif 'text_lines' in value:
                        lines = value['text_lines']
                        await _send_lines(lines, message, bot)
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
                elif key == 'forms_points_trxns_dict':
                    bot.forms_points_trxns = value
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
                        await _send_lines(lines, message, bot)
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