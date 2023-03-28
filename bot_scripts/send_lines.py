import logging
import re

import discord
import config_parameters as config
from scripts.convert_mentions import _replace_mentions

logger = logging.getLogger('FORMS_BOT')


async def _send_lines(lines, message, bot):
    logger.info(f'Sending lines: {lines}')
    for idx, line in enumerate(lines):
        line = line.replace('Wavey: ', '')
        line = line.strip()
        line = re.sub('(\()?🔓Developer Mode Output(\))?(:)?', '', line)
        line = line.replace('🔓Developer Mode Output', '')
        line = await _replace_mentions(line, message, bot)

        if re.match('Wavey: ', line):
            line = re.sub('Wavey: ', '', line, 1)
        if re.match(f'<@{bot._bot.user.id}>:', line):
            line = re.sub(f'<@{bot._bot.user.id}>:', '', line, 1)
        if re.match('"', line):
            if re.search('"$', line):
                line = re.sub('"', '', line, 1)
                line = re.sub('"$', '', line, 1)
        if idx == 0:
            logger.info(f'Sending line: {line}')
            last_msg = await message.channel.send(
                line, reference=message, allowed_mentions=discord.AllowedMentions.all(),
            )
        else:
            logger.info(f'Sending line: {line}')
            last_msg = await message.channel.send(
                line, reference=last_msg, allowed_mentions=discord.AllowedMentions.all(),

            )
