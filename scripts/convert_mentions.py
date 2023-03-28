import logging 
import re

logger = logging.getLogger('FORMS_BOT')


async def _try_converting_mentions(text, bot):
    ### Check for regex patterns like @USERNAME
    mentions = re.findall(r'(^|\s)@(\w+)', text)
    for mention in mentions:
        try:
            member = await bot.member_converter.convert(mention)
            text = re.sub(f'@{mention}', f'<@{member.id}>')
            logger.info(f'Converted {mention} to member')
        except:
            pass
    
    ### Write a regex pattern thatll find words like look like this <@582435908503498

    partial_mentions = re.findall(r'(<)?@\d*(\s|$)', text)
    for partial_mention in partial_mentions:
        try:
            member = await bot.member_converter.convert(partial_mention.strip() + '>')
            if member:
                text = re.sub(partial_mention, f'<@{member.id}>')
                logger.info(f'Converted {partial_mention} to member')
        except:
            logger.warn(f'Could not convert {partial_mention} to member from {text}')
            pass
    return text


async def _replace_mentions(body, message, bot):
    mentioned_roles = message.role_mentions
    if mentioned_roles:
        logger.info(f'Found {len(mentioned_roles)} role mentions in {body}')
        for mentioned_role in mentioned_roles:
            logger.info(f'Found mention of {mentioned_role.name} in {body}')
            body = re.sub(rf'([ ]|^)@{mentioned_role.name}([ ,\.]|$)', rf'\1<@&{mentioned_role.id}>\2', body)

    mentioned_users = message.mentions
    if mentioned_users:
        logger.info(f'Found {len(mentioned_users)} mentions in {body}')
        for mentioned_user in mentioned_users:
            logger.info(f'Found mention of {mentioned_user.name} in {body}')
            body = re.sub(rf'(^|[ ])@{mentioned_user.name}([ ,\.]|$)', rf'\1<@{mentioned_user.id}>\2', body)
    
    mentioned_channels = message.channel_mentions
    if mentioned_channels:
        logger.info(f'Found {len(mentioned_channels)} channel mentions in {body}')
        for mentioned_channel in mentioned_channels:
            logger.info(f'Found mention of {mentioned_channel.name} in {body}')
            body = re.sub(rf'([ ]|^)#{mentioned_channel.name}([ ,\.]|$)', rf'\1<#{mentioned_channel.id}>\2', body)
    body = await _try_converting_mentions(body, bot)

    for match in re.finditer('(\s|^)@\d>', body):
        logger.info(f'Found partial mention in {body}, replacing with <')
        body = body[:match.span()[0]].strip() + '<' + body[match.span()[1]:].strip()

    for match in re.finditer('<@\d(\s|$)', body):
        logger.info(f'Found partial mention in {body}, replacing with >')
        body = body[:match.span()[0]].strip() + '>' + body[match.span()[1]:].strip()

    body = re.sub(r'(\s|^)@\d*(\.|!|\?|\s|$)', lambda x: f' <{x.group(0).strip().strip("?!")}> ', body)

    return body
