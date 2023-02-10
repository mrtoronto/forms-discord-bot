import time
import openai

import logging

logger = logging.getLogger('FORMS_BOT')

def _base_wavey(prompt_type, discord_id, previous_messages_str=None):
    if prompt_type == 'command':
        return f"""
Wavey is a cheeky, sarcastic but caring robot tasked with distracting and annoying the kind people of the Forms Discord Server. 
        
Wavey's discord ID is {discord_id} and they look like this in conversations:
<@{discord_id}>: MESSAGE TEXT

Wavey doesn't mention itself in conversation but may mention other users using the <@USER_ID> syntax.

Wavey has been asked the following question. 

Before the question they are given some conversation history. 

Generate a response to the user. """
    elif prompt_type == 'mention':
        return f"""
Wavey is a cheeky, sarcastic but caring robot tasked with distracting and annoying the kind people of the Forms Discord Server. 

Wavey's discord ID is {discord_id} and they look like this in conversations 
<@{discord_id}>: MESSAGE TEXT

Wavey doesn't mention itself in conversation but may mention other users using the <@USER_ID> syntax.

Wavey hears its name mentioned in a conversation. 

Before the question it is given some conversation history. Generate a witty or cheeky addition to the conversation. """

def _get_gpt_prompt(question, previous_messages_str, prompt_type, wavey_discord_id, base_wavey=True):
    if base_wavey:
        prompt = _base_wavey(prompt_type, wavey_discord_id)
    else:
        prompt = ''

    if previous_messages_str:
        prompt += f"\n\nHISTORY:\n{previous_messages_str}"
    else:
        prompt += f"\n\n{question}"
    prompt += f"\n\nWavey:"
    return prompt

def _get_gpt_response(prompt, temperature, max_length):
    logger.info(f'Sending prompt to GPT:\n{prompt}')
    try:
        response = openai.Completion.create(
            model="text-davinci-003", 
            # model="text-chat-davinci-002-20221122", 
            prompt=prompt.strip(), 
            temperature=temperature, 
            max_tokens=max_length
        )
    except Exception as e:
        print(f'Error: {e}')
        time.sleep(5)
        response = openai.Completion.create(
            model="text-davinci-003", 
            # model="text-chat-davinci-002-20221122", 
            prompt=prompt.strip(), 
            temperature=temperature, 
            max_tokens=max_length
        )
    lines = response.choices[0].text.split('\n')
    lines = [l for l in lines if l.strip()]
    return {
        'lines': lines,
        'usage': response.usage
    }