import time
import openai

import logging

logger = logging.getLogger('FORMS_BOT')

def _base_wavey(prompt_type, previous_messages_str=None):
    if prompt_type == 'command':
        return """Wavey is a cheeky, sarcastic but caring robot tasked with distracting and annoying the kind people of the Forms Discord Server. 

They have been asked the following question. Before the question they are given some conversation history. Generate a response to the user. """
    elif prompt_type == 'mention':
        return """You are Wavey. A cheeky, sarcastic but caring robot tasked with distracting and annoying the kind people of the Forms Discord Server. 

You hear your name mentioned in a conversation. Before the question you are given some conversation history. Generate a witty or cheeky addition to the conversation. """

def _get_gpt_prompt(question, previous_messages_str, prompt_type, base_wavey=True):
    if base_wavey:
        prompt = _base_wavey(prompt_type)
    else:
        prompt = ''

    if previous_messages_str:
        prompt += f"\n\nHISTORY:\n{previous_messages_str}"
    else:
        prompt += f"\n\n{question}"
    prompt += f"\n\nWavey:"
    print(f'Prompt: \n{prompt}')
    return prompt

def _get_gpt_response(prompt, temperature, max_length):
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
    logger.info(f'Generate response:\n{lines} - {response.usage}')
    return {
        'lines': lines,
        'usage': response.usage
    }