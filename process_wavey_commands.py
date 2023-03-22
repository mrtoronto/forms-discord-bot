import logging
import asyncio
import functools
import random
import re

import discord
from oa_api import _get_gpt_prompt, _get_gpt_response
logger = logging.getLogger('FORMS_BOT')

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
    
    ### Write a regex pattern thatll find words like look like this <@582435908503498

    partial_mentions = re.findall(r'(<)?@\d*(\s|$)', text)
    for partial_mention in partial_mentions:
        try:
            member = await bot.member_converter.convert(partial_mention.strip() + '>')
            if member:
                text = re.sub(partial_mention, f'<@{member.id}>')
                logger.info(f'Converted {partial_mention} to member')
        except:
            logger.warn(f'Could not convert {partial_mention} to member from {text}')
            pass
    return text


async def _replace_mentions(body, message, bot):
    mentioned_roles = message.role_mentions
    if mentioned_roles:
        logger.info(f'Found {len(mentioned_roles)} role mentions in {body}')
        for mentioned_role in mentioned_roles:
            logger.info(f'Found mention of {mentioned_role.name} in {body}')
            body = re.sub(rf'([ ]|^)@{mentioned_role.name}([ ,\.]|$)', rf'\1<@&{mentioned_role.id}>\2', body)

    mentioned_users = message.mentions
    if mentioned_users:
        logger.info(f'Found {len(mentioned_users)} mentions in {body}')
        for mentioned_user in mentioned_users:
            logger.info(f'Found mention of {mentioned_user.name} in {body}')
            body = re.sub(rf'(^|[ ])@{mentioned_user.name}([ ,\.]|$)', rf'\1<@{mentioned_user.id}>\2', body)
    
    mentioned_channels = message.channel_mentions
    if mentioned_channels:
        logger.info(f'Found {len(mentioned_channels)} channel mentions in {body}')
        for mentioned_channel in mentioned_channels:
            logger.info(f'Found mention of {mentioned_channel.name} in {body}')
            body = re.sub(rf'([ ]|^)#{mentioned_channel.name}([ ,\.]|$)', rf'\1<#{mentioned_channel.id}>\2', body)
    body = await _try_converting_mentions(body, message, bot)

    for match in re.finditer('(\s|^)@\d>', body):
        logger.info(f'Found partial mention in {body}, replacing with <')
        body = body[:match.span()[0]].strip() + '<' + body[match.span()[1]:].strip()

    for match in re.finditer('<@\d(\s|$)', body):
        logger.info(f'Found partial mention in {body}, replacing with >')
        body = body[:match.span()[0]].strip() + '>' + body[match.span()[1]:].strip()

    body = re.sub(r'(\s|^)@\d*(\.|!|\?|\s|$)', lambda x: f' <{x.group(0).strip().strip("?!")}> ', body)

    return body


async def _get_previous_messages(channel, bot, n_messages=20, n_characters=500):
    previous_messages = channel.history(limit=n_messages)
    previous_messages_list = []
    previous_messages_out_list = []
    async for history_message in previous_messages:
        proc_message = history_message.content.strip()
        proc_message = await _replace_mentions(proc_message, history_message, bot)
        previous_messages_list.append(f'<@{history_message.author.id}>: {proc_message}')
        previous_messages_out_list.append([history_message.author.id, f'<@{history_message.author.id}>: {proc_message}'])
    previous_messages_list = previous_messages_list[::-1]
    previous_messages_out_list = previous_messages_out_list[::-1]
    previous_messages_str = '\n'.join(previous_messages_list)[-n_characters:]

    ### Find any pattern like @\d.*( |$) and replace with <@\d>
    previous_messages_str = re.sub(r'(\s|^)@\d*(\.|!|\?|\s|$)', lambda x: f' <{x.group(0).strip().strip("?!")}> ', previous_messages_str)
    return previous_messages_str, previous_messages_out_list

async def _give_forms_points(wavey_input_data):
    forms_points_dict = wavey_input_data['bot'].forms_points
    sending_name = wavey_input_data['message'].author.name
    sending_member = await wavey_input_data['bot'].member_converter.convert(wavey_input_data['ctx'], sending_name)
    sending_member_id_str = str(sending_member.id)
    amount = float(wavey_input_data['args'][1])
    forms_points_dict[sending_member_id_str] = forms_points_dict.get(sending_member_id_str, 0) + amount
    return {
        'forms_points_dict': forms_points_dict, 
        'reply': {
            'channel': wavey_input_data['message'].channel, 
            'text': f'User {sending_name} sent {amount} to {sending_name}. {sending_name} now has {forms_points_dict[sending_member_id_str]} forms points.'
    }}

