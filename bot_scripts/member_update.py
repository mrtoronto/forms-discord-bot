import discord
import logging

logger = logging.getLogger('FORMS_BOT')

async def _on_member_update(before, after, bot):
    genesis_member_role_id = 1072547064271077436
    team_role_id = 1072543560915746826
    wavey_role_id = 1072632909078462597
    con_category_id = 1091562609884545155

    if after.get_role(genesis_member_role_id) is not None and before.get_role(genesis_member_role_id) is None:
        categories = after.guild.categories
        team_role = after.guild.get_role(team_role_id)
        wavey_role = after.guild.get_role(wavey_role_id)
        con_category = [c for c in categories if c.id == con_category_id][0]
        logger.info(f'Running event on_member_update for {after} with {team_role} & {wavey_role} in {con_category}')

        user_id = after.id
        bot.forms_points[str(user_id)] = 1000
        
        # Create a new private voice channel for the user
        await after.guild.create_text_channel(
            name=f"☎️┃{after.display_name}-hotline",
            category=con_category,
            overwrites={
                after.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                after: discord.PermissionOverwrite(read_messages=True),
                team_role: discord.PermissionOverwrite(read_messages=True),
                wavey_role: discord.PermissionOverwrite(read_messages=True, read_message_history=True)
            },
            position=0,
            reason='Creating a private channel for the new user'
        )


async def _on_member_join(member, bot):
    """
    https://discord.gg/8zepXuy5au
    """
    logger.info(f'Running event on_member_join for {member}')

    ### Check whether genesis invite was used
    old_count = bot.genesis_invite_uses

    new_count = await bot.update_genesis_invite_use_count()

    logger.info(f'Genesis invite use count: {old_count} -> {new_count}')

    if old_count != new_count:
        logger.info(f'Genesis invite used by {member}')
        await member.add_roles(member.guild.get_role(1079479548950880378))
        await member.add_roles(member.guild.get_role(1072547064271077436))

    bot.genesis_invite_uses = new_count