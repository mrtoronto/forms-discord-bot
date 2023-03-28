import logging
import config_parameters as config

logger = logging.getLogger('FORMS_BOT')

async def _on_raw_reaction_remove(payload, bot):
    channel = await bot._bot.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    user = await message.guild.fetch_member(payload.user_id)
    emoji = payload.emoji
    if payload.message_id == config.ALPHA_OPT_IN_MESSAGE_ID:
        reacted_user_ids = set()
        logger.info(f'Reacted')
        for reaction in message.reactions:
            if reaction.emoji.name and reaction.emoji.name in config.ALPHA_REACT_IDS:
                reacted_users = reaction.users()
                async for reacting_user in reacted_users:
                    reacted_user_ids.add(reacting_user.id)

        if user.id not in reacted_user_ids:
            alpha_role = message.guild.get_role(config.ALPHA_ROLE_ID)
            logger.info(f'Removing alpha role from {user.name}')
            await user.remove_roles(alpha_role)
    elif payload.message_id == config.NSFWAVEY_OPT_IN_MESSAGE_ID:
        reacted_user_ids = set()
        logger.info(f'Reacted')
        for reaction in message.reactions:
            if reaction.emoji in config.NSFWAVEY_REACT_IDS:
                reacted_users = reaction.users()
                async for reacting_user in reacted_users:
                    reacted_user_ids.add(reacting_user.id)

        if user.id not in reacted_user_ids:
            alpha_role = message.guild.get_role(config.NSFWAVEY_ROLE_ID)
            logger.info(f'Removing NSFWavey role from {user.name}')
            await user.remove_roles(alpha_role)