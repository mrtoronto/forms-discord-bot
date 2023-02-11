import logging
import asyncio
import functools
import re

import discord
from oa_api import _get_gpt_prompt, _get_gpt_response
logger = logging.getLogger('FORMS_BOT')

VALID_ARGS = [
    'set_temperature',
    'get_temperature',
    'set_max_length',
    'get_max_length',
    'give',
    'tip',
    'check_leaderboards',
    'cleared_prompt',
    'cleared_prompt_n_messages',
    'get_prompt',
    'send_message_to_channel',
    'send_message_as_quote',
    'send_embed_to_channel',
]

async def _try_converting_mentions(text, message, bot):
    ### Check for regex patterns like @USERNAME
    mentions = re.findall(r'(^|\s)@(\w+)', text)
    for mention in mentions:
        try:
            member = await bot.member_converter.convert(mention)
            text = re.sub(f'@{mention}', f'<@{member.id}>')
            logger.info(f'Converted {mention} to member')
        except:
            pass
    return text


async def _replace_mentions(body, message, bot):
    mentioned_users = message.mentions
    if mentioned_users:
        body = body.replace(f'@{mentioned_users[0].name}', f'<@{mentioned_users[0].id}>')
    mentioned_channels = message.channel_mentions
    if mentioned_channels:
        body = body.replace(f'#{mentioned_channels[0].name}', f'<#{mentioned_channels[0].id}>')
    body = await _try_converting_mentions(body, message, bot)
    return body


async def _get_previous_messages(channel, bot, n_messages=20, n_characters=500):
    previous_messages = channel.history(limit=n_messages)
    previous_messages_list = []
    async for history_message in previous_messages:
        proc_message = history_message.content.strip()
        proc_message = await _replace_mentions(proc_message, history_message, bot)
        previous_messages_list.append(f'<@{history_message.author.id}>: {proc_message}')
    previous_messages_list = previous_messages_list[::-1]
    previous_messages_str = '\n'.join(previous_messages_list)[-n_characters:]

    return previous_messages_str

async def _give_forms_points(wavey_input_data):
    if not wavey_input_data['team_role']:
        return {'reply': {'channel': wavey_input_data['message'].channel, 'text': 'No team role set.'}}
    forms_points_dict = wavey_input_data['bot'].forms_points
    sending_name = wavey_input_data['message'].author.name
    sending_member = await wavey_input_data['bot'].member_converter(sending_name)
    sending_member_id_str = str(sending_member.id)
    amount = float(wavey_input_data['args'][1])
    forms_points_dict[sending_member_id_str] = forms_points_dict.get(sending_member_id_str, 0) + amount
    return {
        'forms_points_dict': forms_points_dict, 
        'reply': {'channel': wavey_input_data['message'].channel, 'text': f'User {sending_name} sent {amount} to {sending_name}.'
    }}

async def _tip_forms_points(wavey_input_data):
    forms_points_dict = wavey_input_data['bot'].forms_points
    sending_name = wavey_input_data['message'].author.name
    sending_member = await wavey_input_data['bot'].member_converter.convert(sending_name)
    sending_member_id_str = str(sending_member.id)
    
    receiving_member_str = wavey_input_data['args'][1]
    amount = float(wavey_input_data['args'][2])
    receiving_member = await wavey_input_data['bot'].member_converter.convert(wavey_input_data['ctx'], receiving_member_str.replace('@', ''))
    receiving_member_id = str(receiving_member.id)
    
    if sending_member_id_str not in forms_points_dict:
        return {'reply': {'channel': wavey_input_data['message'].channel, 'text': f'User {wavey_input_data["ctx"].message.author} has no points.'}}
    elif forms_points_dict[sending_member_id_str] < amount:
        return {'reply': {'channel': wavey_input_data['message'].channel, 'text': f'User {wavey_input_data["ctx"].message.author} has insufficient points.'}}
    else:
        forms_points_dict[sending_member_id_str] = forms_points_dict.get(sending_member_id_str, 0) - amount
        forms_points_dict[receiving_member_id] = forms_points_dict.get(receiving_member_id, 0) + amount
    return {'forms_points_dict': forms_points_dict, 'reply': {'channel': wavey_input_data["message"].channel, 'text': f'User {sending_name} sent {amount} to {receiving_member.name}.'}}

def _set_temperature(wavey_input_data):
    if not wavey_input_data['team_role']:
        return {
            'reply': {'channel': wavey_input_data['message'].channel, 'text': 'No team role set.'}
        }
    wavey_input_data['GWP']['temperature'] = float(wavey_input_data['args'][1])
    return {
        'GWP': wavey_input_data['GWP'], 
        'reply': {
            'channel': wavey_input_data['message'].channel, 'text': f'Set temperature to {wavey_input_data["GWP"]["temperature"]}.'
        }
    }

