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
