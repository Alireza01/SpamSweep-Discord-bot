import discord
from discord import app_commands
from discord.ext import commands
import asyncio

TOKEN = "YOUR_BOT_TOKEN"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

DELETE_DELAY = 2  # 2 seconds between deletes

MESSAGEABLE_TYPES = (
    discord.TextChannel,
    discord.Thread,
    discord.VoiceChannel,   # Only if text chat enabled
    discord.ForumChannel
)


@bot.tree.command(name="spammer", description="Delete identical spam messages and ban senders (reply required)")
async def spammer(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("❌ You need Ban Members permission.", ephemeral=True)
        return

    if not interaction.channel.permissions_for(interaction.guild.me).read_message_history:
        await interaction.response.send_message("❌ I can't read message history here.", ephemeral=True)
        return

    # Must be a reply
    if not interaction.message.reference:
        await interaction.response.send_message("❌ Please reply to a spam message.", ephemeral=True)
        return

    replied_message = await interaction.channel.fetch_message(interaction.message.reference.message_id)
    lead_spammer = replied_message.author
    spam_content = replied_message.content.strip()

    if not spam_content:
        await interaction.response.send_message("❌ Cannot target empty message.", ephemeral=True)
        return

    await interaction.response.send_message(
        f"🔍 Scanning server for messages matching the spam from {lead_spammer}..."
    )

    join_date = lead_spammer.joined_at
    banned_users = set()
    deleted_count = 0

    for channel in interaction.guild.channels:
        # Get all messageable channels
        channels_to_scan = []

        if isinstance(channel, discord.TextChannel):
            channels_to_scan.append(channel)
            # Include active threads
            try:
                threads = [t for t in channel.threads if t.is_active()]
                channels_to_scan.extend(threads)
            except:
                pass

        elif isinstance(channel, discord.Thread):
            channels_to_scan.append(channel)

        elif isinstance(channel, discord.VoiceChannel):
            if channel.guild.me.permissions_in(channel).read_message_history:
                channels_to_scan.append(channel)

        elif isinstance(channel, discord.ForumChannel):
            try:
                threads = [t for t in await channel.active_threads() if t.is_active()]
                channels_to_scan.extend(threads)
            except:
                pass

        for ch in channels_to_scan:
            if not ch.permissions_for(interaction.guild.me).read_message_history:
                continue

            try:
                async for message in ch.history(limit=None, after=join_date):
                    if message.content.strip() == spam_content:
                        # Delete message
                        try:
                            await message.delete()
                            deleted_count += 1
                            await asyncio.sleep(DELETE_DELAY)
                        except:
                            continue

                        # Ban user if not already banned & not admin/owner
                        if (
                            message.author.id not in banned_users
                            and not message.author.guild_permissions.administrator
                            and message.author != interaction.guild.owner
                        ):
                            try:
                                await interaction.guild.ban(
                                    message.author,
                                    reason=f"Spam detected via /spammer"
                                )
                                banned_users.add(message.author.id)
                            except:
                                continue
            except:
                continue

    await interaction.followup.send(
        f"✅ Deleted {deleted_count} spam messages.\n"
        f"🔨 Banned {len(banned_users)} users."
    )


bot.run(TOKEN)
