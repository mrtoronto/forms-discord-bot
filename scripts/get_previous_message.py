from scripts.convert_mentions import _replace_mentions
import re


async def _get_previous_messages(channel, bot, n_messages=20, n_characters=500):
    previous_messages = channel.history(limit=n_messages)
    previous_messages_list = []
    previous_messages_out_list = []
    async for history_message in previous_messages:
        proc_message = history_message.content.strip()
        proc_message = await _replace_mentions(proc_message, history_message, bot)
        previous_messages_list.append(f'<@{history_message.author.id}>: {proc_message}')
        previous_messages_out_list.append([history_message.author.id, f'<@{history_message.author.id}>: {proc_message}'])
    previous_messages_list = previous_messages_list[::-1]
    previous_messages_out_list = previous_messages_out_list[::-1]
    previous_messages_str = '\n'.join(previous_messages_list)[-n_characters:]

    ### Find any pattern like @\d.*( |$) and replace with <@\d>
    previous_messages_str = re.sub(r'(\s|^)@\d*(\.|!|\?|\s|$)', lambda x: f' <{x.group(0).strip().strip("?!")}> ', previous_messages_str)
    return previous_messages_str, previous_messages_out_list