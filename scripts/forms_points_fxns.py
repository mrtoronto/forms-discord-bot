import logging
logger = logging.getLogger('FORMS_BOT')

async def _give_forms_points(wavey_input_data):
    forms_points_dict = wavey_input_data['bot'].forms_points
    sending_name = wavey_input_data['message'].author.name
    sending_member = await wavey_input_data['bot'].member_converter.convert(wavey_input_data['ctx'], sending_name)
    sending_member_id_str = str(sending_member.id)
    amount = float(wavey_input_data['args'][1])
    forms_points_dict[sending_member_id_str] = forms_points_dict.get(sending_member_id_str, 0) + amount
    return {
        'forms_points_dict': forms_points_dict, 
        'reply': {
            'channel': wavey_input_data['message'].channel, 
            'text': f'User {sending_name} sent {amount} to {sending_name}. {sending_name} now has {forms_points_dict[sending_member_id_str]} forms points.'
    }}

async def _tip_forms_points(wavey_input_data):
    amount = float(wavey_input_data['args'][2])
    if amount < 0:
        return {
            'reply': {
                'channel': wavey_input_data['message'].channel, 
                'text': f'Cannot tip negative forms points.'
        }
    }
    forms_points_dict = wavey_input_data['bot'].forms_points
    sending_name = wavey_input_data['message'].author.name
    sending_member = await wavey_input_data['bot'].member_converter.convert(wavey_input_data['ctx'], sending_name)
    sending_member_id_str = str(sending_member.id)
    
    receiving_member_str = wavey_input_data['args'][1]
    receiving_member = await wavey_input_data['bot'].member_converter.convert(wavey_input_data['ctx'], receiving_member_str.replace('@', ''))
    receiving_member_id = str(receiving_member.id)
    
    if sending_member_id_str not in forms_points_dict:
        return {
            'reply': {
                'channel': wavey_input_data['message'].channel, 
                'text': f'User {wavey_input_data["ctx"].message.author} has no points.'}
            }
    elif forms_points_dict[sending_member_id_str] < amount:
        return {
            'reply': {
            'channel': wavey_input_data['message'].channel, 
            'text': f'User {wavey_input_data["ctx"].message.author} has insufficient points.'}
        }
    else:
        forms_points_dict[sending_member_id_str] = forms_points_dict.get(sending_member_id_str, 0) - amount
        forms_points_dict[receiving_member_id] = forms_points_dict.get(receiving_member_id, 0) + amount
    return {
        'forms_points_dict': forms_points_dict, 
        'reply': {
            'channel': wavey_input_data["message"].channel, 
            'text': f'User {sending_name} sent {amount} to {receiving_member.name}. {sending_name} now has {forms_points_dict[sending_member_id_str]} forms points. {receiving_member.name} now has {forms_points_dict[receiving_member_id]} forms points.' 
            }
        }

async def _check_leaderboards(data):
    leader_board = sorted(data['bot'].forms_points.items(), key=lambda x: x[1])
    leader_board_str = ''
    for user_id, score in leader_board:
        try:
            user_obj = await data['ctx'].guild.fetch_member(int(user_id))
            username = user_obj.name
            leader_board_str += f'{username}: {score} \n'
        except:
            logger.info(f'Could not find user with id {user_id} in guild {data["ctx"].guild.name}.')
    return {
        'reply': {
            'channel': data['message'].channel, 
            'text': f'LEADERBOARD: \n\n {leader_board_str}'
        }
    }