def _get_temperature(wavey_input_data):
    if not wavey_input_data['team_role']:
        return {
            'reply': {'channel': wavey_input_data['message'].channel, 'text': 'No team role set.'}
        }
    return {
        'reply': {'channel': wavey_input_data['message'].channel, 'text': f'Temperature currently set to {wavey_input_data["GWP"]["temperature"]}'}
    }
def _get_max_length(wavey_input_data):
    if not wavey_input_data['team_role']:
        return {
            'reply': {'channel': wavey_input_data['message'].channel, 'text': 'No team role set.'}
        }
    return {
        'reply': {'channel': wavey_input_data['message'].channel, 'text': f'max_length currently set to {wavey_input_data["GWP"]["max_length"]}'}
    }

def _set_max_length(wavey_input_data):
    if not wavey_input_data['team_role']:
        return {
            'reply': {'channel': wavey_input_data['message'].channel, 'text': 'No team role set.'}
        }
    wavey_input_data["GWP"]['max_length'] = int(wavey_input_data["args"][1])
    return {
        'GWP': wavey_input_data["GWP"], 
        'reply': {'channel': wavey_input_data['message'].channel, 'text': f'Set max_length to {wavey_input_data["GWP"]["max_length"]}.'}
    }

async def _send_message_to_channel(wavey_input_data):
    if not wavey_input_data['team_role']:
        return {'reply': {'channel': wavey_input_data['message'].channel, 'text': 'No team role set.'}}
    

    try:
        channel_id = int(wavey_input_data["args"][1])
        channel = await wavey_input_data["bot"]._bot.fetch_channel(channel_id)
    except:
        channel = None
    
    if wavey_input_data['args'][1] == 'here':
        channel = wavey_input_data['message'].channel
        channel_id = channel.id
    
    if channel:
        if wavey_input_data['message'].attachments:
            image = await wavey_input_data['message'].attachments[0].to_file()
        else:
            image = None
        message_text = " ".join(wavey_input_data["args"][2:])
        
        message_text = await _replace_mentions(message_text, wavey_input_data['message'], wavey_input_data['bot'])
        
        return {'reply': {
                'channel': channel, 
                'text': message_text,
                'file': image
            }
        }
    else:
        return {'reply': {
                'channel': wavey_input_data['message'].channel, 
                'text': f'Could not find channel with id {channel_id}'
            }
        }

async def _send_embed_to_channel(wavey_input_data):
    if not wavey_input_data['team_role']:
        return {
            'reply': {
                'channel': wavey_input_data['message'].channel, 
                'text': 'No team role set.'
            }
        }
    
    try:
        channel_id = int(wavey_input_data["args"][1])
        channel = await wavey_input_data["bot"]._bot.fetch_channel(channel_id)
    except:
        channel = None
        channel_id = None
    
    if wavey_input_data['args'][1] == 'here':
        channel = wavey_input_data['message'].channel
        channel_id = channel.id

    full_text = wavey_input_data["message"].clean_content
    title = full_text.split('title:')[1].split('<END>')[0]
    body = full_text.split('body:')[1].split('<END>')[0]
    if 'link: ' in full_text:
        link = full_text.split('link:')[1].split('<END>')[1]
    else:
        link = None
    
    body = await _replace_mentions(body, wavey_input_data['message'], wavey_input_data['bot'])
    if wavey_input_data['message'].attachments:
        image_url = wavey_input_data['message'].attachments[0].url
    else:
        image_url = None
        
    
    if channel:
        embed = discord.Embed(
            title=title,
            description=body,
            url=link,
            color=0xA429D6
        )
        if image_url:
            embed.set_image(url=image_url)
        
        return {
            'reply': {
                'channel': channel, 
                'embed': embed
            }
        }
    else:
        return {'reply': {
                'channel': wavey_input_data['message'].channel, 
                'text': f'Could not find channel with id {channel_id}'
            }
        }

async def _send_message_as_quote(wavey_input_data):
    if not wavey_input_data["team_role"]:
        wavey_input_data["ctx"].send('No team role set.')
        return {'reply': {'channel': wavey_input_data['message'].channel, 'text': 'No team role set.'}}
    message_id = int(wavey_input_data["args"][1])
    guild_channels = wavey_input_data["ctx"].guild.channels
    referenced_message = None
    for channel in guild_channels:
        try:
            referenced_message = await channel.fetch_message(message_id)
            break
        except:
            pass
    if not referenced_message:
        return {'reply': {'channel': wavey_input_data['message'].channel, 'text': f'Could not find message with id {message_id}'}}
    
    else:
        message_text = " ".join(wavey_input_data["args"][2:])
        message_text = await _replace_mentions(message_text, wavey_input_data['message'], wavey_input_data['bot'])

        if wavey_input_data["message"].attachments:
            image = await wavey_input_data["message"].attachments[0].to_file()
        else:
            image = None

        try:
            return {'reply': {
                    'channel': channel,
                    'text': message_text,
                    'file': image,
                    'reference': referenced_message
                }
            }
        except discord.errors.Forbidden:
            return {'reply': {
                'channel': wavey_input_data['message'].channel, 
                'text': f'Could not send message to channel {channel.name} bc permission error.'
            }}
        except Exception:
            return {'reply': {'channel': wavey_input_data["message"].channel, 'text': f'Could not send message to channel {channel.name} for other reasons.'}}

