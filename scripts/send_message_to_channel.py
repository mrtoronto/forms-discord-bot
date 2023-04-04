import re
from scripts.convert_mentions import _replace_mentions

import logging

logger = logging.getLogger('FORMS_BOT')

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

        try:
            message_text = wavey_input_data["message"].content.split('---')[1]
        except:
            return {
                'reply': {
                    'channel': wavey_input_data['message'].channel,
                    'text': f'Could not find message text. Please format your message like this: `@Wavey send_message_to_channel {channel_id} --- message text`'
                }
            }
        
        message_text = await _replace_mentions(message_text, wavey_input_data['message'], wavey_input_data['bot'])
        logger.info(f'Sending message to channel {channel_id} with text {message_text} and image {image}.')
        return {'reply': {
                'channel': channel, 
                'text': message_text,
                'file': image
            }
        }
    else:
        return {
            'reply': {
                'channel': wavey_input_data['message'].channel, 
                'text': f'Could not find channel with id {channel_id}'
            }
        }