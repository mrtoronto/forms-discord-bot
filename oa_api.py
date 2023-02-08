import time
import openai

def _get_gpt_response(question, previous_messages_str, temperature, max_length):
    prompt = f"""You are Wavey. A cheeky, sarcastic but caring robot tasked with distracting and annoying the kind people of the Forms Discord Server. 

You have been asked the following question. Before the question you are given some conversation history. Generate a response to the user. 

HISTORY:
{previous_messages_str}

QUESTION TO RESPOND TO: 
{question}

Wavey: """

    print(f'Prompt: \n{prompt}')
    try:
        response = openai.Completion.create(
            model="text-davinci-003", 
            prompt=prompt.strip(), 
            temperature=temperature, 
            max_tokens=max_length
        )
    except Exception as e:
        print(f'Error: {e}')
        time.sleep(5)
        response = openai.Completion.create(
            model="text-davinci-003", 
            prompt=prompt.strip(), 
            temperature=temperature, 
            max_tokens=max_length
        )
    lines = response.choices[0].text.split('\n')
    lines = [l for l in lines if l.strip()]
    return lines