async def _check_leaderboards(data):
    if not data['team_role']:
        return {
            'reply': {
                'channel': data['message'].channel, 
                'text': 'No team role set.'
            }
        }
    leader_board = sorted(data['bot'].forms_points.items(), key=lambda x: x[1])
    leader_board_str = ''
    for user_id, score in leader_board:
        try:
            user_obj = await data['ctx'].guild.fetch_member(int(user_id))
            username = user_obj.name
            leader_board_str += f'{username}: {score} \n'
        except:
            logger.info(f'Could not find user with id {user_id} in guild {data["ctx"].guild.name}.')
    return {
        'reply': {
            'channel': data['message'].channel, 
            'text': f'LEADERBOARD: \n\n {leader_board_str}'
        }
    }

async def _cleared_prompt_n_messages(data):
    if not data['team_role']:
        return {
            'reply': {
                'channel': data['message'].channel, 
                'text': 'No team role set.'
            }
        }
    n_messages = int(data['args'][1])
    previous_messages_str = await _get_previous_messages(data['message'].channel, data['bot'], n_messages=n_messages)
    prompt = _get_gpt_prompt(
        " ".join(data['args'][1:]), 
        previous_messages_str, 
        wavey_discord_id=data['bot']._bot.user.id,
        prompt_type='cleared'
    )
    await data['message'].channel.send(
        f'NOT WAVEY: Generating response including last {n_messages} messages and temperature {data["GWP"]["temperature"]}. \n`{prompt}`'
    )
    loop = asyncio.get_running_loop()
    gpt_output = await loop.run_in_executor(
        None, 
        _get_gpt_response, 
        prompt, 
        data['GWP']['temperature'],
        data['GWP']['max_length']
    )
    lines = gpt_output['lines']
    return {
        'reply': {
            'channel': data['message'].channel, 'text_lines': lines
        },
        'usage': gpt_output['usage']
    }


async def _cleared_prompt(data):
    if not data['team_role']:
        # ctx.send('No team role set.')
        return {
            'reply': {
                'channel': data['message'].channel, 
                'text': 'No team role set.'
            }
        }
    prompt = _get_gpt_prompt(
        " ".join(data['args'][1:]), '', 
        wavey_discord_id=data['bot']._bot.user.id, prompt_type='cleared')
    await data['message'].channel.send(f'NOT WAVEY: Generating response with no additional prompting and temperature {data["GWP"]["temperature"]}. \n`{prompt}`')
    loop = asyncio.get_running_loop()
    gpt_output = await loop.run_in_executor(
        None, 
        _get_gpt_response, 
        prompt, 
        data['GWP']['temperature'],
        data['GWP']['max_length']
    )
    lines = gpt_output['lines']
    return {
        'reply': {
            'channel': data['message'].channel, 'text_lines': lines
        },
        'usage': gpt_output['usage']
    }

async def _get_prompt(data):
    if not data['team_role']:
        return {'reply': {'channel': data['message'].channel, 'text': 'No team role set.'}}
    prompt_type = data['args'][1]
    previous_messages_str = await _get_previous_messages(
        data['message'].channel,
        data['bot'],
        n_messages=10,
        n_characters=500
    )
    prompt_type = data['args'][1]
    user_submitted_prompt = data['message'].content
    user_submitted_prompt = await _replace_mentions(user_submitted_prompt, data['message'], data['bot'])
    prompt = _get_gpt_prompt(
        user_submitted_prompt, 
        previous_messages_str, 
        wavey_discord_id=data['bot']._bot.user.id, 
        prompt_type=prompt_type
    )

    return {
        'reply': {
            'channel': data['message'].channel, 
            'text': f'NOT WAVEY: Prompt including last 10 messages and temperature {data["GWP"]["temperature"]}. \n`{prompt}`'
        }
    }

