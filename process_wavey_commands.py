
import asyncio
import functools

import discord
from oa_api import _get_gpt_prompt, _get_gpt_response

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


async def _get_previous_messages(channel, n_messages=10, n_characters=500):
    previous_messages = channel.history(limit=n_messages)
    previous_messages_list = []
    async for history_message in previous_messages:
        proc_message = history_message.clean_content.strip()
        previous_messages_list.append(f'{history_message.author.name}: {proc_message}')
    previous_messages_list = previous_messages_list[::-1]
    previous_messages_str = '\n'.join(previous_messages_list)[-n_characters:]

    return previous_messages_str

async def _give_forms_points(wavey_input_data):
    if not wavey_input_data['team_role']:
        return {'reply': {'channel': wavey_input_data['message'].channel, 'text': 'No team role set.'}}
    forms_points_dict = wavey_input_data['bot'].forms_points
    sending_name = wavey_input_data['message'].author.name
    sending_member = await wavey_input_data['bot'].member_converter.convert(wavey_input_data['ctx'], sending_name)
    sending_member_id_str = str(sending_member.id)
    amount = float(wavey_input_data['args'][1])
    forms_points_dict[sending_member_id_str] = forms_points_dict.get(sending_member_id_str, 0) + amount
    # await ctx.send(f'User {sending_name} sent {amount} to {sending_name}.')
    return {
        'forms_points_dict': forms_points_dict, 
        'reply': {'channel': wavey_input_data['message'].channel, 'text': f'User {sending_name} sent {amount} to {sending_name}.'
    }}

async def _tip_forms_points(wavey_input_data):
    forms_points_dict = wavey_input_data['bot'].forms_points
    sending_name = wavey_input_data['message'].author.name
    sending_member = await wavey_input_data['bot'].member_converter.convert(wavey_input_data['ctx'], sending_name)
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
        # await ctx.send(f'User {sending_name} sent {amount} to {receiving_member.name}.')
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
        return {'reply': {
                'channel': channel, 
                'text': " ".join(wavey_input_data["args"][2:]),
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
    
    full_text = " ".join(wavey_input_data["args"][2:])
    title = full_text.split('title:')[1].split('`')[1]
    body = wavey_input_data['message'].content.split('body:')[1].split('`')[1]
    link = full_text.split('link:')[1].split('`')[1]

    if wavey_input_data['message'].attachments:
        image_url = wavey_input_data['message'].attachments[0].url
    else:
        image_url = None
        
    
    if channel:
        embed = discord.Embed(
            title=title,
            description=body,
            url=link,
            color=0x00ff00
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
        if wavey_input_data["message"].attachments:
            image = await wavey_input_data["message"].attachments[0].to_file()
        else:
            image = None

        try:
            return {'reply': {
                    'channel': channel,
                    'text': " ".join(wavey_input_data["args"][2:]),
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
            print(f'Could not find user with id {user_id} in guild {data["ctx"].guild.name}.')
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
    previous_messages_str = await _get_previous_messages(data['message'].channel, n_messages=n_messages)
    prompt = _get_gpt_prompt(" ".join(data['args'][1:]), previous_messages_str, base_wavey=False)
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
    prompt = _get_gpt_prompt(" ".join(data['args'][1:]), '', base_wavey=False)
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
    previous_messages_str = await _get_previous_messages(
        data['message'].channel,
        n_messages=10,
        n_characters=500
    )
    prompt = _get_gpt_prompt(data['message'].clean_content, previous_messages_str, base_wavey=True)

    return {
        'reply': {
            'channel': data['message'].channel, 
            'text': f'NOT WAVEY: Prompt including last 10 messages and temperature {data["GWP"]["temperature"]}. \n`{prompt}`'
        }
    }

async def _get_wavey_reply(data):
    previous_messages_str = await _get_previous_messages(
        data['message'].channel,
        n_messages=10,
        n_characters=500
    )
    prompt = _get_gpt_prompt(
        data['message'].clean_content, 
        previous_messages_str, 
        base_wavey=True,
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
    print(f'Generated response to {data["message"].clean_content} with temperature {data["GWP"]["temperature"]} using {gpt_output["usage"]}')
    lines = gpt_output['lines']
    return {'reply': {
        'channel': data['message'].channel, 
        'text_lines': lines}
    }

VALID_ARGS_DICT = {
    'set_temperature': {'f': _set_temperature, 'async': False},
    'get_temperature': {'f': _get_temperature, 'async': False},
    'set_max_length': {'f': _set_max_length, 'async': False},
    'get_max_length': {'f': _get_max_length, 'async': False},
    'give_forms_points': {'f': _give_forms_points, 'async': True},
    'tip_forms_points': {'f': _tip_forms_points, 'async': True},
    'send_message_to_channel': {'f': _send_message_to_channel, 'async': True},
    'send_embed_to_channel': {'f': _send_embed_to_channel, 'async': True},
    'send_message_as_quote': {'f': _send_message_as_quote, 'async': True},
    'check_leaderboards': {'f': _check_leaderboards, 'async': True},
    'cleared_prompt_n_messages': {'f': _cleared_prompt_n_messages, 'async': True},
    'cleared_prompt': {'f': _cleared_prompt, 'async': True},
    'get_prompt': {'f': _get_prompt, 'async': True},
    'get_wavey_reply': {'f': _get_wavey_reply, 'async': True},
}

async def _process_wavey_command(bot,message, args):
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
        'prompt_type': 'command'
    }
    if args[0] in VALID_ARGS:
        wavey_reply = {}
        if args[0] == 'set_temperature':
            return _set_temperature(wavey_input_data)
        elif args[0] == 'get_temperature':
            return _get_temperature(wavey_input_data)
        elif args[0] == 'set_max_length':
            return _set_max_length(wavey_input_data)
        elif args[0] == 'get_max_length':
            return _get_max_length(wavey_input_data)
        elif args[0] == 'give':
            return await _give_forms_points(wavey_input_data)
        elif args[0] == 'tip': 
            return await _tip_forms_points(wavey_input_data)
        elif args[0] == 'send_message_to_channel':
            return await _send_message_to_channel(wavey_input_data)
        elif args[0] == 'send_embed_to_channel':
            return await _send_embed_to_channel(wavey_input_data)
        elif args[0] == 'send_message_as_quote':
            return await _send_message_as_quote(wavey_input_data)
        elif args[0] == 'check_leaderboards':
            return await _check_leaderboards(wavey_input_data)
        elif args[0] == 'cleared_prompt':
            return await _cleared_prompt(wavey_input_data)
        elif args[0] == 'cleared_prompt_n_messages':
            return await _cleared_prompt_n_messages(wavey_input_data)
        elif args[0] == 'get_prompt':
            return await _get_prompt(wavey_input_data)

    else:
        print(f'Invalid wavey command: {args[0]}')
        return await _get_wavey_reply(wavey_input_data)


    return wavey_reply

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