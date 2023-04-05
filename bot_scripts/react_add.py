import asyncio
import logging

import discord
import config_parameters as config
from bot_scripts.send_lines import _send_lines
from oa_api import _get_gpt_prompt, _get_gpt_response
from scripts.process_wavey_commands import _send_quote_tweet, _send_tweet
from scripts.twitter_utils import _generate_reply_to_tweet

logger = logging.getLogger('FORMS_BOT')


async def _on_raw_reaction_add(payload, bot):
    channel = await bot._bot.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    user = await message.guild.fetch_member(payload.user_id)
    emoji = payload.emoji
    if message.channel.id == config.INFLUENCER_TWITTER_CHANNEL_ID:
        logger.info(f'Reacted to influencer tweet - {emoji.name}')
        ### if the emoji is the saluting face
        if emoji.name == '🫡' or emoji.name == 'salute':
            async with channel.typing():
                try:
                    message_text = message.content
                    tweet_text = message_text.split('```')[-2]
                    reply_to_tweet_id = message_text.split('\n')[1].split('/')[-1]


                    tweet_text = tweet_text.replace(u'\u2642', '')
                    tweet_text = tweet_text.strip()

                except:
                    logger.warning(f'Failed to get tweet text from {message.content}')
                    return
                try:
                    logger.info(f'Replying to tweet {reply_to_tweet_id} with {tweet_text}')
                    return _send_tweet(
                        tweet_text, 
                        channel=channel,  
                        reply_to_tweet_id=reply_to_tweet_id
                    )
                except:
                    logger.warning(f'Failed to send tweet {tweet_text}')
                
        elif emoji.name == '📣' or emoji.name == 'mega':
            async with channel.typing():
                try:
                    message_text = message.content
                    tweet_text = message_text.split('```')[-2]
                    tweet_link = message_text.split('\n')[1]
                    reply_to_tweet_id = tweet_link.split('/')[-1]

                    tweet_text = tweet_text.replace(u'\u2642', '')
                    tweet_text = tweet_text.strip()                    

                except:
                    logger.warning(f'Failed to get tweet text from {message.content}')
                    return
                try:
                    logger.info(f'Quote tweeting {reply_to_tweet_id} with {tweet_text}')
                    return _send_quote_tweet(
                        tweet_text, 
                        tweet_link=tweet_link,
                        channel=channel, 
                        reply_to_tweet_id=reply_to_tweet_id
                    )
                except:
                    logger.warning(f'Failed to send tweet {tweet_text}')

        elif emoji.name == '🔁' or emoji.name == 'repeat':
            ### Make the bot type while it processes the request
            async with channel.typing():
                message_text = message.content
                username = message_text.split('\n')[1].split('/')[-3]
                reply_to_tweet_id = message_text.split('\n')[1].split('/')[-1]
                original_tweet_text = "\n".join([i for i in message_text.split('\n') if i[0] == '>']).replace('> ', '')
                tweet = {
                    'id': reply_to_tweet_id,
                    'text': original_tweet_text,
                }
                logger.info(f'tweet: {tweet}')
                body = await _generate_reply_to_tweet(tweet, username)
                logger.info(f'body: {body}')
                body = body.strip()
                msg = await channel.send(body)
                await asyncio.sleep(1)
                await msg.edit(suppress=True)


    if payload.message_id == config.ALPHA_OPT_IN_MESSAGE_ID and emoji.is_custom_emoji() and emoji.name in config.ALPHA_REACT_IDS:
        logger.info(f'Reacted')
        alpha_role = user.get_role(config.ALPHA_ROLE_ID)
        if alpha_role:
            logger.info(f'User {user.name} already has alpha role')
            return
        else:
            alpha_role = message.guild.get_role(config.ALPHA_ROLE_ID)
            logger.info(f'Giving alpha role to {user.name}')
            await user.add_roles(alpha_role)
    elif payload.message_id == config.NSFWAVEY_OPT_IN_MESSAGE_ID and emoji.name in config.NSFWAVEY_REACT_IDS:
        logger.info(f'Reacted to NSFWavey opt-in')
        nsfwavey_role = user.get_role(config.NSFWAVEY_ROLE_ID)
        if nsfwavey_role:
            logger.info(f'User {user.name} already has NSFWavey role')
            return
        else:
            nsfwavey_role = message.guild.get_role(config.NSFWAVEY_ROLE_ID)
            logger.info(f'Giving NSFWavey role to {user.name}')
            await user.add_roles(nsfwavey_role)
    elif emoji.is_custom_emoji() and emoji.name in config.ALPHA_REACT_IDS:
        if message.id in bot.sent_alpha:
            return
        
        if message.id in bot.pending_alpha:
            bot.pending_alpha[message.id] += 1
        
        else:
            bot.pending_alpha[message.id] = 1

        if bot.pending_alpha[message.id] >= bot.GWP['alpha_threshold']:
            alpha_role = message.guild.get_role(config.ALPHA_ROLE_ID)
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

            await _send_lines(gpt_output['lines'], message, bot._bot)