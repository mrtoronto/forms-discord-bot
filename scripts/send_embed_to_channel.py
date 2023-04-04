import discord
from scripts.convert_mentions import _replace_mentions

import logging

logger = logging.getLogger('FORMS_BOT')

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