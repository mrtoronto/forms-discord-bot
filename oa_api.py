import time
import openai

def _base_wavey():
    return """You are Wavey. A cheeky, sarcastic but caring robot tasked with distracting and annoying the kind people of the Forms Discord Server. 

You have been asked the following question. Before the question you are given some conversation history. Generate a response to the user. """

def _get_gpt_prompt(question, previous_messages_str, base_wavey=True):
    if base_wavey:
        prompt = _base_wavey()
    else:
        prompt = ''

    if previous_messages_str:
        prompt += f"History:\n{previous_messages_str}"

    prompt += f"{question}"
    print(f'Prompt: \n{prompt}')
    return prompt

def _get_gpt_response(prompt, temperature, max_length):
    try:
        response = openai.Completion.create(
            model="text-davinci-002", 
            # model="text-chat-davinci-002-20221122", 
            prompt=prompt.strip(), 
            temperature=temperature, 
            max_tokens=max_length
        )
    except Exception as e:
        print(f'Error: {e}')
        time.sleep(5)
        response = openai.Completion.create(
            model="text-davinci-002", 
            # model="text-chat-davinci-002-20221122", 
            prompt=prompt.strip(), 
            temperature=temperature, 
            max_tokens=max_length
        )
    lines = response.choices[0].text.split('\n')
    lines = [l for l in lines if l.strip()]
    return lines