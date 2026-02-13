import discord
from discord.ext import commands
import asyncio

TOKEN = "YOUR_BOT_TOKEN"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

DELETE_DELAY = 2  # seconds
SCAN_LIMIT = 200  # last 200 messages per channel
MESSAGEABLE_TYPES = (
    discord.TextChannel,
    discord.Thread,
    discord.VoiceChannel,
    discord.ForumChannel
)

async def delete_user_messages(interaction, user: discord.Member):
    deleted_count = 0

    for ch in interaction.guild.channels:
        channels_to_scan = []

        if isinstance(ch, discord.TextChannel):
            channels_to_scan.append(ch)
            try:
                channels_to_scan.extend([t for t in ch.threads if t.is_active()])
            except:
                pass
        elif isinstance(ch, discord.Thread):
            channels_to_scan.append(ch)
        elif isinstance(ch, discord.VoiceChannel):
            if ch.guild.me.permissions_in(ch).read_message_history:
                channels_to_scan.append(ch)
        elif isinstance(ch, discord.ForumChannel):
            try:
                channels_to_scan.extend([t for t in await ch.active_threads() if t.is_active()])
            except:
                pass

        for scan_ch in channels_to_scan:
            if not scan_ch.permissions_for(interaction.guild.me).read_message_history:
                continue
            try:
                async for message in scan_ch.history(limit=SCAN_LIMIT):
                    if message.author.id == user.id:
                        try:
                            await message.delete()
                            deleted_count += 1
                            await asyncio.sleep(DELETE_DELAY)
                        except:
                            continue
            except:
                continue

    return deleted_count

@bot.tree.command(name="bancleanup", description="Ban a user and delete their recent messages (reply required)")
async def bancleanup(interaction: discord.Interaction):
    channel = interaction.channel

    # Only allow users with Manage Channels
    if not channel.permissions_for(interaction.user).manage_channels:
        await interaction.response.send_message(
            "❌ You need Manage Channels permission to use this command.", ephemeral=True
        )
        return

    if not interaction.channel.permissions_for(interaction.guild.me).ban_members:
        await interaction.response.send_message(
            "❌ I do not have permission to ban members.", ephemeral=True
        )
        return

    if not interaction.message.reference:
        await interaction.response.send_message(
            "❌ Please reply to a user's message to use this command.", ephemeral=True
        )
        return

    replied_message = await interaction.channel.fetch_message(interaction.message.reference.message_id)
    target_user = replied_message.author

    # Safety check: skip admins / owner
    if target_user.guild_permissions.administrator or target_user == interaction.guild.owner:
        await interaction.response.send_message(
            "❌ Cannot ban admins or the server owner.", ephemeral=True
        )
        return

    await interaction.response.send_message(f"🔨 Banning {target_user} and cleaning up recent messages...")

    # Ban the user
    try:
        await interaction.guild.ban(target_user, reason=f"Banned by {interaction.user} using bancleanup")
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to ban {target_user}: {e}")
        return

    # Delete recent messages
    deleted_count = await delete_user_messages(interaction, target_user)

    await interaction.followup.send(
        f"✅ {target_user} was banned and {deleted_count} messages deleted."
    )

bot.run(TOKEN)
