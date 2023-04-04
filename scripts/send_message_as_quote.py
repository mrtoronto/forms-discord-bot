from scripts.convert_mentions import _replace_mentions

import discord

import logging

logger = logging.getLogger('FORMS_BOT')

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
        try:
            message_text = wavey_input_data["message"].content.split('---')[1]
        except:
            return {
                'reply': {
                    'channel': wavey_input_data['message'].channel,
                    'text': f'Could not find message text. Please format your message like this: `@Wavey send_message_as_quote {message_id} --- message text`'
                }
            }
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