async def _tip_forms_points(wavey_input_data):
    amount = float(wavey_input_data['args'][2])
    if amount < 0:
        return {
            'reply': {
                'channel': wavey_input_data['message'].channel, 
                'text': f'Cannot tip negative forms points.'
        }
    }
    forms_points_dict = wavey_input_data['bot'].forms_points
    sending_name = wavey_input_data['message'].author.name
    sending_member = await wavey_input_data['bot'].member_converter.convert(wavey_input_data['ctx'], sending_name)
    sending_member_id_str = str(sending_member.id)
    
    receiving_member_str = wavey_input_data['args'][1]
    receiving_member = await wavey_input_data['bot'].member_converter.convert(wavey_input_data['ctx'], receiving_member_str.replace('@', ''))
    receiving_member_id = str(receiving_member.id)
    
    if sending_member_id_str not in forms_points_dict:
        return {
            'reply': {
                'channel': wavey_input_data['message'].channel, 
                'text': f'User {wavey_input_data["ctx"].message.author} has no points.'}
            }
    elif forms_points_dict[sending_member_id_str] < amount:
        return {
            'reply': {
            'channel': wavey_input_data['message'].channel, 
            'text': f'User {wavey_input_data["ctx"].message.author} has insufficient points.'}
        }
    else:
        forms_points_dict[sending_member_id_str] = forms_points_dict.get(sending_member_id_str, 0) - amount
        forms_points_dict[receiving_member_id] = forms_points_dict.get(receiving_member_id, 0) + amount
    return {
        'forms_points_dict': forms_points_dict, 
        'reply': {
            'channel': wavey_input_data["message"].channel, 
            'text': f'User {sending_name} sent {amount} to {receiving_member.name}. {sending_name} now has {forms_points_dict[sending_member_id_str]} forms points. {receiving_member.name} now has {forms_points_dict[receiving_member_id]} forms points.' 
            }
        }

def _set_temperature(wavey_input_data):
    wavey_input_data['GWP']['temperature'] = float(wavey_input_data['args'][1])
    return {
        'GWP': wavey_input_data['GWP'], 
        'reply': {
            'channel': wavey_input_data['message'].channel, 'text': f'Set temperature to {wavey_input_data["GWP"]["temperature"]}.'
        }
    }

def _get_temperature(wavey_input_data):
    return {
        'reply': {'channel': wavey_input_data['message'].channel, 'text': f'Temperature currently set to {wavey_input_data["GWP"]["temperature"]}'}
    }
def _get_max_length(wavey_input_data):
    return {
        'reply': {'channel': wavey_input_data['message'].channel, 'text': f'max_length currently set to {wavey_input_data["GWP"]["max_length"]}'}
    }

def _set_max_length(wavey_input_data):
    wavey_input_data["GWP"]['max_length'] = int(wavey_input_data["args"][1])
    return {
        'GWP': wavey_input_data["GWP"], 
        'reply': {'channel': wavey_input_data['message'].channel, 'text': f'Set max_length to {wavey_input_data["GWP"]["max_length"]}.'}
    }

def _get_alpha_threshold(wavey_input_data):
    return {
        'reply': {
            'channel': wavey_input_data['message'].channel, 
            'text': f'alpha_threshold is currently set to {wavey_input_data["bot"].GWP["alpha_threshold"]}'}
    }

def _set_alpha_threshold(wavey_input_data):
    wavey_input_data["GWP"]['alpha_threshold'] = int(wavey_input_data["args"][1])
    return {
        'GWP': wavey_input_data["GWP"], 
        'reply': {
            'channel': wavey_input_data['message'].channel, 
            'text': f'Set alpha_threshold to {wavey_input_data["GWP"]["alpha_threshold"]}.',
            'GWP': wavey_input_data["GWP"]
        }
    }

async def _send_message_to_channel(wavey_input_data):    

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
        logger.info(f'Sending message to channel {channel_id} with text {message_text} and image {image}.')
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


async def _get_prompt(data):
    previous_messages_str, previous_messages_list = await _get_previous_messages(
        data['message'].channel,
        data['bot'],
        n_messages=10,
        n_characters=500
    )
    if len(data['args']) > 1:

        prompt_type = data['args'][1]
    else:
        prompt_type = 'none'
    user_submitted_prompt = data['message'].content
    user_submitted_prompt = await _replace_mentions(user_submitted_prompt, data['message'], data['bot'])
    prompt = _get_gpt_prompt(
        user_submitted_prompt, 
        previous_messages_str, 
        previous_messages_list=previous_messages_list,
        wavey_discord_id=data['bot']._bot.user.id, 
        prompt_type=prompt_type,
        NSFWavey=False,
        model='gpt-3.5-turbo'
    )

    return {
        'reply': {
            'channel': data['message'].channel, 
            'text': f'NOT WAVEY: Prompt including last 10 messages and temperature {data["GWP"]["temperature"]}. \n`{prompt}`'
        }
    }

