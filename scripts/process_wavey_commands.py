import logging
import asyncio
import functools
import random
import re

import discord
from oa_api import _get_gpt_prompt, _get_gpt_response

from scripts.convert_mentions import _replace_mentions
from scripts.forms_points_fxns import _give_forms_points, _tip_forms_points, _check_leaderboards, _check_balance
from scripts.get_previous_message import _get_previous_messages
from scripts.get_set_params import (
    _get_temperature, 
    _set_temperature, 
    _get_alpha_threshold, 
    _set_alpha_threshold, 
    _get_max_length, 
    _set_max_length
)

from scripts.send_message_to_channel import _send_message_to_channel
from scripts.send_embed_to_channel import _send_embed_to_channel
from scripts.send_message_as_quote import _send_message_as_quote

logger = logging.getLogger('FORMS_BOT')

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
    'check_balance': {
        'f': _check_balance, 
        'async': True,
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

    if " ".join(args).lower() in ['check my balance', 'how many pip do I have', 'pip balance', 'give me my pip balance']:
        return await _check_balance(wavey_input_data)
    
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