async def _get_wavey_reply(data):
    previous_messages_str = await _get_previous_messages(
        data['message'].channel,
        data['bot'],
        n_messages=20,
        n_characters=2000
    )
    prompt = _get_gpt_prompt(
        data['message'].content, 
        previous_messages_str, 
        wavey_discord_id=data['bot']._bot.user.id,
        prompt_type=data['prompt_type']
    )

    loop = asyncio.get_running_loop()
    gpt_output = await loop.run_in_executor(
        None, 
        _get_gpt_response, 
        prompt, 
        data['GWP']['temperature'],
        data['GWP']['max_length']
    )
    logger.info(f'Generated response to {data["message"].clean_content} with temperature {data["GWP"]["temperature"]} using {gpt_output["usage"]}')
    lines = gpt_output['lines']
    return {'reply': {
        'channel': data['message'].channel, 
        'text_lines': lines}
    }

def _help(data):
    return {
        'reply': {
            'channel': data['message'].channel, 
            'text': f'Commands: {", ".join(VALID_ARGS_DICT.keys())}'
        }
    }

def _command_help(data):
    if data['args'][1] not in VALID_ARGS_DICT:
        return {
            'reply': {
                'channel': data['message'].channel,
                'text': f'Command `{data["args"][1]}` not found.'
            }
        }
    
    else:
        if 'help' in VALID_ARGS_DICT[data['args'][1]]:
            return {
                'reply': {
                    'channel': data['message'].channel,
                    'text': f'Help for command `{data["args"][1]}`: \n{VALID_ARGS_DICT[data["args"][1]]["help"]}'
                }
            }
        else:
            return {
                'reply': {
                    'channel': data['message'].channel,
                    'text': f'Command `{data["args"][1]}` found but does not have help.'
                }
            }

VALID_ARGS_DICT = {
    'set_temperature': {'f': _set_temperature, 'async': False},
    'get_temperature': {'f': _get_temperature, 'async': False},
    'set_max_length': {'f': _set_max_length, 'async': False},
    'get_max_length': {'f': _get_max_length, 'async': False},
    'give': {'f': _give_forms_points, 'async': True},
    'tip': {'f': _tip_forms_points, 'async': True},
    'send_message_to_channel': {
        'f': _send_message_to_channel, 'async': True,
        'help': 'Send a message to a channel. CHANNEL_ID can be substituted for `here` for debugging.Example: \n`send_message_to_channel CHANNEL_ID MESSAGE`'},
    'send_embed_to_channel': {
        'f': _send_embed_to_channel, 'async': True,
        'help': 'Send an embed to a channel. CHANNEL_ID can be substituted for `here` for debugging. Example: \n`send_embed_to_channel CHANNEL_ID title:TITLE<END> body:BODY<END> link:LINK<END>`'},
    'send_message_as_quote': {
        'f': _send_message_as_quote, 'async': True,
        'help': 'Send a reply to a message. Example: \n`send_message_as_quote MESSAGE_ID MESSAGE`'},
    'check_leaderboards': {'f': _check_leaderboards, 'async': True},
    'cleared_prompt_n_messages': {'f': _cleared_prompt_n_messages, 'async': True},
    'cleared_prompt': {'f': _cleared_prompt, 'async': True},
    'get_prompt': {'f': _get_prompt, 'async': True, 'help': 'Get a prompt for the bot. Specify a prompt type after the command. Options are mention, command and general. Example: \n`get_prompt mention`'},
    'get_wavey_reply': {'f': _get_wavey_reply, 'async': True},
    'bot_help': {'f': _help, 'async': False},
    'command_help': {'f': _command_help, 'async': False},
}



async def _process_wavey_command(bot, message, args, prompt_type):
    team_role = discord.utils.get(message.author.roles, name='Team')
    ctx = await bot._bot.get_context(message)
    GWP = bot.GWP
    wavey_input_data = {
        'ctx': ctx,
        'message': message,
        'args': args,
        'bot': bot,
        'team_role': team_role,
        'GWP': GWP,
        'prompt_type': prompt_type
    }
    if args[0] in VALID_ARGS_DICT:
        if VALID_ARGS_DICT[args[0]]['async']:
            return await VALID_ARGS_DICT[args[0]]['f'](wavey_input_data)
        else:
            return VALID_ARGS_DICT[args[0]]['f'](wavey_input_data)

    else:
        logger.info(f'Invalid wavey command: {args[0]}')
        return await _get_wavey_reply(wavey_input_data)

async def _process_wavey_mention(bot, message, args):
    team_role = discord.utils.get(message.author.roles, name='Team')
    ctx = await bot._bot.get_context(message)
    GWP = bot.GWP
    wavey_input_data = {
        'ctx': ctx,
        'message': message,
        'args': args,
        'bot': bot,
        'team_role': team_role,
        'GWP': GWP,
        'prompt_type': 'mention'
    }
    return await _get_wavey_reply(wavey_input_data)