async def _get_wavey_reply(data):
    rand = random.random()
    ### Default history characters
    n_chars = 500
    if rand < 0.01:
        n_chars = n_chars * 5
    elif rand < 0.1:
        n_chars = n_chars * 2
    
    if data['NSFWavey'][0] and data['NSFWavey'][1]:
        n_messages = 5
    else:
        n_messages = 20

    previous_messages_str, previous_messages_list = await _get_previous_messages(
        data['message'].channel,
        data['bot'],
        n_messages=n_messages,
        n_characters=n_chars
    )
    prompt = _get_gpt_prompt(
        data['message'].content, 
        previous_messages_str, 
        previous_messages_list=previous_messages_list,
        wavey_discord_id=data['bot']._bot.user.id,
        prompt_type=data['prompt_type'],
        NSFWavey=data['NSFWavey'],
        model='gpt-3.5-turbo'
    )

    loop = asyncio.get_running_loop()
    gpt_output = await loop.run_in_executor(
        None, 
        _get_gpt_response, 
        prompt, 
        data['GWP']['temperature'],
        data['GWP']['max_length'],
        data['bot']._bot.user.id,
        data['NSFWavey'],
        'gpt-3.5-turbo'
    )
    logger.info(f'Generated response to {data["message"].clean_content} with temperature {data["GWP"]["temperature"]} using {gpt_output["usage"]}')
    lines = gpt_output['lines']
    return {'reply': {
        'channel': data['message'].channel, 
        'text_lines': lines
        }
    }

def _help(data):
    user_commands = {f: v for (f, v) in VALID_ARGS_DICT.items() if not v.get('team')}
    user_commands = f'Commands: {", ".join(user_commands.keys())}'
    command_out_string = user_commands
    if data['team_role']:
        command_out_string += '\n\n'
        team_commands = {f: v for (f, v) in VALID_ARGS_DICT.items() if v.get('team')}
        team_commands = f'Team commands: {", ".join(team_commands.keys())}'
        command_out_string += team_commands

    
    return {
        'reply': {
            'channel': data['message'].channel, 
            'text': command_out_string
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
            if not data['team_role'] and VALID_ARGS_DICT[data['args'][1]].get('team'):
                return {
                    'reply': {
                        'channel': data['message'].channel,
                        'text': f'Command `{data["args"][1]}` is a team command.'
                    }
                }
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
    'set_temperature': {
        'f': _set_temperature, 
        'async': False,
        'team': True,
        'help': 'Set the temperature of the GPT-3 response.'
    },
    'get_temperature': {
        'f': _get_temperature, 
        'async': False,
        'team': True,
        'help': 'Get the temperature of the GPT-3 response.'
    },
    'set_max_length': {
        'f': _set_max_length, 
        'async': False,
        'team': True,
        'help': 'Set the max length of the GPT-3 response.'
    },
    'get_max_length': {
        'f': _get_max_length, 
        'async': False,
        'team': True,
        'help': 'Get the max length of the GPT-3 response.'
    },
    'set_alpha_threshold': {
        'f': _set_alpha_threshold, 
        'async': False,
        'team': True,
        'help': 'Set the alpha threshold for repost to Wavey\'s corner.'
    },
    'get_alpha_threshold': {
        'f': _get_alpha_threshold, 
        'async': False,
        'team': True,
        'help': 'Get the alpha threshold for a repost to Wavey\'s corner.'
    },
    'give': {
        'f': _give_forms_points, 
        'async': True,
        'help': 'Give a user some forms points. Example: \n`give @USER 100`',
        'team': True
    },
    'tip': {
        'f': _tip_forms_points, 
        'async': True, 
        'help': 'Tip a user some forms points. Example: \n`tip @USER 100`'
    },
    'send_message_to_channel': {
        'f': _send_message_to_channel, 
        'async': True,
        'help': 'Send a message to a channel. CHANNEL_ID can be substituted for `here` for debugging.Example: \n`send_message_to_channel CHANNEL_ID MESSAGE`',
        'team': True
    },
    'send_embed_to_channel': {
        'f': _send_embed_to_channel, 'async': True,
        'help': 'Send an embed to a channel. CHANNEL_ID can be substituted for `here` for debugging. Example: \n`send_embed_to_channel CHANNEL_ID title:TITLE<END> body:BODY<END> link:LINK<END>`',
        'team': True
    },
    'send_message_as_quote': {
        'f': _send_message_as_quote, 
        'async': True,
        'help': 'Send a reply to a message. Example: \n`send_message_as_quote MESSAGE_ID MESSAGE`',
        'team': True
    },
    'check_leaderboards': {
        'f': _check_leaderboards, 
        'async': True,
        'team': True
    },
    'get_prompt': {
        'f': _get_prompt, 
        'async': True, 
        'help': 'Get a prompt for the bot. Specify a prompt type after the command. Options are mention, command and general. Example: \n`get_prompt mention`',
        'team': True
    },
    'bot_help': {
        'f': _help, 
        'async': False
    },
    'command_help': {
        'f': _command_help, 
        'async': False
    },
}



async def _process_wavey_command(bot, message, args, prompt_type, NSFWavey):
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
        'prompt_type': prompt_type,
        'NSFWavey': NSFWavey
    }
    
    if len(args) and args[0] in VALID_ARGS_DICT:
        logger.info(f'Running valid wavey command: {args[0]}')
        f_data = VALID_ARGS_DICT[args[0]]
        if f_data.get('team', False) and not team_role:
            return {
                'reply': {
                    'channel': message.channel,
                    'text': 'You are not a team member.'
                }
            }
        if f_data['async']:
            return await f_data['f'](wavey_input_data)
        else:
            logger.info(f'Generating response from wavey for text: {args[0]}')
            return f_data['f'](wavey_input_data)

    else:
        if len(args):
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